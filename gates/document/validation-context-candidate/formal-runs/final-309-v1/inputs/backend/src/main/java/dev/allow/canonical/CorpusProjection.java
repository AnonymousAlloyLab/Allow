package dev.allow.canonical;

import dev.allow.egraph.IslandResult;
import edu.mit.csail.sdg.ast.Command;
import edu.mit.csail.sdg.ast.Func;
import edu.mit.csail.sdg.parser.CompModule;
import java.util.ArrayList;
import java.util.List;

/** Captures a target and a separate anonymous retrieval environment. */
public final class CorpusProjection {
    /** Prevents construction of the stateless facade. */
    private CorpusProjection() { }

    /** Returns the anonymous environment, body and checked target island.
     * @param world resolved module
     * @param command generated command for traversal
     * @param slot selected function slot
     * @return anonymous projection
     * @throws IllegalArgumentException unsupported target or proof
     * @throws Rejected unsupported structural profile
     */
    public static Result capture(CompModule world, Command command, int slot) {
        List<Func> functions = sourceFunctions(world);
        ModuleEncoder encoder = new ModuleEncoder(world, functions);
        List<Object> module;
        try { module = encoder.encode(command); }
        catch (UnsupportedCanonical failure) { throw new Rejected(profileReason(failure)); }
        List<?> encodedFunctions = (List<?>) module.get(3);
        if (slot < 0 || slot >= encodedFunctions.size()) throw new IllegalArgumentException("target slot");
        List<?> selected = (List<?>) encodedFunctions.get(slot);
        Object body = selected.get(5);
        List<Object> replacement = new ArrayList<>(selected);
        replacement.set(5, List.of("target"));
        List<Object> rewritten = new ArrayList<>(encodedFunctions);
        rewritten.set(slot, replacement);
        List<Object> environment = new ArrayList<>(module.subList(0, 5));
        environment.set(3, rewritten);
        if (dependent(world, functions, slot)) environment.add(List.of("target-dependency", body));
        String context = AnonymizedArtifact.fromStructure(environment).payload();
        String original = AnonymizedArtifact.fromStructure(module).payload();
        List<Integer> path = List.of(3, slot, 5);
        List<IslandCapture> roots = new ArrayList<>();
        for (IslandCapture item : encoder.islands()) if (item.path().equals(path)) roots.add(item);
        if (roots.size() != 1) throw new IllegalArgumentException("target capture");
        EgraphView view = new IslandAdapter(encoder.slots()).analyze(original, roots);
        IslandResult result = view.islands().get(0);
        if (!"CHECKED".equals(result.certificateStatus())) throw new IllegalArgumentException("target proof");
        return new Result(context, body, view.rulesetDigest(), result);
    }

    /** Returns source declarations in stable order, excluding parser-generated command functions.
     * @param world resolved module
     * @return immutable source-function table
     */
    public static List<Func> sourceFunctions(CompModule world) {
        List<Func> result = new ArrayList<>();
        for (Func function : world.getAllFunc()) {
            if (function.isPrivate != edu.mit.csail.sdg.alloy4.Pos.UNKNOWN) result.add(function);
        }
        return List.copyOf(result);
    }

    /** Maps closed profile failure locations to stable non-source diagnostics.
     * @param failure internal profile rejection
     * @return fixed reason code
     */
    private static String profileReason(UnsupportedCanonical failure) {
        for (StackTraceElement frame : failure.getStackTrace()) {
            if (frame.getClassName().equals(ModuleEncoder.class.getName())) {
                if (frame.getMethodName().equals("checkSignature")) return "SIGNATURE_PROFILE_UNSUPPORTED";
                if (frame.getMethodName().equals("field")) return "FIELD_PROFILE_UNSUPPORTED";
                if (frame.getMethodName().equals("checkImports")) return "IMPORT_PROFILE_UNSUPPORTED";
                if (frame.getMethodName().equals("function")) return "FUNCTION_PROFILE_UNSUPPORTED";
            }
            if (frame.getClassName().equals(ExpressionEncoder.class.getName())
                    && frame.getMethodName().equals("checkDeclaration")) return "DECLARATION_PROFILE_UNSUPPORTED";
        }
        return "CANONICAL_PROFILE_UNSUPPORTED";
    }

    /** Closed rejection code, without parser messages or source identifiers. */
    public static final class Rejected extends RuntimeException {
        private final String reason;
        /** Creates a closed diagnostic.
         * @param reason fixed reason code
         */
        Rejected(String reason) { this.reason = reason; }
        /** Reads the fixed reason code.
         * @return reason code
         */
        public String reason() { return reason; }
    }

    /** Checks transitive calls from facts and retained functions to the target.
     * @param world parsed module
     * @param functions source functions in slot order
     * @param slot target index
     * @return true when the body affects retained environment semantics
     */
    private static boolean dependent(CompModule world, List<Func> functions, int slot) {
        Func target = functions.get(slot);
        List<Func> pending = new ArrayList<>();
        for (var fact : world.getAllFacts()) fact.b.findAllFunctions().forEach(pending::add);
        for (Func function : functions) {
            if (function != target) function.getBody().findAllFunctions().forEach(pending::add);
        }
        List<Func> seen = new ArrayList<>();
        while (!pending.isEmpty()) {
            Func next = pending.remove(pending.size() - 1);
            if (next == target) return true;
            if (!seen.contains(next)) { seen.add(next); next.getBody().findAllFunctions().forEach(pending::add); }
        }
        return false;
    }

    /** Anonymous output with replayable certificate.
     * @param context anonymous environment
     * @param body anonymous target tree
     * @param rulesetDigest pinned rule identity
     * @param island checked target proof
     */
    public record Result(String context, Object body, String rulesetDigest, IslandResult island) { }
}
