package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.Hashes;
import dev.allow.worker.JsonWire;
import dev.allow.worker.WitnessProjector;
import edu.mit.csail.sdg.alloy4.A4Reporter;
import edu.mit.csail.sdg.alloy4.Err;
import edu.mit.csail.sdg.alloy4.Pos;
import edu.mit.csail.sdg.ast.*;
import edu.mit.csail.sdg.parser.CompModule;
import edu.mit.csail.sdg.translator.*;
import java.io.IOException;
import java.util.*;
import kodkod.engine.satlab.SATFactory;

/** Four sequential real SAT4J queries with assignment-bound independent witness replay. */
final class ComparisonSolver {
    private final ComparisonSyntax syntax;
    private final Map<String, String> originalIds;
    private final CompModule world;
    private final String source;

    /** Parses and checks the entire synthesized source inside the worker.
     * @param module complete independently validated forest
     * @param left first formula identity
     * @param right second formula identity
     * @param scope shared bounded scope
     * @param originalIds checked-to-original identity mapping
     * @throws Err synthesis rejected by Alloy
     * @throws IOException isolated parser failure
     */
    ComparisonSolver(JsonNode module, String left, String right, int scope, Map<String, String> originalIds) throws Err, IOException {
        this.originalIds = Map.copyOf(originalIds);
        new ModuleChecker(module).check();
        syntax = new ComparisonSyntax(module);
        source = syntax.source(left, right, scope);
        world = SourceParser.parse(source);
    }

    /** Solves every category sequentially; only a complete response can leave the worker.
     * @return bounded complete category partition
     * @throws Err solver failure
     * @throws IOException serialization failure
     */
    ObjectNode solve() throws Err, IOException {
        ObjectNode result = JsonNodeFactory.instance.objectNode().put("synthesizedSourceHash", Hashes.text(source));
        ObjectNode categories = result.putObject("categories");
        String[] names = {"both", "leftOnly", "rightOnly", "neither"};
        for (int index = 0; index < 4; index++) categories.set(names[index], category(index));
        boolean all = true;
        for (JsonNode category : categories) all &= category.path("status").asText().equals("UNSAT");
        boolean difference = categories.path("leftOnly").path("status").asText().equals("SAT")
                || categories.path("rightOnly").path("status").asText().equals("SAT");
        result.put("classification", all ? "NO_INSTANCES" : difference ? "DISTINGUISHED" : "AGREEMENT");
        return result;
    }

    /** Executes one pure Java solver call with the original explicit bounds.
     * @param index category truth pair index
     * @return SAT evidence or bounded UNSAT
     * @throws Err solver/evaluation failure
     * @throws IOException witness serialization failure
     * @throws IllegalStateException solver or replay mismatch
     */
    private ObjectNode category(int index) throws Err, IOException {
        A4Options options = new A4Options();
        options.solver = SATFactory.get("sat4j"); options.noOverflow = true;
        options.decompose_mode = 0; options.tempDirectory = "/tmp"; options.skolemDepth = 1;
        A4Solution solution = TranslateAlloyToKodkod.execute_command(A4Reporter.NOP, world.getAllReachableSigs(),
                world.getAllCommands().get(index), options);
        if (solution == null) throw new IllegalStateException("Missing solver outcome");
        ObjectNode result = JsonNodeFactory.instance.objectNode().put("status", solution.satisfiable() ? "SAT" : "UNSAT");
        if (!solution.satisfiable()) return result;
        List<Expr> arguments = assignments(solution);
        boolean left = replay(solution, "Left", arguments), right = replay(solution, "Right", arguments);
        if (left != (index < 2) || right != (index == 0 || index == 2)) throw new IllegalStateException("Comparison witness replay failed");
        result.put("left", left).put("right", right);
        result.set("witness", JsonWire.decode(JsonWire.encode(new WitnessProjector().project(solution)), JsonNode.class));
        String assignmentHash = assignmentHash(solution, arguments);
        result.set("assignment", assignmentProjection(solution, arguments, true));
        String identity = result.path("witness").path("fullInstanceHash").asText();
        result.put("evidenceHash", Hashes.text(Hashes.text(source) + ":" + index + ":" + left + ":" + right
                + ":" + identity + ":" + assignmentHash));
        ComparisonDisplay.bound(result);
        return result;
    }

