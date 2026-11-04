package dev.allow.canonical;

import edu.mit.csail.sdg.ast.Decl;
import edu.mit.csail.sdg.ast.Expr;
import edu.mit.csail.sdg.ast.ExprBinary;
import edu.mit.csail.sdg.ast.ExprCall;
import edu.mit.csail.sdg.ast.ExprConstant;
import edu.mit.csail.sdg.ast.ExprHasName;
import edu.mit.csail.sdg.ast.ExprITE;
import edu.mit.csail.sdg.ast.ExprLet;
import edu.mit.csail.sdg.ast.ExprList;
import edu.mit.csail.sdg.ast.ExprQt;
import edu.mit.csail.sdg.ast.ExprUnary;
import edu.mit.csail.sdg.ast.ExprVar;
import edu.mit.csail.sdg.ast.Sig;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Encodes supported resolved expressions with lexical identity and ordered children. */
final class ExpressionEncoder {
    private final SlotRegistry slots;
    private int depth;
    private int nodes;

    /** Shares one module's slot registry across all declaration and body traversals.
     * @param slots deterministic global and lexical registry
     */
    ExpressionEncoder(SlotRegistry slots) {
        this.slots = slots;
    }

    /** Serializes one expression with node/depth limits and no source-text fallback.
     * @param expression resolved, type-checked Alloy node
     * @return immutable anonymous constructor tree
     * @throws UnsupportedCanonical on unsupported nodes, scope failures or budget exhaustion
     */
    List<Object> encode(Expr expression) {
        if (++nodes > 10000 || ++depth > 128) { throw new UnsupportedCanonical(); }
        try {
            if (expression instanceof Sig || expression instanceof Sig.Field || expression instanceof ExprVar) {
                return slots.reference(expression);
            }
            if (expression instanceof ExprConstant constant) { return constant(constant); }
            return composite(expression);
        } finally {
            depth--;
        }
    }

    /** Dispatches supported compound classes without using rendered labels.
     * @param expression resolved compound node
     * @return anonymous ordered constructor
     * @throws UnsupportedCanonical if the parser constructor is not represented
     */
    private List<Object> composite(Expr expression) {
        if (expression instanceof ExprUnary unary) { return unary(unary); }
        if (expression instanceof ExprBinary binary) { return binary(binary); }
        if (expression instanceof ExprList list) { return sequence(list); }
        if (expression instanceof ExprQt quantified) { return quantified(quantified); }
        if (expression instanceof ExprLet binding) { return binding(binding); }
        if (expression instanceof ExprCall call) {
            return CanonicalNodes.node("call", slots.function(call.fun), arguments(call.args));
        }
        if (expression instanceof ExprITE choice) {
            return CanonicalNodes.node("ite", encode(choice.cond), encode(choice.left), encode(choice.right));
        }
        throw new UnsupportedCanonical();
    }

    /** Preserves unary multiplicity, relational and Boolean operator identity.
     * @param expression parser unary node
     * @return tagged unary structure
     */
    private List<Object> unary(ExprUnary expression) {
        String operator = OperatorPolicy.checked("unary", expression.op.name());
        return CanonicalNodes.node("unary", operator, encode(expression.sub));
    }

    /** Preserves ordered operands and exact operator family, including integer variants.
     * @param expression parser binary node
     * @return tagged binary structure
     */
    private List<Object> binary(ExprBinary expression) {
        String operator = OperatorPolicy.checked("binary", expression.op.name());
        return CanonicalNodes.node("binary", operator, encode(expression.left), encode(expression.right));
    }

    /** Preserves ordered list children; it does not claim AC/ACI normalization.
     * @param expression parser list expression
     * @return tagged list structure
     */
    private List<Object> sequence(ExprList expression) {
        String operator = OperatorPolicy.checked("list", expression.op.name());
        return CanonicalNodes.node("list", operator, arguments(expression.args));
    }

    /** Encodes semantic integer constants or known built-ins, rejecting strings.
     * @param expression parser constant
     * @return typed constant node
     */
    private List<Object> constant(ExprConstant expression) {
        if (expression.op == ExprConstant.Op.NUMBER) {
            return CanonicalNodes.node("number", expression.num);
        }
        return CanonicalNodes.node("constant", OperatorPolicy.checked("constant", expression.op.name()));
    }

    /** Encodes ordered arguments without exposing a mutable result collection.
     * @param arguments resolved argument sequence
     * @return immutable anonymous argument nodes
     */
    List<Object> arguments(Iterable<? extends Expr> arguments) {
        List<Object> result = new ArrayList<>();
        for (Expr argument : arguments) { result.add(encode(argument)); }
        return List.copyOf(result);
    }

    /** Enters all binder domains in sequence, then serializes the quantified body.
     * @param expression quantified expression with parser-resolved declarations
     * @return tagged quantifier with globally distinct bound ordinals
     */
    private List<Object> quantified(ExprQt expression) {
        String operator = OperatorPolicy.checked("quantifier", expression.op.name());
        Map<ExprHasName, Integer> saved = slots.snapshot();
        try {
            List<Object> declarations = declarations(expression.decls);
            return CanonicalNodes.node("quantifier", operator, declarations, encode(expression.sub));
        } finally {
            slots.restore(saved);
        }
    }

    /** Evaluates a let value before extending its lexical body scope.
     * @param expression parser-resolved let binding
     * @return tagged let node with capture-free reference identity
     */
    private List<Object> binding(ExprLet expression) {
        Map<ExprHasName, Integer> saved = slots.snapshot();
        try {
            List<Object> value = encode(expression.expr);
            int slot = slots.bind(expression.var);
            return CanonicalNodes.node("let", slot, value, encode(expression.sub));
        } finally {
            slots.restore(saved);
        }
    }

    /** Serializes domains before introducing each declaration into the following scope.
     * @param declarations parameter or quantifier declarations in source order
     * @return immutable binding constructors; caller restores scope afterwards
     */
    List<Object> declarations(Iterable<Decl> declarations) {
        List<Object> result = new ArrayList<>();
        for (Decl declaration : declarations) {
            checkDeclaration(declaration);
            List<Object> domain = encode(declaration.expr);
            List<Integer> indices = new ArrayList<>();
            for (ExprHasName name : declaration.names) { indices.add(slots.bind(name)); }
            result.add(CanonicalNodes.node("bind", List.copyOf(indices), domain));
        }
        return List.copyOf(result);
    }

    /** Rejects declaration attributes absent from this conservative profile.
     * @param declaration declaration whose multiplicity remains in its expression
     * @throws UnsupportedCanonical on disjoint/private/mutable declarations
     */
    void checkDeclaration(Decl declaration) {
        if (declaration.disjoint != null || declaration.disjoint2 != null
                || declaration.isPrivate != null || declaration.isVar != null) {
            throw new UnsupportedCanonical();
        }
    }
}
