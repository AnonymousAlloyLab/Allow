package dev.allow.corpus;

import edu.mit.csail.sdg.alloy4.A4Reporter;
import edu.mit.csail.sdg.ast.Command;
import edu.mit.csail.sdg.ast.Expr;
import edu.mit.csail.sdg.parser.CompModule;
import edu.mit.csail.sdg.translator.A4Options;
import edu.mit.csail.sdg.translator.A4Solution;
import edu.mit.csail.sdg.translator.TranslateAlloyToKodkod;
import java.util.ArrayList;
import java.util.List;
import kodkod.engine.satlab.SATFactory;

/** Builds one bounded polarity pool from full validated solver solutions. */
final class PoolBuilder {
    /** Executes and enumerates a single polarity.
     * @param world original module
     * @param command generated bounded query
     * @param predicate target body
     * @param positive expected target truth
     * @param count desired unique instances
     * @return immutable evidence
     */
    Pool build(CompModule world, Command command, Expr predicate, boolean positive, int count) {
        List<String> members = new ArrayList<>();
        String existence = "UNKNOWN";
        int enumerated = 0;
        try {
            A4Options options = options();
            A4Solution solution = TranslateAlloyToKodkod.execute_command(
                    A4Reporter.NOP, world.getAllReachableSigs(), command, options);
            if (!solution.satisfiable()) return new Pool("UNSAT", "EXHAUSTED", members, 0);
            existence = "SAT";
            while (solution.satisfiable() && enumerated < 64) {
                enumerated++;
                if (!Boolean.TRUE.equals(solution.eval(world.getAllReachableFacts()))
                        || !Boolean.valueOf(positive).equals(solution.eval(predicate))) {
                    return new Pool(existence, "ERROR", members, enumerated);
                }
                String value = new InstanceCanonicalizer().project(world, solution);
                if (!members.contains(value)) members.add(value);
                if (members.size() == count) return new Pool(existence, "CAP_REACHED", members, enumerated);
                solution = solution.next();
            }
            return new Pool(existence, solution.satisfiable() ? "LIMIT" : "EXHAUSTED", members, enumerated);
        } catch (IllegalArgumentException limit) {
            return new Pool(existence, "LIMIT", members, enumerated);
        } catch (Exception | StackOverflowError failure) {
            return new Pool(existence, "ERROR", members, enumerated);
        }
    }

    /** Creates fixed local solver options.
     * @return bounded solver settings
     */
    private A4Options options() {
        A4Options options = new A4Options();
        options.solver = SATFactory.get("sat4j");
        options.noOverflow = true;
        options.decompose_mode = 0;
        options.tempDirectory = "/tmp";
        return options;
    }

    /** Immutable independent existence and enumeration outcomes.
     * @param existence initial solver state
     * @param termination enumeration stop
     * @param members canonical complete instances
     * @param enumerated number of visited solutions
     */
    record Pool(String existence, String termination, List<String> members, int enumerated) {
        Pool { members = List.copyOf(members); }
    }
}
