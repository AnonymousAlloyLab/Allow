package dev.allow.document;

import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import edu.mit.csail.sdg.ast.Decl;
import edu.mit.csail.sdg.ast.Expr;
import edu.mit.csail.sdg.ast.ExprBinary;
import edu.mit.csail.sdg.ast.ExprCall;
import edu.mit.csail.sdg.ast.ExprList;
import edu.mit.csail.sdg.ast.ExprQt;
import edu.mit.csail.sdg.ast.ExprUnary;
import edu.mit.csail.sdg.ast.ExprVar;
import edu.mit.csail.sdg.ast.Func;
import edu.mit.csail.sdg.ast.Sig;
import java.util.IdentityHashMap;
import java.util.Map;
import java.util.UUID;

/** Reads Alloy expression objects into the closed document expression family. */
final class AlloyExpressionReader {
    private final Map<Object, String> identities = new IdentityHashMap<>();
    private final ArrayNode nodes = JsonNodeFactory.instance.arrayNode();
    private final Map<String, Expr> origins = new java.util.HashMap<>();
    private final boolean generatedSource;

    /**
     * Creates an expression reader for a known source origin.
     * @param generatedSource true only for printer-produced source without authored restrictions
     */
    AlloyExpressionReader(boolean generatedSource) {
        this.generatedSource = generatedSource;
    }

    /**
     * Binds an exact parser object to an already resolved declaration identity.
     * @param object Alloy declaration object
     * @param id stable declaration identity
     * @throws IllegalArgumentException for unsupported or unresolved syntax
     */
    void bind(Object object, String id) {
        if (identities.put(object, id) != null) throw new IllegalArgumentException("duplicate parser identity");
    }

    /**
     * Reads one expression, rejecting unsupported parser AST forms.
     * @param expression resolved Alloy AST expression
     * @return generated root identity
     * @throws IllegalArgumentException for unsupported or unresolved syntax
     */
    String read(Expr expression) {
        Expr e = unwrap(expression);
        String result;
        if (e instanceof Sig) result = reference("signature_ref", e);
        else if (e instanceof Sig.Field) result = reference("field_ref", e);
        else if (e instanceof ExprVar) result = reference("variable_ref", e);
        else if (e instanceof ExprUnary) result = unary((ExprUnary) e);
        else if (e instanceof ExprBinary && generatedSource && generatedField((ExprBinary) e)) {
            result = reference("field_ref", unwrap(((ExprBinary) e).right));
        } else if (e instanceof ExprBinary) result = binary((ExprBinary) e);
        else if (e instanceof ExprList) result = list((ExprList) e);
        else if (e instanceof ExprCall) result = call((ExprCall) e);
        else if (e instanceof ExprQt) result = quantifier((ExprQt) e);
        else throw new IllegalArgumentException("unsupported Alloy expression");
        origins.put(result, expression);
        return result;
    }

    /**
     * Returns parser origins for nodes that were not synthetic list folds.
     * @return immutable node-to-parser-expression index
     */
    Map<String, Expr> origins() {
        return Map.copyOf(origins);
    }

    /**
     * Returns a defensive copy of constructed nodes.
     * @return expression node array
     */
    ArrayNode nodes() {
        return nodes.deepCopy();
    }

    /**
     * Removes parser NOOP wrappers.
     * @param expression parser expression
     * @return expression without transparent wrappers
     */
    private Expr unwrap(Expr expression) {
        Expr current = expression;
        while (current instanceof ExprUnary && ((ExprUnary) current).op == ExprUnary.Op.NOOP) {
            current = ((ExprUnary) current).sub;
        }
        return current;
    }

    /**
     * Reads a parser-resolved reference by object identity.
     * @param tag closed reference tag
     * @param object parser declaration object
     * @return generated node identity
     * @throws IllegalArgumentException for unsupported or unresolved syntax
     */
    private String reference(String tag, Object object) {
        String target = identities.get(object);
        if (target == null) throw new IllegalArgumentException("unresolved Alloy identity");
        ObjectNode result = node(tag);
        result.put("targetId", target);
        return result.path("id").textValue();
    }

    /**
     * Reads a supported unary expression.
     * @param expression Alloy unary node
     * @return generated node identity
     * @throws IllegalArgumentException for unsupported or unresolved syntax
     */
    private String unary(ExprUnary expression) {
        String tag = switch (expression.op) {
            case NOT -> "not";
            case SOME -> "some_test";
            case NO -> "no_test";
            case ONE -> "one_test";
            case LONE -> "lone_test";
            case TRANSPOSE -> "transpose";
            default -> throw new IllegalArgumentException("unsupported unary operator");
        };
        ObjectNode result = node(tag);
        result.put("operandId", read(expression.sub));
        return result.path("id").textValue();
    }

