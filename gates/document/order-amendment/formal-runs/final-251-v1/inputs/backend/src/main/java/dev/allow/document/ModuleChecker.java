package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Checks the closed syntax forest and its independently derived nominal types. */
final class ModuleChecker {
    private final JsonNode module;
    private final Map<String, JsonNode> nodes = new HashMap<>();
    private final Map<String, String> kinds = new HashMap<>();
    private final Map<String, List<String>> schemas = new HashMap<>();
    private final Map<String, JsonNode> predicates = new HashMap<>();
    private final Set<String> names = new HashSet<>();
    private final Set<String> seen = new HashSet<>();
    private final Set<String> active = new HashSet<>();
    private final Map<String, Set<String>> calls = new HashMap<>();
    private int declarations;

    /**
     * Creates a checker over one immutable candidate.
     * @param module complete wire module
     */
    ModuleChecker(JsonNode module) {
        this.module = module;
    }

    /**
     * Checks all declarations, bodies and ownership.
     * @throws IllegalArgumentException on invalid input
     */
    void check() {
        shape(module, "version", "signatures", "fields", "predicates", "facts", "assertions", "commands", "nodes");
        if (!module.path("version").isInt() || module.path("version").intValue() != 1) fail("version");
        collect();
        declarations();
        bodies();
        if (seen.size() != nodes.size()) fail("unreachable expression");
        for (String id : predicates.keySet()) dependency(id, new HashSet<>(), new HashSet<>());
    }

    /** Collects declaration identities before resolving references. */
    private void collect() {
        collectArray("signatures", "signature");
        collectArray("fields", "field");
        collectArray("predicates", "predicate");
        collectArray("facts", "fact");
        collectArray("assertions", "assertion");
        collectArray("commands", null);
        JsonNode all = array(module, "nodes", 512);
        for (JsonNode node : all) {
            String id = register(node, "expression");
            nodes.put(id, node);
        }
        if (declarations > 128) fail("declaration limit");
    }

    /**
     * Registers an ordered declaration collection.
     * @param key module array name
     * @param tag required tag, or null for commands
     */
    private void collectArray(String key, String tag) {
        for (JsonNode item : array(module, key, 128)) {
            String kind = tag == null ? text(item, "tag") : tag;
            if (!kind.equals(text(item, "tag"))) fail("declaration tag");
            if (tag == null && !kind.equals("run") && !kind.equals("check")) fail("command tag");
            String id = register(item, tag == null ? "command" : kind);
            if (kind.equals("predicate")) predicates.put(id, item);
            declarations++;
        }
    }

    /** Checks declarations against the complete signature environment. */
    private void declarations() {
        for (JsonNode s : module.path("signatures")) signature(s);
        for (JsonNode f : module.path("fields")) field(f);
        for (JsonNode p : module.path("predicates")) predicate(p);
        for (JsonNode f : module.path("facts")) namedBody(f);
        for (JsonNode a : module.path("assertions")) namedBody(a);
        for (JsonNode c : module.path("commands")) command(c);
    }

    /**
     * Checks a signature declaration.
     * @param s signature
     */
    private void signature(JsonNode s) {
        shape(s, "tag", "id", "name", "multiplicity");
        name(s);
        multiplicity(s);
        schemas.put(text(s, "id"), List.of(text(s, "id")));
    }

    /**
     * Checks a field and derives its owner-prefixed schema.
     * @param f field
     */
    private void field(JsonNode f) {
        shape(f, "tag", "id", "name", "ownerSignatureId", "rangeColumns", "multiplicity");
        name(f);
        String owner = text(f, "ownerSignatureId");
        requireKind(owner, "signature");
        List<String> range = schema(f.path("rangeColumns"));
        if (range.size() >= 8) fail("field arity");
        String multiplicity = multiplicity(f);
        if (range.size() > 1 && !multiplicity.equals("set")) fail("tuple multiplicity");
        List<String> result = new ArrayList<>();
        result.add(owner);
        result.addAll(range);
        schemas.put(text(f, "id"), List.copyOf(result));
    }

