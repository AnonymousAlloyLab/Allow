package dev.allow.document;

import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import edu.mit.csail.sdg.alloy4.Pair;
import edu.mit.csail.sdg.ast.Assert;
import edu.mit.csail.sdg.ast.Command;
import edu.mit.csail.sdg.ast.Decl;
import edu.mit.csail.sdg.ast.Expr;
import edu.mit.csail.sdg.ast.Func;
import edu.mit.csail.sdg.ast.Sig;
import edu.mit.csail.sdg.parser.CompModule;
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Converts resolved Alloy declarations after independent lexical fragment checking. */
final class AlloyModuleReader {
    private final CompModule parsed;
    private final boolean generatedSource;
    private final boolean transientComparison;
    private final Map<Object, String> identities = new IdentityHashMap<>();
    private final Map<String, String> names = new HashMap<>();
    private final ObjectNode module = JsonNodeFactory.instance.objectNode();
    private final AlloyExpressionReader expressions;
    private final AlloySchemaReader schemas;
    private int authoredCommands;

    /**
     * Creates an adapter over an already parsed complete module.
     * @param parsed Alloy module
     * @param generatedSource true only for exact server-printer output
     */
    AlloyModuleReader(CompModule parsed, boolean generatedSource) {
        this(parsed, generatedSource, false);
    }

    /**
     * Creates a reader with an internal comparison-only depth profile.
     * @param parsed resolved Alloy module
     * @param generatedSource whether printer wrappers are allowed
     * @param transientComparison whether reconstruction is discarded after comparison
     */
    AlloyModuleReader(CompModule parsed, boolean generatedSource, boolean transientComparison) {
        this.parsed = parsed;
        this.generatedSource = generatedSource;
        this.transientComparison = transientComparison;
        this.expressions = new AlloyExpressionReader(generatedSource);
        this.schemas = new AlloySchemaReader(identities);
    }

    /**
     * Reads declarations and authored command count after lexical validation.
     * @param authoredCommands number of actual command tokens
     * @return independently checked candidate module
     */
    ObjectNode read(int authoredCommands) {
        this.authoredCommands = authoredCommands;
        module.put("version", 1);
        for (String key : List.of("signatures", "fields", "predicates", "facts", "assertions", "commands", "nodes")) {
            module.putArray(key);
        }
        bindDeclarations();
        signatures();
        predicates();
        formulas();
        commands(authoredCommands);
        module.set("nodes", expressions.nodes());
        new ModuleChecker(module, transientComparison ? 512 : 32).check();
        return module.deepCopy();
    }

    /**
     * Returns parser origins captured during the last elaboration.
     * @return immutable expression-origin index
     */
    Map<String, Expr> origins() {
        return expressions.origins();
    }

    /** Binds all declaration objects before processing any body. */
    private void bindDeclarations() {
        for (Sig sig : parsed.getAllReachableUserDefinedSigs()) {
            bind(sig, shortName(sig.label));
            for (Sig.Field field : sig.getFields()) bind(field, shortName(field.label));
        }
        for (Func func : parsed.getAllFunc()) if (!synthetic(func)) bind(func, shortName(func.label));
        for (Assert assertion : parsed.getAllAssertions()) bind(assertion, shortName(assertion.label));
    }

    /**
     * Records parser object and global declaration name.
     * @param object resolved object
     * @param name declaration name
     * @throws IllegalArgumentException for unsupported declarations
     */
    private void bind(Object object, String name) {
        String id = id();
        if (names.putIfAbsent(name, id) != null) throw new IllegalArgumentException("duplicate name");
        identities.put(object, id);
        expressions.bind(object, id);
    }

    /** Reads static signatures and fields. */
    private void signatures() {
        for (Sig sig : parsed.getAllReachableUserDefinedSigs()) {
            checkSignature(sig);
            ObjectNode item = item("signatures", "signature", identities.get(sig), shortName(sig.label));
            item.put("multiplicity", sig.isOne != null ? "one" : sig.isLone != null ? "lone" : sig.isSome != null ? "some" : "set");
            for (Sig.Field field : sig.getFields()) field(sig, field);
        }
    }

    /**
     * Rejects unsupported signature attributes.
     * @param sig Alloy signature
     * @throws IllegalArgumentException for unsupported declarations
     */
    private void checkSignature(Sig sig) {
        if (sig.builtin || !sig.isTopLevel() || sig.isAbstract != null || sig.isPrivate != null
                || sig.isEnum != null || sig.isVariable != null || !sig.getFacts().isEmpty()) {
            throw new IllegalArgumentException("unsupported signature");
        }
    }