    /**
     * Identifies only Alloy's exact generated field-owner wrapper.
     * @param expression parser binary expression
     * @return whether the wrapper denotes its field owner
     */
    private boolean generatedField(ExprBinary expression) {
        Expr left = unwrap(expression.left);
        Expr right = unwrap(expression.right);
        return expression.op == ExprBinary.Op.DOMAIN && right instanceof Sig.Field
            && left == ((Sig.Field) right).sig;
    }

    /**
     * Reads a supported binary expression.
     * @param expression Alloy binary node
     * @return generated node identity
     * @throws IllegalArgumentException for unsupported or unresolved syntax
     */
    private String binary(ExprBinary expression) {
        String tag = binaryTag(expression);
        ObjectNode result = node(tag);
        result.put("leftId", read(expression.left));
        result.put("rightId", read(expression.right));
        return result.path("id").textValue();
    }

    /**
     * Maps only supported Alloy binary operators.
     * @param expression binary expression
     * @return closed tag
     * @throws IllegalArgumentException for unsupported or unresolved syntax
     */
    private String binaryTag(ExprBinary expression) {
        return switch (expression.op) {
            case AND -> "and";
            case OR -> "or";
            case IMPLIES -> "implies";
            case IFF -> "iff";
            case EQUALS -> "equal";
            case IN -> "subset";
            case PLUS -> "union";
            case INTERSECT -> "intersection";
            case MINUS -> "difference";
            case JOIN -> "join";
            case ARROW -> "product";
            default -> throw new IllegalArgumentException("unsupported binary operator");
        };
    }

    /**
     * Reads an ordered parser conjunction or disjunction as a left fold.
     * @param expression Alloy list
     * @return generated root identity
     * @throws IllegalArgumentException for unsupported or unresolved syntax
     */
    private String list(ExprList expression) {
        String tag = expression.op == ExprList.Op.AND ? "and" : expression.op == ExprList.Op.OR ? "or" : "";
        if (tag.isEmpty() || expression.args.size() < 2) throw new IllegalArgumentException("unsupported expression list");
        String root = read(expression.args.get(0));
        for (int index = 1; index < expression.args.size(); index++) {
            ObjectNode parent = node(tag);
            parent.put("leftId", root);
            parent.put("rightId", read(expression.args.get(index)));
            root = parent.path("id").textValue();
        }
        return root;
    }

    /**
     * Reads a resolved predicate call.
     * @param expression Alloy invocation
     * @return generated call identity
     * @throws IllegalArgumentException for unsupported or unresolved syntax
     */
    private String call(ExprCall expression) {
        Func function = expression.fun;
        String target = identities.get(function);
        if (!function.isPred || target == null) throw new IllegalArgumentException("unknown predicate");
        ObjectNode result = node("predicate_call");
        result.put("predicateId", target);
        ArrayNode args = result.putArray("arguments");
        for (Expr arg : expression.args) args.add(read(arg));
        return result.path("id").textValue();
    }

    /**
     * Reads an atom quantifier with a single declared binder.
     * @param expression Alloy quantifier
     * @return generated quantifier identity
     * @throws IllegalArgumentException for unsupported or unresolved syntax
     */
    private String quantifier(ExprQt expression) {
        if ((expression.op != ExprQt.Op.ALL && expression.op != ExprQt.Op.SOME)
                || expression.decls.size() != 1 || expression.decls.get(0).names.size() != 1) {
            throw new IllegalArgumentException("unsupported quantifier");
        }
        Decl decl = expression.decls.get(0);
        if (decl.disjoint != null || decl.disjoint2 != null || decl.isPrivate != null || decl.isVar != null) {
            throw new IllegalArgumentException("unsupported quantifier modifiers");
        }
        Expr domain = unwrap(decl.expr);
        if (domain instanceof ExprUnary && ((ExprUnary) domain).op == ExprUnary.Op.ONEOF) domain = unwrap(((ExprUnary) domain).sub);
        if (!(domain instanceof Sig) || !identities.containsKey(domain)) throw new IllegalArgumentException("quantifier domain");
        ObjectNode result = node(expression.op == ExprQt.Op.ALL ? "all_quant" : "some_quant");
        ObjectNode binder = result.putObject("binder");
        String binderId = id();
        binder.put("id", binderId);
        binder.put("name", decl.get().label);
        binder.put("signatureId", identities.get(domain));
        identities.put(decl.get(), binderId);
        result.put("bodyId", read(expression.sub));
        identities.remove(decl.get());
        return result.path("id").textValue();
    }

    /**
     * Appends a new node with a fresh parser-elaboration identity.
     * @param tag closed node tag
     * @return node under construction
     */
    private ObjectNode node(String tag) {
        ObjectNode result = nodes.addObject();
        result.put("tag", tag);
        result.put("id", id());
        return result;
    }

    /**
     * Allocates a fresh server identity.
     * @return UUIDv4 identity
     */
    private String id() {
        return "server:" + UUID.randomUUID();
    }
}