    /**
     * Checks predicate parameters and their declarations.
     * @param p predicate
     */
    private void predicate(JsonNode p) {
        shape(p, "tag", "id", "name", "parameters", "bodyId");
        name(p);
        for (JsonNode param : array(p, "parameters", 16)) {
            shape(param, "tag", "id", "name", "columns");
            if (!text(param, "tag").equals("parameter")) fail("parameter tag");
            String id = register(param, "binder");
            name(param);
            schemas.put(id, schema(param.path("columns")));
        }
    }

    /**
     * Checks a named formula declaration.
     * @param n fact or assertion
     */
    private void namedBody(JsonNode n) {
        shape(n, "tag", "id", "name", "bodyId");
        name(n);
    }

    /**
     * Checks a command's target and bounds.
     * @param c command
     */
    private void command(JsonNode c) {
        shape(c, "tag", "id", "targetId", "uniformScope", "bitwidth", "maxseq");
        String target = text(c, "targetId");
        String tag = text(c, "tag");
        requireKind(target, tag.equals("run") ? "predicate" : "assertion");
        if (tag.equals("run") && predicates.get(target).path("parameters").size() != 0) fail("run target");
        if (!integer(c, "uniformScope", 1, 5) || !integer(c, "bitwidth", 4, 4)
                || !integer(c, "maxseq", 3, 3)) fail("command bounds");
    }

    /** Checks every root and lexical environment. */
    private void bodies() {
        for (JsonNode p : module.path("predicates")) {
            Map<String, List<String>> env = new HashMap<>();
            for (JsonNode param : p.path("parameters")) env.put(text(param, "id"), schemas.get(text(param, "id")));
            calls.put(text(p, "id"), new HashSet<>());
            formula(expression(text(p, "bodyId"), env, text(p, "id"), 1));
        }
        for (JsonNode f : module.path("facts")) formula(expression(text(f, "bodyId"), Map.of(), "", 1));
        for (JsonNode a : module.path("assertions")) formula(expression(text(a, "bodyId"), Map.of(), "", 1));
    }

    /**
     * Derives an expression type while enforcing forest ownership.
     * @param id expression identity
     * @param env lexical binders
     * @param caller enclosing predicate, if any
     * @param depth root-relative depth
     * @return relation schema, or empty list for a formula
     */
    private List<String> expression(String id, Map<String, List<String>> env, String caller, int depth) {
        if (depth > 32 || !nodes.containsKey(id) || !seen.add(id) || !active.add(id)) fail("forest");
        JsonNode n = nodes.get(id);
        String tag = text(n, "tag");
        List<String> result;
        if (tag.endsWith("_ref")) result = reference(n, tag, env);
        else if (tag.equals("predicate_call")) result = call(n, env, caller, depth);
        else if (tag.equals("all_quant") || tag.equals("some_quant")) result = quantifier(n, env, caller, depth);
        else if (Set.of("not", "some_test", "no_test", "one_test", "lone_test", "transpose").contains(tag)) {
            result = unary(n, tag, env, caller, depth);
        } else result = binary(n, tag, env, caller, depth);
        active.remove(id);
        return result;
    }

    /**
     * Derives a reference type.
     * @param n node
     * @param tag operator
     * @param env lexical binders
     * @return nominal schema
     */
    private List<String> reference(JsonNode n, String tag, Map<String, List<String>> env) {
        shape(n, "id", "tag", "targetId");
        String target = text(n, "targetId");
        if (tag.equals("variable_ref")) {
            if (!env.containsKey(target)) fail("unbound binder");
            return env.get(target);
        }
        String kind = tag.equals("signature_ref") ? "signature" : tag.equals("field_ref") ? "field" : "unknown";
        requireKind(target, kind);
        return schemas.get(target);
    }

    /**
     * Checks one predicate invocation.
     * @param n call node
     * @param env lexical binders
     * @param caller enclosing predicate
     * @param depth current depth
     * @return formula type
     */
    private List<String> call(JsonNode n, Map<String, List<String>> env, String caller, int depth) {
        shape(n, "tag", "id", "predicateId", "arguments");
        String target = text(n, "predicateId");
        requireKind(target, "predicate");
        JsonNode args = array(n, "arguments", 16);
        JsonNode params = predicates.get(target).path("parameters");
        if (args.size() != params.size()) fail("call arity");
        for (int i = 0; i < args.size(); i++) {
            if (!args.get(i).isTextual()) fail("argument id");
            List<String> actual = expression(args.get(i).textValue(), env, caller, depth + 1);
            if (!actual.equals(schemas.get(text(params.get(i), "id")))) fail("call schema");
        }
        if (!caller.isEmpty()) calls.get(caller).add(target);
        return List.of();
    }