    /**
     * Reads one field declaration from resolved nominal expressions.
     * @param owner owning signature
     * @param field field declaration
     * @throws IllegalArgumentException for unsupported declarations
     */
    private void field(Sig owner, Sig.Field field) {
        Decl decl = field.decl();
        if (field.defined || field.isPrivate != null || field.isVariable != null || decl.names.size() != 1
                || decl.disjoint != null || decl.disjoint2 != null) throw new IllegalArgumentException("unsupported field");
        ObjectNode item = item("fields", "field", identities.get(field), shortName(field.label));
        item.put("ownerSignatureId", identities.get(owner));
        ArrayNode columns = item.putArray("rangeColumns");
        for (String column : schemas.fieldColumns(decl.expr)) columns.add(column);
        item.put("multiplicity", schemas.fieldMultiplicity(decl.expr));
    }

    /**
     * Recognizes Alloy's synthetic no-command helper.
     * @param function parser function
     * @return whether this helper is synthetic
     */
    private boolean synthetic(Func function) {
        return authoredCommands == 0 && function.label.equals("this/$$Default");
    }

    /** Reads predicates and their set-valued parameters before their bodies. */
    private void predicates() {
        for (Func pred : parsed.getAllFunc()) if (!synthetic(pred)) predicate(pred);
    }

    /**
     * Reads a single predicate declaration.
     * @param pred resolved predicate
     * @throws IllegalArgumentException for unsupported declarations
     */
    private void predicate(Func pred) {
        if (!pred.isPred || pred.isPrivate != null) throw new IllegalArgumentException("unsupported function: " + pred.label);
        ObjectNode item = item("predicates", "predicate", identities.get(pred), shortName(pred.label));
        ArrayNode params = item.putArray("parameters");
        for (Decl decl : pred.decls) parameter(params, decl);
        item.put("bodyId", expressions.read(pred.getBody()));
    }

    /**
     * Reads and binds one explicit set-valued parameter.
     * @param params output parameter array
     * @param decl parser declaration
     * @throws IllegalArgumentException for unsupported declarations
     */
    private void parameter(ArrayNode params, Decl decl) {
        if (decl.names.size() != 1 || decl.disjoint != null || decl.disjoint2 != null
                || decl.isPrivate != null || decl.isVar != null) throw new IllegalArgumentException("parameter shape");
        String id = id();
        ObjectNode item = params.addObject();
        item.put("tag", "parameter");
        item.put("id", id);
        item.put("name", decl.get().label);
        ArrayNode columns = item.putArray("columns");
        for (String column : schemas.parameter(decl.expr)) columns.add(column);
        expressions.bind(decl.get(), id);
    }

    /** Reads authored fact and assertion bodies before command expansion. */
    private void formulas() {
        for (Pair<String, Expr> fact : parsed.getAllFacts()) {
            ObjectNode item = item("facts", "fact", id(), shortName(fact.a));
            item.put("bodyId", expressions.read(fact.b));
        }
        for (Assert assertion : parsed.getAllAssertions()) {
            ObjectNode item = item("assertions", "assertion", identities.get(assertion), shortName(assertion.label));
            item.put("bodyId", expressions.read(assertion.expr));
        }
    }

    /**
     * Reads bounded commands after their authored tokens have been checked.
     * @param count number of explicit authored commands
     * @throws IllegalArgumentException for unsupported declarations
     */
    private void commands(int count) {
        if (count < 0 || count > 32 || (count > 0 && parsed.getAllCommands().size() != count)) {
            throw new IllegalArgumentException("command count");
        }
        if (count == 0) return;
        for (Command command : parsed.getAllCommands()) command(command);
    }

    /**
     * Records a resolved command with bounded options.
     * @param command Alloy command
     * @throws IllegalArgumentException for unsupported declarations
     */
    private void command(Command command) {
        String target = names.get(shortName(command.label));
        if (target == null || command.overall < 1 || command.overall > 5 || command.bitwidth != 4
                || command.maxseq != 3 || !command.scope.isEmpty() || command.expects >= 0) {
            throw new IllegalArgumentException("unsupported command");
        }
        ObjectNode item = module.withArray("commands").addObject();
        item.put("tag", command.check ? "check" : "run");
        item.put("id", id());
        item.put("targetId", target);
        item.put("uniformScope", command.overall);
        item.put("bitwidth", command.bitwidth);
        item.put("maxseq", command.maxseq);
    }

    /**
     * Creates a named declaration.
     * @param array module collection
     * @param tag declaration tag
     * @param id declaration identity
     * @param name declaration name
     * @throws IllegalArgumentException for unsupported declarations
     * @return new declaration object
     */
    private ObjectNode item(String array, String tag, String id, String name) {
        ObjectNode item = module.withArray(array).addObject();
        item.put("tag", tag);
        item.put("id", id);
        item.put("name", name);
        return item;
    }

    /**
     * Removes Alloy's module qualification from a declaration label.
     * @param label parser label
     * @return local declaration name
     */
    private String shortName(String label) {
        return label.substring(label.lastIndexOf('/') + 1);
    }

    /**
     * Allocates a server-owned declaration ID.
     * @return UUIDv4 identity
     */
    private String id() {
        return "server:" + UUID.randomUUID();
    }
}
