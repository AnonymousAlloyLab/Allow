package dev.allow.canonical;

import edu.mit.csail.sdg.ast.Expr;
import edu.mit.csail.sdg.ast.ExprHasName;
import edu.mit.csail.sdg.ast.ExprVar;
import edu.mit.csail.sdg.ast.Func;
import edu.mit.csail.sdg.ast.Sig;
import edu.mit.csail.sdg.parser.CompModule;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;

/** Assigns deterministic slots to resolved AST object identities, never names. */
final class SlotRegistry {
    private final Map<Object, List<Object>> globals = new IdentityHashMap<>();
    private final Map<Func, Integer> functions = new IdentityHashMap<>();
    private final Map<ExprHasName, Integer> locals = new IdentityHashMap<>();
    private int nextBound;

    /** Allocates global namespaces in the parser's source declaration order.
     * @param module resolved single-module AST
     */
    SlotRegistry(CompModule module) { this(module, module.getAllFunc()); }

    /** Allocates slots from an explicit corpus declaration table.
     * @param module resolved module
     * @param sourceFunctions ordered source functions
     */
    SlotRegistry(CompModule module, Iterable<Func> sourceFunctions) {
        int signature = 0;
        int field = 0;
        int function = 0;
        for (Sig sig : module.getAllSigs()) {
            globals.put(sig, CanonicalNodes.node("ref", "sig", signature++));
            for (Sig.Field member : sig.getFields()) {
                globals.put(member, CanonicalNodes.node("ref", "field", field++));
            }
        }
        for (Func func : sourceFunctions) {
            functions.put(func, function++);
        }
    }

    /** Resolves a reference in its exact namespace, rejecting free local variables.
     * @param expression resolved reference node
     * @return anonymous tagged reference
     * @throws UnsupportedCanonical if no supported declaration owns the identity
     */
    List<Object> reference(Expr expression) {
        if (expression instanceof ExprVar variable && locals.containsKey(variable)) {
            return CanonicalNodes.node("ref", "bound", locals.get(variable));
        }
        if (globals.containsKey(expression)) {
            return globals.get(expression);
        }
        if (expression == Sig.UNIV) { return CanonicalNodes.node("builtin", "UNIV"); }
        if (expression == Sig.NONE) { return CanonicalNodes.node("builtin", "NONE"); }
        if (expression == Sig.SIGINT) { return CanonicalNodes.node("builtin", "INT"); }
        if (expression == Sig.SEQIDX) { return CanonicalNodes.node("builtin", "SEQIDX"); }
        throw new UnsupportedCanonical();
    }

    /** Reads a global slot index after verifying its registered identity.
     * @param expression signature or field declaration
     * @return namespace-local index
     * @throws UnsupportedCanonical if no global declaration owns the identity
     */
    int index(Expr expression) {
        if (!globals.containsKey(expression)) { throw new UnsupportedCanonical(); }
        return (Integer) globals.get(expression).get(2);
    }

    /** Resolves a call target without reading its human label.
     * @param function resolved function identity
     * @return predicate/function namespace index
     * @throws UnsupportedCanonical if the target belongs to an unknown module
     */
    int function(Func function) {
        Integer result = functions.get(function);
        if (result == null) { throw new UnsupportedCanonical(); }
        return result;
    }

    /** Allocates one globally fresh lexical binder slot.
     * @param name parser-owned local declaration object
     * @return fresh bound namespace ordinal
     */
    int bind(ExprHasName name) {
        int slot = nextBound++;
        locals.put(name, slot);
        return slot;
    }

    /** Copies lexical state before entering a nested body; counters remain global.
     * @return independent identity-based lexical snapshot
     */
    Map<ExprHasName, Integer> snapshot() {
        return new IdentityHashMap<>(locals);
    }

    /** Restores lexical visibility after a scope without recycling binder ordinals.
     * @param snapshot previously copied lexical environment
     */
    void restore(Map<ExprHasName, Integer> snapshot) {
        locals.clear();
        locals.putAll(snapshot);
    }
}