    /**
     * Checks a quantifier and extends only its body scope.
     * @param n quantifier
     * @param env outer environment
     * @param caller enclosing predicate
     * @param depth current depth
     * @return formula type
     */
    private List<String> quantifier(JsonNode n, Map<String, List<String>> env, String caller, int depth) {
        shape(n, "tag", "id", "binder", "bodyId");
        JsonNode binder = n.path("binder");
        shape(binder, "id", "name", "signatureId");
        String id = register(binder, "binder");
        name(binder);
        String signature = text(binder, "signatureId");
        requireKind(signature, "signature");
        Map<String, List<String>> extended = new HashMap<>(env);
        extended.put(id, List.of(signature));
        formula(expression(text(n, "bodyId"), extended, caller, depth + 1));
        return List.of();
    }

    /**
     * Checks unary operators.
     * @param n unary node
     * @param tag operator
     * @param env lexical binders
     * @param caller enclosing predicate
     * @param depth current depth
     * @return derived type
     */
    private List<String> unary(JsonNode n, String tag, Map<String, List<String>> env, String caller, int depth) {
        shape(n, "tag", "id", "operandId");
        List<String> value = expression(text(n, "operandId"), env, caller, depth + 1);
        if (tag.equals("not")) formula(value);
        else if (tag.equals("transpose")) {
            if (value.size() != 2) fail("transpose arity");
            return List.of(value.get(1), value.get(0));
        } else relation(value);
        return List.of();
    }

    /**
     * Checks binary operators.
     * @param n binary node
     * @param tag operator
     * @param env lexical binders
     * @param caller enclosing predicate
     * @param depth current depth
     * @return derived type
     */
    private List<String> binary(JsonNode n, String tag, Map<String, List<String>> env, String caller, int depth) {
        shape(n, "tag", "id", "leftId", "rightId");
        List<String> left = expression(text(n, "leftId"), env, caller, depth + 1);
        List<String> right = expression(text(n, "rightId"), env, caller, depth + 1);
        if (Set.of("and", "or", "implies", "iff").contains(tag)) {
            formula(left);
            formula(right);
            return List.of();
        }
        relation(left);
        relation(right);
        if (tag.equals("join") || tag.equals("product")) return combine(tag, left, right);
        if (!Set.of("equal", "subset", "union", "intersection", "difference").contains(tag)) fail("unknown tag");
        if (!left.equals(right)) fail("schema mismatch");
        return tag.equals("equal") || tag.equals("subset") ? List.of() : left;
    }

    /**
     * Derives join or product output columns.
     * @param tag operator
     * @param left left schema
     * @param right right schema
     * @return nonempty bounded output schema
     */
    private List<String> combine(String tag, List<String> left, List<String> right) {
        List<String> result = new ArrayList<>();
        if (tag.equals("join")) {
            if (!left.get(left.size() - 1).equals(right.get(0))) fail("join endpoint");
            result.addAll(left.subList(0, left.size() - 1));
            result.addAll(right.subList(1, right.size()));
        } else {
            result.addAll(left);
            result.addAll(right);
        }
        if (result.isEmpty() || result.size() > 8) fail("result arity");
        return List.copyOf(result);
    }

    /**
     * Rejects recursive predicate dependencies.
     * @param id current predicate
     * @param stack active path
     * @param done completed nodes
     */
    private void dependency(String id, Set<String> stack, Set<String> done) {
        if (done.contains(id)) return;
        if (!stack.add(id)) fail("recursive predicate");
        for (String next : calls.get(id)) dependency(next, stack, done);
        stack.remove(id);
        done.add(id);
    }

