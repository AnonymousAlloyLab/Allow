package dev.allow.canonical;

import com.fasterxml.jackson.databind.ObjectMapper;
import dev.allow.egraph.Context;
import dev.allow.egraph.EGraphEngine;
import dev.allow.egraph.EngineInput;
import dev.allow.egraph.IslandResult;
import dev.allow.egraph.RuleCatalog;
import dev.allow.egraph.Term;
import java.io.IOException;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

/** Adapts captured occurrences to independent bounded engine invocations.
     */
final class IslandAdapter {
    private static final ObjectMapper JSON = new ObjectMapper();
    private final IslandLowering lowering;
    /** Shares the original traversal's resolved declaration slots.
     * @param slots module identity registry
     */
    IslandAdapter(SlotRegistry slots) { lowering = new IslandLowering(slots); }

    /** Analyzes captured roots against their complete anonymous module context.
     * @param module module JSON
     * @param roots exact occurrence captures
     * @return bounded profile result
     */
    EgraphView analyze(String module, List<IslandCapture> roots) {
        long deadline = System.nanoTime() + 1_000_000_000L;
        List<IslandResult> results = new ArrayList<>();
        EGraphEngine engine = new EGraphEngine();
        String digest = new RuleCatalog().digest();
        boolean truncated = roots.size() > 16;
        for (IslandCapture root : roots.subList(0, Math.min(roots.size(), 16))) {
            IslandResult result = analyzeRoot(module, root, engine, deadline);
            List<IslandResult> proposed = new ArrayList<>(results);
            proposed.add(result);
            EgraphView candidate = new EgraphView("allow-egraph-v1", digest, "AVAILABLE", proposed, truncated);
            if (!fits(candidate)) {
                truncated = true;
                appendLimit(results, root.path(), digest);
                break;
            }
            results.add(result);
        }
        return new EgraphView("allow-egraph-v1", digest, "AVAILABLE", results, truncated);
    }

    /** Converts and checks a single island without affecting canonical output on failure.
     * @param module exact context
     * @param capture root occurrence
     * @param engine bounded engine
     * @param deadline shared deadline
     * @return result
     */
    private IslandResult analyzeRoot(String module, IslandCapture capture, EGraphEngine engine, long deadline) {
        try {
            if (System.nanoTime() >= deadline) { return unavailable(capture.path(), "TIME_LIMIT"); }
            Term root = lowering.lower(capture.expression(), capture.tree());
            if (root.cost() > 2048) { return unavailable(capture.path(), "INPUT_LIMIT"); }
            List<Term> atoms = new ArrayList<>();
            collect(root, atoms);
            atoms = atoms.stream().distinct().sorted(Comparator.comparing(Context::atomKey)).toList();
            Context context = new Context(module, capture.path(), atoms);
            return engine.analyze(new EngineInput(context, root), deadline);
        } catch (IslandLimit failure) {
            return unavailable(capture.path(), "INPUT_LIMIT");
        } catch (RuntimeException failure) {
            return unavailable(capture.path(), "ERROR");
        }
    }

    /** Records exact atom leaves from the lowered input.
     * @param term input term
     * @param atoms accumulator
     */
    private void collect(Term term, List<Term> atoms) {
        if (term.op().equals("ATOM")) { atoms.add(term); return; }
        for (Term child : term.children()) { collect(child, atoms); }
    }

    /** Adds a bounded explicit limit sentinel, dropping prior results only if needed.
     * @param results retained islands
     * @param path omitted root path
     * @param digest ruleset identity
     */
    void appendLimit(List<IslandResult> results, List<Integer> path, String digest) {
        IslandResult sentinel = unavailable(path, "OUTPUT_LIMIT");
        while (true) {
            List<IslandResult> candidate = new ArrayList<>(results);
            candidate.add(sentinel);
            if (fits(new EgraphView("allow-egraph-v1", digest, "AVAILABLE", candidate, true))) {
                results.add(sentinel);
                return;
            }
            if (results.isEmpty()) { return; }
            results.remove(results.size() - 1);
        }
    }

    /** Checks serialized byte size without materializing an unbounded string.
     * @param value result envelope
     * @return whether serialization fits the output cap
     */
    static boolean fits(Object value) {
        try { JSON.writeValue(new CappedOutput(), value); return true; }
        catch (IOException failure) { return false; }
    }

    /** Counts UTF-8 bytes and stops serialization at the fixed output limit. */
    private static final class CappedOutput extends OutputStream {
        private int count;
        /** Counts one serialized byte.
         * @param value byte value
         * @throws IOException if the result exceeds its cap
         */
        @Override
        public void write(int value) throws IOException { count(1); }

        /** Counts a serialized byte span.
         * @param bytes source buffer
         * @param offset first byte
         * @param length number of bytes
         * @throws IOException if the result exceeds its cap
         */
        @Override
        public void write(byte[] bytes, int offset, int length) throws IOException { count(length); }

        /** Rejects output above the fixed byte limit.
         * @param amount additional bytes
         * @throws IOException if the limit is exceeded
         */
        private void count(int amount) throws IOException {
            if (amount > 524288 - count) { throw new IOException("Output limit"); }
            count += amount;
        }
    }

    /** Constructs an explicit no-claim island result.
     * @param path exact root path
     * @param reason bounded failure
     * @return unavailable result
     */
    private IslandResult unavailable(List<Integer> path, String reason) {
        return new IslandResult(path, "UNAVAILABLE", reason, null, null, null, null,
                Map.of(), Map.of(), Map.of(), null);
    }
}
