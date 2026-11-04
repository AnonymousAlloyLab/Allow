package dev.allow.canonical;

import dev.allow.egraph.Sort;
import dev.allow.egraph.Term;
import edu.mit.csail.sdg.ast.Expr;
import edu.mit.csail.sdg.ast.ExprBinary;
import edu.mit.csail.sdg.ast.ExprConstant;
import edu.mit.csail.sdg.ast.ExprList;
import edu.mit.csail.sdg.ast.ExprUnary;
import java.util.ArrayList;
import java.util.List;
import java.util.IdentityHashMap;
import java.util.Map;

/** Lowers only admitted operators, preserving each captured occurrence's anonymous subtree.
     */
final class IslandLowering {
    private final IslandTypes types;
    private final Map<Term, Integer> sizes = new IdentityHashMap<>();
    /** Uses the module's exact identity registry.
     * @param slots canonical traversal registry
     */
    IslandLowering(SlotRegistry slots) { types = new IslandTypes(slots); }

    /** Lowers one captured expression; unsupported nodes remain whole opaque atoms.
     * @param expr resolved occurrence
     * @param tree captured tree
     * @return typed term
     */
    Term lower(Expr expr, List<Object> tree) {
        Sort sort = types.sort(expr);
        if (expr instanceof ExprUnary unary) { return unary(unary, tree, sort); }
        if (expr instanceof ExprBinary binary) { return binary(binary, tree, sort); }
        if (expr instanceof ExprList list) { return list(list, tree, sort); }
        if (expr instanceof ExprConstant constant && sort.kind().equals("BOOL")) {
            if (constant.op == ExprConstant.Op.TRUE) { return node("TRUE", sort); }
            if (constant.op == ExprConstant.Op.FALSE) { return node("FALSE", sort); }
        }
        return atom(sort, tree);
    }

    /** Lowers admitted unary operations only.
     * @param expr unary occurrence
     * @param tree canonical subtree
     * @param sort resolved sort
     * @return term
     */
    private Term unary(ExprUnary expr, List<Object> tree, Sort sort) {
        String op = expr.op.name();
        if (!List.of("NOOP", "NOT", "SOME", "NO").contains(op)) { return atom(sort, tree); }
        List<Object> sub = child(tree, "unary", op, 2);
        Term operand = lower(expr.sub, sub);
        if (op.equals("NOOP")) {
            return expr.type().equals(expr.sub.type()) && sort.equals(operand.sort()) ? operand : atom(sort, tree);
        }
        if (!sort.equals(Sort.bool())) { return atom(sort, tree); }
        if (op.equals("NOT") && !operand.sort().equals(sort)) { return atom(sort, tree); }
        if (!op.equals("NOT") && !operand.sort().kind().equals("REL")) { return atom(sort, tree); }
        return node(op, sort, operand);
    }

    /** Lowers Boolean and exact-schema relation operations.
     * @param expr binary occurrence
     * @param tree canonical subtree
     * @param sort resolved sort
     * @return term
     */
    private Term binary(ExprBinary expr, List<Object> tree, Sort sort) {
        String op = expr.op.name();
        if (!List.of("AND", "OR", "IMPLIES", "IFF", "PLUS", "INTERSECT", "MINUS").contains(op)) {
            return atom(sort, tree);
        }
        Term a = lower(expr.left, child(tree, "binary", op, 2));
        Term b = lower(expr.right, child(tree, "binary", op, 3));
        if (!sort.equals(a.sort()) || !sort.equals(b.sort())) { return atom(sort, tree); }
        if (sort.kind().equals("BOOL")) { return boolBinary(op, sort, a, b, tree); }
        String rel = switch (op) { case "PLUS" -> "UNION"; case "INTERSECT" -> "INTER";
            case "MINUS" -> "DIFF"; default -> ""; };
        return rel.isEmpty() ? atom(sort, tree) : node(rel, sort, a, b);
    }

    /** Expands supported Boolean connectives with fixed ordered children.
     * @param op source operator
     * @param sort Boolean sort
     * @param a left
     * @param b right
     * @param tree captured tree
     * @return term
     */
    private Term boolBinary(String op, Sort sort, Term a, Term b, List<Object> tree) {
        if (op.equals("AND") || op.equals("OR")) { return node(op, sort, a, b); }
        Term ab = node("OR", sort, node("NOT", sort, a), b);
        if (op.equals("IMPLIES")) { return ab; }
        if (op.equals("IFF")) { return node("AND", sort, ab, node("OR", sort, node("NOT", sort, b), a)); }
        return atom(sort, tree);
    }

    /** Folds ordered Boolean list children from left to right.
     * @param expr list occurrence
     * @param tree canonical subtree
     * @param sort resolved sort
     * @return term
     * @throws UnsupportedCanonical if the captured tree differs
     */
    private Term list(ExprList expr, List<Object> tree, Sort sort) {
        String op = expr.op.name();
        if (!sort.equals(Sort.bool()) || !List.of("AND", "OR").contains(op)) { return atom(sort, tree); }
        if (tree.size() != 3 || !tree.get(0).equals("list") || !tree.get(1).equals(op)
                || !(tree.get(2) instanceof List<?> children) || children.size() != expr.args.size()) {
            throw new UnsupportedCanonical();
        }
        Term result = null;
        for (int i = 0; i < children.size(); i++) {
            Term next = lower(expr.args.get(i), checked(children.get(i)));
            if (!next.sort().equals(sort)) { return atom(sort, tree); }
            result = result == null ? next : node(op, sort, result, next);
        }
        return result == null ? node(op.equals("AND") ? "TRUE" : "FALSE", sort) : result;
    }

    /** Checks and returns an exact anonymous child.
     * @param tree parent tree
     * @param tag expected tag
     * @param op expected operation
     * @param index child position
     * @return child tree
     * @throws UnsupportedCanonical if the captured tree differs
     */
    private List<Object> child(List<Object> tree, String tag, String op, int index) {
        if (tree.size() <= index || !tree.get(0).equals(tag) || !tree.get(1).equals(op)) {
            throw new UnsupportedCanonical();
        }
        return checked(tree.get(index));
    }

    /** Validates a positional array without trusting an unchecked cast.
     * @param value captured value
     * @return copied child
     * @throws UnsupportedCanonical if the child is not an array
     */
    private List<Object> checked(Object value) {
        if (!(value instanceof List<?> list)) { throw new UnsupportedCanonical(); }
        return new ArrayList<>(list);
    }

    /** Constructs an opaque anonymous leaf.
     * @param sort exact sort
     * @param tree anonymous tree
     * @return atom
     */
    private Term atom(Sort sort, List<Object> tree) {
        Term term = Term.atom(sort, AnonymizedArtifact.fromStructure(tree).payload());
        sizes.put(term, 1);
        return term;
    }

    /** Constructs a typed operator.
     * @param op closed operator
     * @param sort result sort
     * @param children ordered operands
     * @return term
     * @throws IslandLimit if lowering exceeds the island input budget
     */
    private Term node(String op, Sort sort, Term... children) {
        int size = 1;
        for (Term child : children) {
            size += sizes.get(child);
            if (size > 2048) { throw new IslandLimit(); }
        }
        Term term = Term.node(op, sort, List.of(children));
        sizes.put(term, size);
        return term;
    }
}