    /**
     * Registers an identity uniquely across all namespaces.
     * @param n identity owner
     * @param kind identity kind
     * @return identity
     */
    private String register(JsonNode n, String kind) {
        String id = text(n, "id");
        if (!id.matches("(?:server|draft):[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")) {
            fail("invalid id");
        }
        if (kinds.putIfAbsent(id, kind) != null) fail("duplicate id");
        return id;
    }

    /**
     * Validates and records a globally unique profile name.
     * @param n named declaration
     */
    private void name(JsonNode n) {
        String name = text(n, "name");
        if (!name.matches("[A-Za-z][A-Za-z0-9_]{0,63}") || name.startsWith("allow_")
                || RESERVED.contains(name) || !names.add(name)) fail("invalid or duplicate name");
    }

    private static final Set<String> RESERVED = Set.of("sig", "one", "lone", "some", "no", "all", "fact", "pred", "run", "check", "and", "or", "not", "implies", "univ", "none", "Int", "abstract", "as", "assert", "but", "disj", "else", "enum", "exactly", "expect", "extends", "for", "fun", "iden", "iff", "in", "let", "module", "open", "private", "seq", "set", "sum", "this", "var", "always", "eventually", "after", "before", "until", "releases", "historically", "once", "since", "triggered");

    /**
     * Validates a nonempty ordered signature schema.
     * @param value JSON array
     * @return immutable signature IDs
     */
    private List<String> schema(JsonNode value) {
        if (!value.isArray() || value.isEmpty() || value.size() > 8) fail("schema");
        List<String> result = new ArrayList<>();
        for (JsonNode item : value) {
            if (!item.isTextual()) fail("schema id");
            requireKind(item.textValue(), "signature");
            result.add(item.textValue());
        }
        return List.copyOf(result);
    }

    /**
     * Validates a declared multiplicity.
     * @param n declaration
     * @return multiplicity
     */
    private String multiplicity(JsonNode n) {
        String value = text(n, "multiplicity");
        if (!Set.of("set", "one", "lone", "some").contains(value)) fail("multiplicity");
        return value;
    }

    /**
     * Requires an identity of the expected declaration kind.
     * @param id referenced identity
     * @param kind required kind
     */
    private void requireKind(String id, String kind) {
        if (!kind.equals(kinds.get(id))) fail("unknown or wrong-kind reference");
    }

    /**
     * Requires a closed JSON object.
     * @param n object
     * @param fields exact required fields
     */
    private static void shape(JsonNode n, String... fields) {
        if (!n.isObject() || n.size() != fields.length) fail("object shape");
        for (String field : fields) if (!n.has(field) || n.get(field).isNull()) fail("object field");
    }

    /**
     * Reads a bounded required array.
     * @param n parent
     * @param key property
     * @param max maximum elements
     * @return array
     */
    private static JsonNode array(JsonNode n, String key, int max) {
        JsonNode value = n.path(key);
        if (!value.isArray() || value.size() > max) fail("array " + key);
        return value;
    }

    /**
     * Reads a required string.
     * @param n parent
     * @param key property
     * @return string
     */
    private static String text(JsonNode n, String key) {
        JsonNode value = n.path(key);
        if (!value.isTextual()) fail("string " + key);
        return value.textValue();
    }

    /**
     * Tests a bounded JSON integer.
     * @param n parent
     * @param key property
     * @param low inclusive minimum
     * @param high inclusive maximum
     * @return whether the value is in range
     */
    private static boolean integer(JsonNode n, String key, int low, int high) {
        JsonNode value = n.path(key);
        return value.isIntegralNumber() && value.canConvertToInt() && value.intValue() >= low && value.intValue() <= high;
    }

    /**
     * Requires a formula type.
     * @param type derived type
     */
    private static void formula(List<String> type) {
        if (!type.isEmpty()) fail("expected formula");
    }

    /**
     * Requires a relation type.
     * @param type derived type
     */
    private static void relation(List<String> type) {
        if (type.isEmpty()) fail("expected relation");
    }

    /**
     * Rejects the candidate.
     * @param message diagnostic category
     * @throws IllegalArgumentException always
     */
    private static void fail(String message) {
        throw new IllegalArgumentException(message);
    }
}
