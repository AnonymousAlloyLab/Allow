package dev.allow.document;

import edu.mit.csail.sdg.ast.Expr;
import edu.mit.csail.sdg.ast.ExprBinary;
import edu.mit.csail.sdg.ast.ExprUnary;
import edu.mit.csail.sdg.ast.Sig;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Derives nominal declaration schemas from resolved Alloy syntax, never Type strings. */
final class AlloySchemaReader {
    private final Map<Object, String> identities;

    /**
     * Creates a schema reader using exact parser-object identity bindings.
     * @param identities parser signature objects to stable IDs
     */
    AlloySchemaReader(Map<Object, String> identities) {
        this.identities = identities;
    }

    /**
     * Derives ordered columns from an explicitly set-valued parameter.
     * @param expression parameter declaration expression
     * @return nonempty nominal schema
     * @throws IllegalArgumentException if syntax is outside the supported fragment
     */
    List<String> parameter(Expr expression) {
        Expr value = unwrap(expression);
        if (!(value instanceof ExprUnary) || ((ExprUnary) value).op != ExprUnary.Op.SETOF) {
            throw new IllegalArgumentException("parameter must be set-valued");
        }
        return columns(((ExprUnary) value).sub);
    }

    /**
     * Derives ordered columns from a field range declaration.
     * @param expression field declaration expression
     * @return nonempty nominal schema
     */
    List<String> fieldColumns(Expr expression) {
        Expr value = unwrap(expression);
        if (value instanceof ExprUnary) value = ((ExprUnary) value).sub;
        return columns(value);
    }

    /**
     * Reads the field's declared multiplicity.
     * @param expression field declaration expression
     * @return closed multiplicity
     * @throws IllegalArgumentException for unsupported multiplicity
     */
    String fieldMultiplicity(Expr expression) {
        Expr value = unwrap(expression);
        if (!(value instanceof ExprUnary)) return columns(value).size() == 1 ? "one" : "set";
        return switch (((ExprUnary) value).op) {
            case ONEOF -> "one";
            case LONEOF -> "lone";
            case SOMEOF -> "some";
            case SETOF -> "set";
            default -> throw new IllegalArgumentException("unsupported field multiplicity");
        };
    }

    /**
     * Reads a plain signature product.
     * @param expression resolved declaration expression
     * @return nonempty ordered schema
     * @throws IllegalArgumentException for invalid arity
     */
    private List<String> columns(Expr expression) {
        List<String> result = new ArrayList<>();
        append(unwrap(expression), result);
        if (result.isEmpty() || result.size() > 8) throw new IllegalArgumentException("declaration arity");
        return List.copyOf(result);
    }

    /**
     * Flattens only plain product operators and bound nominal signatures.
     * @param expression current Alloy expression
     * @param result output columns
     * @throws IllegalArgumentException for unsupported syntax
     */
    private void append(Expr expression, List<String> result) {
        Expr value = unwrap(expression);
        if (value instanceof Sig) {
            String id = identities.get(value);
            if (id == null) throw new IllegalArgumentException("unknown nominal signature");
            result.add(id);
        } else if (value instanceof ExprBinary && ((ExprBinary) value).op == ExprBinary.Op.ARROW) {
            append(((ExprBinary) value).left, result);
            append(((ExprBinary) value).right, result);
        } else throw new IllegalArgumentException("unsupported declaration schema");
    }

    /**
     * Removes only transparent parser wrappers.
     * @param expression resolved Alloy expression
     * @return unwrapped expression
     */
    private Expr unwrap(Expr expression) {
        Expr result = expression;
        while (result instanceof ExprUnary && ((ExprUnary) result).op == ExprUnary.Op.NOOP) result = ((ExprUnary) result).sub;
        return result;
    }
}
