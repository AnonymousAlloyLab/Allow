package dev.allow.canonical;

import dev.allow.egraph.Sort;
import edu.mit.csail.sdg.ast.Expr;
import edu.mit.csail.sdg.ast.Sig;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** Converts resolved Alloy types into exact anonymous nominal schemas.
     */
final class IslandTypes {
    private final SlotRegistry slots;
    /** Uses the registry belonging to the canonical module traversal.
     * @param slots module identity registry
     */
    IslandTypes(SlotRegistry slots) { this.slots = slots; }

    /** Converts a resolved expression type or rejects unsupported types.
     * @param expr resolved expression
     * @return exact sort
     * @throws UnsupportedCanonical if the resolved type is unsupported
     */
    Sort sort(Expr expr) {
        var type = expr.type();
        if (type.is_bool) {
            if (type.hasTuple() || type.is_int()) { throw new UnsupportedCanonical(); }
            return Sort.bool();
        }
        if (type.is_int() || !type.hasTuple()) { throw new UnsupportedCanonical(); }
        List<List<String>> alternatives = new ArrayList<>();
        for (List<Sig.PrimSig> product : type.fold()) {
            List<String> columns = new ArrayList<>();
            for (Sig.PrimSig sig : product) { columns.add(column(sig)); }
            if (columns.isEmpty()) { throw new UnsupportedCanonical(); }
            alternatives.add(List.copyOf(columns));
        }
        alternatives.sort(Comparator.comparing(IslandTypes::encoding));
        return Sort.relation(alternatives.stream().distinct().toList());
    }

    /** Represents a signature solely through its anonymous declaration slot or builtin.
     * @param sig nominal column
     * @return closed token
     */
    private String column(Sig sig) {
        if (sig == Sig.UNIV) { return "UNIV"; }
        if (sig == Sig.SIGINT) { return "INT"; }
        if (sig == Sig.SEQIDX) { return "SEQIDX"; }
        return "sig:" + slots.index(sig);
    }

    /** Encodes an anonymous tuple for deterministic ordering.
     * @param tuple ordered columns
     * @return compact JSON
     */
    private static String encoding(List<String> tuple) {
        return AnonymizedArtifact.fromStructure(new ArrayList<>(tuple)).payload();
    }
}
