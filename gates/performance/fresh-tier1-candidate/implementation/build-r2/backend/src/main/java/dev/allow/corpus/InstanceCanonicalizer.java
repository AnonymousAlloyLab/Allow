package dev.allow.corpus;

import dev.allow.worker.JsonWire;
import edu.mit.csail.sdg.ast.Sig;
import edu.mit.csail.sdg.parser.CompModule;
import edu.mit.csail.sdg.translator.A4Solution;
import edu.mit.csail.sdg.translator.A4Tuple;
import edu.mit.csail.sdg.translator.A4TupleSet;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;

/** Canonicalizes complete static relational instances under a global atom bijection. */
final class InstanceCanonicalizer {
    private final List<String> atoms = new ArrayList<>();
    private final Map<String, String> integers = new HashMap<>();
    private final List<A4TupleSet> relations = new ArrayList<>();
    private String minimum;
    private int permutations;

    /** Projects and canonicalizes all signatures and fields.
     * @param world original parsed world
     * @param solution static satisfying solution
     * @return canonical anonymous JSON
     * @throws IllegalArgumentException unsupported instance or limit
     * @throws IOException serialization failure
     */
    String project(CompModule world, A4Solution solution) throws IOException {
        if (solution.getTraceLength() != 1) throw new IllegalArgumentException("trace=" + solution.getTraceLength());
        for (A4Tuple item : solution.eval(Sig.SIGINT)) integers.put(item.atom(0), item.atom(0));
        TreeSet<String> all = new TreeSet<>();
        for (Sig signature : world.getAllSigs()) {
            A4TupleSet set = solution.eval(signature);
            relations.add(set);
            for (A4Tuple tuple : set) all.add(tuple.atom(0));
            for (Sig.Field field : signature.getFields()) relations.add(solution.eval(field));
        }
        all.removeAll(integers.keySet());
        atoms.addAll(all);
        if (atoms.size() > 8) throw new IllegalArgumentException("ATOM_LIMIT");
        permute(new int[atoms.size()], new boolean[atoms.size()], 0);
        return minimum;
    }

    /** Enumerates all bijections, regardless of transient solver atom names.
     * @param permutation mapped ordinals
     * @param used ordinals already assigned
     * @param index next atom position
     * @throws IOException encoding failure
     */
    private void permute(int[] permutation, boolean[] used, int index) throws IOException {
        if (index == permutation.length) { consider(permutation); return; }
        for (int i = 0; i < used.length; i++) {
            if (!used[i]) {
                used[i] = true; permutation[index] = i;
                permute(permutation, used, index + 1);
                used[i] = false;
            }
        }
    }

    /** Serializes one complete permutation and retains its lexical minimum.
     * @param permutation global atom mapping
     * @throws IOException encoding failure
     * @throws IllegalArgumentException permutation limit
     */
    private void consider(int[] permutation) throws IOException {
        if (++permutations > 100000) throw new IllegalArgumentException("PERMUTATION_LIMIT");
        Map<String, String> mapping = new HashMap<>();
        for (int i = 0; i < atoms.size(); i++) mapping.put(atoms.get(i), "a" + permutation[i]);
        List<Object> encoded = new ArrayList<>();
        for (A4TupleSet relation : relations) encoded.add(rows(relation, mapping));
        String value = new String(JsonWire.encode(List.of("instance-v1", atoms.size(), encoded)),
                StandardCharsets.UTF_8);
        if (minimum == null || value.compareTo(minimum) < 0) minimum = value;
    }

    /** Encodes one relation including arity and empty relations.
     * @param relation full relation
     * @param mapping global atom mapping
     * @return canonical relation
     * @throws IllegalArgumentException unknown atom or encoding
     */
    private Object rows(A4TupleSet relation, Map<String, String> mapping) {
        List<String> tuples = new ArrayList<>();
        for (A4Tuple tuple : relation) {
            List<String> row = new ArrayList<>();
            for (int i = 0; i < tuple.arity(); i++) {
                String atom = tuple.atom(i);
                String mapped = mapping.get(atom);
                if (mapped == null && integers.containsKey(atom)) mapped = "i" + integers.get(atom);
                if (mapped == null) throw new IllegalArgumentException("UNKNOWN_ATOM");
                row.add(mapped);
            }
            try { tuples.add(new String(JsonWire.encode(row), StandardCharsets.UTF_8)); }
            catch (IOException error) { throw new IllegalArgumentException("ENCODING"); }
        }
        Collections.sort(tuples);
        return List.of(relation.arity(), tuples);
    }
}
