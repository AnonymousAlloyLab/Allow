package dev.allow.worker;

import edu.mit.csail.sdg.ast.*;
import edu.mit.csail.sdg.parser.CompModule;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;

/** Iterative occurrence/depth limit; solver-specific bounds are conservative. */
final class AstPolicy {
    /** Prevents construction of the stateless policy. */
    private AstPolicy() {}

    /**
     * Checks the entire module and selected command.
     * @param world parsed module
     * @param command selection
     * @throws IllegalArgumentException unsupported imports or resources
     */
    static void check(CompModule world, Command command) {
        imports(world);
        bounds(command);
        ArrayDeque<Entry> pending = new ArrayDeque<>();
        for (Command item : world.getAllCommands()) pending.add(new Entry(item.formula, 1));
        for (Assert item : world.getAllAssertions()) pending.add(new Entry(item.expr, 1));
        for (edu.mit.csail.sdg.parser.Macro item : world.getAllMacros()) pending.add(new Entry(item.body, 1));
        pending.add(new Entry(world.getAllReachableFacts(), 1));
        for (Func function : world.getAllFunc()) {
            pending.add(new Entry(function.getBody(), 1));
            if (function.returnDecl != null) pending.add(new Entry(function.returnDecl, 1));
            for (Decl decl : function.decls) pending.add(new Entry(decl.expr, 1));
        }
        for (Sig signature : world.getAllSigs()) {
            for (Decl decl : signature.getFieldDecls()) pending.add(new Entry(decl.expr, 1));
            for (Expr fact : signature.getFacts()) pending.add(new Entry(fact, 1));
        }
        walk(pending);
    }

    /**
     * Allows only Alloy's implicit integer library.
     * @param world parsed module
     * @throws IllegalArgumentException explicit import
     */
    private static void imports(CompModule world) {
        for (CompModule.Open open : world.getOpens()) {
            if (open.pos != null || !open.filename.equals("util/integer") || !open.args.isEmpty()) {
                throw new IllegalArgumentException("Imports are unsupported.");
            }
        }
        if (world.getAllReachableModules().size() > 2) {
            throw new IllegalArgumentException("Unexpected reachable modules.");
        }
    }

    /**
     * Rejects excessive bounds before translation.
     * @param command parsed command
     * @throws IllegalArgumentException excessive command bounds
     */
    private static void bounds(Command command) {
        if (command.overall > 8 || command.bitwidth > 8 || command.maxseq > 8
                || command.maxprefix > 10 || command.minprefix > 10) {
            throw new IllegalArgumentException("Local policy allows scope/bitwidth/sequence up to 8 and trace up to 10.");
        }
        for (CommandScope scope : command.scope) {
            if (scope.endingScope > 8) throw new IllegalArgumentException("Signature scope exceeds 8.");
        }
    }

    /**
     * Counts occurrences without recursive Java stack use.
     * @param pending initial roots
     * @throws IllegalArgumentException excessive nodes or depth
     */
    private static void walk(ArrayDeque<Entry> pending) {
        int count = 0;
        while (!pending.isEmpty()) {
            Entry current = pending.removeLast();
            if (++count > 10000 || current.depth() > 128) {
                throw new IllegalArgumentException("AST node/depth limit exceeded.");
            }
            for (Expr child : children(current.expression())) {
                pending.add(new Entry(child, current.depth() + 1));
            }
        }
    }

    /**
     * Lists syntactic children, treating references as leaves.
     * @param expression node
     * @return ordered children
     */
    private static List<Expr> children(Expr expression) {
        List<Expr> result = new ArrayList<>();
        if (expression instanceof ExprUnary unary) result.add(unary.sub);
        else if (expression instanceof ExprBinary binary) result.addAll(List.of(binary.left, binary.right));
        else if (expression instanceof ExprList list) result.addAll(list.args);
        else if (expression instanceof ExprCall call) result.addAll(call.args);
        else if (expression instanceof ExprITE conditional) {
            result.addAll(List.of(conditional.cond, conditional.left, conditional.right));
        } else if (expression instanceof ExprLet let) result.addAll(List.of(let.expr, let.sub));
        else if (expression instanceof ExprQt quantifier) {
            for (Decl declaration : quantifier.decls) result.add(declaration.expr);
            result.add(quantifier.sub);
        }
        return result;
    }

    /** Work stack element; no mutable traversal state is exposed. */
    private record Entry(Expr expression, int depth) {}
}
