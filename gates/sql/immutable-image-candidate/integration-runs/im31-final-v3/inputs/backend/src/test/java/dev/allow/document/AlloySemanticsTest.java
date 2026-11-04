package dev.allow.document;

import edu.mit.csail.sdg.alloy4.A4Reporter;
import edu.mit.csail.sdg.ast.Command;
import edu.mit.csail.sdg.parser.CompModule;
import edu.mit.csail.sdg.parser.CompUtil;
import edu.mit.csail.sdg.translator.A4Options;
import edu.mit.csail.sdg.translator.A4Solution;
import edu.mit.csail.sdg.translator.TranslateAlloyToKodkod;
import kodkod.engine.satlab.SATFactory;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Finite SAT4J fixtures for the declared multiplicity and parameter policy. */
class AlloySemanticsTest {
    /**
     * Solves the first command of a tiny isolated fixture.
     * @param source complete Alloy module
     * @return whether the command is satisfiable
     * @throws Exception when Alloy or SAT4J fails
     */
    private boolean satisfiable(String source) throws Exception {
        CompModule module = CompUtil.parseEverything_fromString(A4Reporter.NOP, source);
        Command command = module.getAllCommands().get(0);
        A4Options options = new A4Options();
        options.solver = SATFactory.get("sat4j");
        A4Solution solution = TranslateAlloyToKodkod.execute_command(A4Reporter.NOP,
            module.getAllReachableSigs(), command, options);
        return solution.satisfiable();
    }

    /**
     * Checks per-owner one and some field requirements.
     * @throws Exception when Alloy or SAT4J fails
     */
    @Test
    void unaryMultiplicityConstrainsEveryOwner() throws Exception {
        String suffix = " sig B {} run { some a: A | no a.r } for 3";
        assertFalse(satisfiable("one sig A { r: one B }" + suffix));
        assertFalse(satisfiable("one sig A { r: some B }" + suffix));
        assertTrue(satisfiable("one sig A { r: set B }" + suffix));
    }

    /**
     * Checks that lone forbids two distinct range atoms for one owner.
     * @throws Exception when Alloy or SAT4J fails
     */
    @Test
    void loneRejectsTwoRangeAtoms() throws Exception {
        String suffix = " sig B {} run { some a: A | some disj b, c: B | b + c in a.r } for 3";
        assertFalse(satisfiable("one sig A { r: lone B }" + suffix));
        assertTrue(satisfiable("one sig A { r: set B }" + suffix));
    }

    /**
     * Checks that tuple-set fields may be empty or nonempty.
     * @throws Exception when Alloy or SAT4J fails
     */
    @Test
    void tupleSetAllowsBothCardinalities() throws Exception {
        String head = "one sig A { r: set (B -> C) } one sig B {} one sig C {} ";
        assertTrue(satisfiable(head + "run { no A.r } for 3"));
        assertTrue(satisfiable(head + "run { some A.r } for 3"));
    }

    /**
     * Checks set-valued binary predicate arguments with empty and nonempty tuples.
     * @throws Exception when Alloy or SAT4J fails
     */
    @Test
    void setTupleParametersReceiveRelations() throws Exception {
        String head = "one sig B {} one sig C {} pred p[x: set (B -> C)] { no x } ";
        assertFalse(satisfiable(head + "run { p[B -> C] } for 3"));
        assertTrue(satisfiable(head + "run { p[(B -> C) - (B -> C)] } for 3"));
    }
}
