package dev.allow.worker;

import dev.allow.dto.*;
import edu.mit.csail.sdg.ast.Sig;
import edu.mit.csail.sdg.translator.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

/** Full-trace identity is computed separately from the bounded display. */
final class WitnessProjector {
    private final MessageDigest digest = Hashes.digest();
    private boolean truncated;

    /**
     * Projects a real SAT witness without combining trace states.
     * @param solution SAT solution
     * @return display plus complete identity
     */
    WitnessView project(A4Solution solution) {
        List<StateView> states = new ArrayList<>();
        hash(Integer.toString(solution.getTraceLength()));
        hash(Integer.toString(solution.getLoopState()));
        for (int state = 0; state < solution.getTraceLength(); state++) {
            hash(Integer.toString(state));
            StateView view = state(solution, state);
            if (state < 10) states.add(view);
            else truncated = true;
        }
        return new WitnessView(states, solution.getTraceLength(), solution.getLoopState(),
                truncated, HexFormat.of().formatHex(digest.digest()));
    }

    /**
     * Projects one state while retaining distinct memberships.
     * @param solution instance
     * @param state index
     * @return bounded state
     */
    private StateView state(A4Solution solution, int state) {
        Map<String, List<String>> members = new TreeMap<>();
        List<RelationView> relations = new ArrayList<>();
        for (Sig signature : solution.getAllReachableSigs()) {
            hash("signature");
            hash(signature.label);
            hash(Integer.toString(solution.eval(signature, state).size()));
            for (A4Tuple tuple : solution.eval(signature, state)) {
                hash(tuple.atom(0));
                if (members.size() < 1000 || members.containsKey(tuple.atom(0))) {
                    members.computeIfAbsent(tuple.atom(0), WitnessProjector::newMembership).add(signature.label);
                } else truncated = true;
            }
            for (Sig.Field field : signature.getFields()) {
                RelationView relation = relation(solution, state, signature.label + "." + field.label, field);
                if (relations.size() < 128) relations.add(relation);
                else truncated = true;
            }
        }
        List<AtomView> atoms = new ArrayList<>();
        for (Map.Entry<String, List<String>> item : members.entrySet()) {
            atoms.add(new AtomView(item.getKey(), item.getValue()));
        }
        return new StateView(atoms, relations);
    }

    /**
     * Creates a private membership accumulator.
     * @param ignored atom id
     * @return mutable local list
     */
    private static List<String> newMembership(String ignored) {
        return new ArrayList<>();
    }

    /**
     * Hashes all tuple positions, displaying at most 1000 rows per relation.
     * @param solution instance
     * @param state index
     * @param name exact field identity
     * @param field parsed field
     * @return relation
     */
    private RelationView relation(A4Solution solution, int state, String name, Sig.Field field) {
        A4TupleSet values = solution.eval(field, state);
        List<List<String>> rows = new ArrayList<>();
        hash(name);
        hash(Integer.toString(values.arity()));
        hash(Integer.toString(values.size()));
        for (A4Tuple tuple : values) {
            List<String> row = new ArrayList<>();
            for (int column = 0; column < tuple.arity(); column++) {
                hash(tuple.atom(column));
                if (rows.size() < 1000) row.add(tuple.atom(column));
            }
            if (rows.size() < 1000) rows.add(row);
            else truncated = true;
        }
        return new RelationView(name, values.arity(), rows);
    }

    /**
     * Uses byte-length prefixes to avoid ambiguous concatenation.
     * @param value exact identity fragment
     */
    private void hash(String value) {
        byte[] bytes = value.getBytes(StandardCharsets.UTF_8);
        digest.update(Integer.toString(bytes.length).getBytes(StandardCharsets.US_ASCII));
        digest.update((byte) ':');
        digest.update(bytes);
    }
}
