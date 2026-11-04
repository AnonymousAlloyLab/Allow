package dev.allow.canonical;

import edu.mit.csail.sdg.ast.Command;
import edu.mit.csail.sdg.alloy4.Pos;
import edu.mit.csail.sdg.ast.CommandScope;
import edu.mit.csail.sdg.ast.Expr;
import edu.mit.csail.sdg.ast.ExprHasName;
import edu.mit.csail.sdg.ast.Func;
import edu.mit.csail.sdg.ast.Sig;
import edu.mit.csail.sdg.parser.CompModule;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Maps the supported whole-module semantics to the frozen anonymous structural grammar. */
final class ModuleEncoder {
    private final CompModule module;
    private final SlotRegistry slots;
    private final ExpressionEncoder expressions;
    private final List<IslandCapture> islands = new ArrayList<>();

    /** Creates a fresh mapper; no name-dependent state survives another module.
     * @param module parser-resolved single module
     */
    ModuleEncoder(CompModule module) {
        this.module = module;
        slots = new SlotRegistry(module);
        expressions = new ExpressionEncoder(slots);
    }

    /** Serializes all relevant declarations/facts plus the selected command context.
     * @param command selected parsed run/check command
     * @return complete anonymous module constructor
     * @throws UnsupportedCanonical if module macros are present
     */
    List<Object> encode(Command command) {
        if (!module.getAllMacros().isEmpty()) {
            throw new UnsupportedCanonical();
        }
        checkImports();
        List<Object> signatures = signatures();
        List<Object> functions = functions();
        List<Object> facts = new ArrayList<>();
        for (var fact : module.getAllFacts()) {
            List<Object> tree = expressions.encode(fact.b);
            islands.add(new IslandCapture(List.of(4, facts.size()), fact.b, tree));
            facts.add(tree);
        }
        return CanonicalNodes.node("module", 1, signatures, functions, List.copyOf(facts), command(command));
    }

    /** Allows only the parser's synthetic integer module, never a source open.
     * @throws UnsupportedCanonical if an explicit or unknown import is present
     */
    private void checkImports() {
        for (CompModule.Open imported : module.getOpens()) {
            if (imported.pos != null || !imported.filename.equals("util/integer") || !imported.args.isEmpty()) {
                throw new UnsupportedCanonical();
            }
        }
    }

    /** Preserves source declaration ordering rather than sorting visible signature names.
     * @return supported signature declarations and their field structures
     */
    private List<Object> signatures() {
        List<Object> result = new ArrayList<>();
        for (Sig signature : module.getAllSigs()) {
            checkSignature(signature);
            List<Object> fields = new ArrayList<>();
            for (Sig.Field field : signature.getFields()) { fields.add(field(field)); }
            result.add(CanonicalNodes.node("sig", slots.index(signature), List.copyOf(fields)));
        }
        return List.copyOf(result);
    }

    /** Rejects semantic signature flags not represented by the v1 grammar.
     * @param signature resolved signature to validate
     * @throws UnsupportedCanonical if signature attributes are outside the profile
     */
    private void checkSignature(Sig signature) {
        if (!(signature instanceof Sig.PrimSig primitive) || primitive.parent != Sig.UNIV
                || signature.isAbstract != null || signature.isSubset != null
                || signature.isLone != null || signature.isOne != null || signature.isSome != null
                || signature.isPrivate != null || signature.isEnum != null || signature.isVariable != null
                || signature.isMeta != null || !signature.getFacts().isEmpty()) {
            throw new UnsupportedCanonical();
        }
    }

    /** Preserves field owner identity and exact declared domain/multiplicity.
     * @param field parser field declaration
     * @return anonymous field constructor
     * @throws UnsupportedCanonical if field attributes are outside the profile
     */
    private List<Object> field(Sig.Field field) {
        if (field.isPrivate != null || field.isVariable != null || field.defined || field.isMeta != null) {
            throw new UnsupportedCanonical();
        }
        expressions.checkDeclaration(field.decl());
        return CanonicalNodes.node("field", slots.index(field), slots.index(field.sig),
                expressions.encode(field.decl().expr));
    }

    /** Encodes all function declarations to preserve call targets and parameter scopes.
     * @return immutable function constructors in declaration order
     */
    private List<Object> functions() {
        List<Object> result = new ArrayList<>();
        for (Func function : module.getAllFunc()) { result.add(function(function)); }
        return List.copyOf(result);
    }

    /** Serializes a function with lexical parameters and restores scope afterwards.
     * @param function resolved function declaration
     * @return constructor without the function's display label
     * @throws UnsupportedCanonical if source-private or recursive declarations are encountered
     */
    private List<Object> function(Func function) {
        if (function.isPrivate != null && function.isPrivate != Pos.UNKNOWN) { throw new UnsupportedCanonical(); }
        for (Func reached : function.getBody().findAllFunctions()) {
            if (reached == function) { throw new UnsupportedCanonical(); }
        }
        Map<ExprHasName, Integer> saved = slots.snapshot();
        try {
            List<Object> parameters = expressions.declarations(function.decls);
            Object returns = function.isPred ? null : expressions.encode(function.returnDecl);
            List<Object> body = expressions.encode(function.getBody());
            islands.add(new IslandCapture(List.of(3, slots.function(function), 5), function.getBody(), body));
            return CanonicalNodes.node("function", slots.function(function), function.isPred,
                    parameters, returns, body);
        } finally {
            slots.restore(saved);
        }
    }

    /** Binds canonical structure to selected command, scopes and integer semantics.
     * @param command selected command with its resolved formula
     * @return command constructor with no display label
     * @throws UnsupportedCanonical if temporal or incremental command semantics are present
     */
    private List<Object> command(Command command) {
        if (command.minprefix != -1 || command.maxprefix != -1 || command.parent != null
                || !command.additionalExactScopes.isEmpty()) { throw new UnsupportedCanonical(); }
        List<Object> scopes = new ArrayList<>();
        for (CommandScope scope : command.scope) {
            scopes.add(CanonicalNodes.node("scope", slots.index(scope.sig), scope.isExact,
                    scope.startingScope, scope.endingScope, scope.increment));
        }
        List<Object> formula = expressions.encode(command.formula);
        islands.add(new IslandCapture(List.of(5, 6), command.formula, formula));
        return CanonicalNodes.node("command", command.check, command.overall, command.bitwidth,
                command.maxseq, List.copyOf(scopes), formula);
    }
    /** Returns captures in traversal order without exposing mutable state.
     * @return immutable occurrence captures
     */
    List<IslandCapture> islands() { return List.copyOf(islands); }

    /** Exposes the same identity registry used for the module traversal.
     * @return module-local registry
     */
    SlotRegistry slots() { return slots; }

}