    /** Resolves only exact generated skolems, requiring one binding per original free identity.
     * @param solution exact satisfying solution
     * @return positional expressions for direct replay
     * @throws IllegalStateException absent or ambiguous assignment
     */
    private List<Expr> assignments(A4Solution solution) {
        List<Expr> result = new ArrayList<>();
        for (String name : syntax.variableNames()) {
            ExprVar found = null;
            for (ExprVar skolem : solution.getAllSkolems()) {
                if (!skolem.label.endsWith("_" + name)) continue;
                if (found != null) throw new IllegalStateException("Ambiguous comparison assignment");
                found = skolem;
            }
            if (found == null) throw new IllegalStateException("Missing comparison assignment");
            result.add(found);
        }
        return result;
    }

    /** Independently evaluates a helper formula on the exact satisfying assignment.
     * @param solution exact category solution
     * @param suffix left/right helper suffix
     * @param arguments shared skolem expressions
     * @return independently evaluated truth
     * @throws Err evaluation failed
     * @throws IllegalStateException missing helper or nonboolean result
     */
    private boolean replay(A4Solution solution, String suffix, List<Expr> arguments) throws Err {
        Func helper = null;
        for (Func function : world.getAllFunc()) if (function.label.equals("this/" + syntax.prefix() + suffix)) helper = function;
        if (helper == null) throw new IllegalStateException("Missing replay helper");
        Object value = solution.eval(ExprCall.make(Pos.UNKNOWN, Pos.UNKNOWN, helper, arguments, 0));
        if (!(value instanceof Boolean)) throw new IllegalStateException("Nonboolean replay result");
        return (Boolean) value;
    }

    /** Hashes every assignment tuple without allocating an unbounded JSON projection.
     * @param solution exact satisfying solution
     * @param arguments positional skolem expressions
     * @return full assignment identity
     * @throws Err evaluation failure
     */
    private String assignmentHash(A4Solution solution, List<Expr> arguments) throws Err {
        java.security.MessageDigest digest = Hashes.digest();
        List<String> ids = syntax.variables();
        for (int index = 0; index < ids.size(); index++) {
            String id = ids.get(index);
            hash(digest, originalIds.getOrDefault(id, id)); hash(digest, syntax.name(id));
            for (String column : syntax.columns(id)) hash(digest, column);
            A4TupleSet values = (A4TupleSet) solution.eval(arguments.get(index));
            hash(digest, Integer.toString(values.size())); hash(digest, Integer.toString(values.arity()));
            for (A4Tuple tuple : values) for (int column = 0; column < tuple.arity(); column++) hash(digest, tuple.atom(column));
        }
        return java.util.HexFormat.of().formatHex(digest.digest());
    }

    /** Adds one unambiguous byte-length-prefixed assignment component.
     * @param digest full assignment digest
     * @param value component text
     */
    private void hash(java.security.MessageDigest digest, String value) {
        byte[] bytes = value.getBytes(java.nio.charset.StandardCharsets.UTF_8);
        digest.update(Integer.toString(bytes.length).getBytes(java.nio.charset.StandardCharsets.US_ASCII));
        digest.update((byte) ':'); digest.update(bytes);
    }

    /** Projects original lexical identities and schemas while hashing all assignment tuples.
     * @param solution exact category solution
     * @param arguments positional bound skolems
     * @param bounded whether display limits apply
     * @return ordered assignment descriptors
     * @throws Err assignment evaluation failed
     */
    private ArrayNode assignmentProjection(A4Solution solution, List<Expr> arguments, boolean bounded) throws Err {
        ArrayNode result = JsonNodeFactory.instance.arrayNode();
        List<String> ids = syntax.variables();
        for (int index = 0; index < ids.size(); index++) {
            String id = ids.get(index);
            ObjectNode item = result.addObject().put("id", originalIds.getOrDefault(id, id)).put("name", syntax.name(id));
            ArrayNode columns = item.putArray("columns");
            for (String column : syntax.columns(id)) columns.add(column);
            A4TupleSet values = (A4TupleSet) solution.eval(arguments.get(index));
            item.put("truncated", bounded && values.size() > 1000);
            ArrayNode tuples = item.putArray("tuples");
            for (A4Tuple tuple : values) {
                if (bounded && tuples.size() >= 1000) break;
                ArrayNode row = tuples.addArray();
                for (int column = 0; column < tuple.arity(); column++) row.add(tuple.atom(column));
            }
        }
        return result;
    }
}
