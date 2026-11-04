package dev.allow.worker;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;

/** Regression tests for the pre-resolver import boundary. */
class SourcePolicyTest {
    /** Rejects import tokens after every supported line-comment terminator. */
    @Test
    void rejectsImportsAfterLineComments() {
        for (String prefix : new String[]{"//", "--"}) {
            for (String newline : new String[]{"\n", "\r", "\r\n"}) {
                String source = prefix + " comment" + newline + "open util/boolean\nsig A {}";
                assertThrows(IllegalArgumentException.class, new Check(source)::run);
            }
        }
    }

    /** Preserves harmless comment, string and longer-identifier content. */
    @Test
    void permitsNonImportTokensInTriviaAndStrings() {
        for (String prefix : new String[]{"//", "--"}) {
            for (String newline : new String[]{"\n", "\r", "\r\n"}) {
                String source = prefix + " open util/boolean" + newline + "sig A {}";
                assertDoesNotThrow(new Check(source)::run);
            }
        }
        assertDoesNotThrow(new Check("/* open util/boolean */ sig A {}")::run);
        assertDoesNotThrow(new Check("\"open util/boolean\" sig opener {}")::run);
    }

    /** Named callback to exercise the preflight directly. */
    private static final class Check {
        private final String source;

        /**
         * Creates a preflight callback.
         * @param source exact input
         */
        private Check(String source) {
            this.source = source;
        }

        /** Runs preflight before any parser or resolver is invoked. */
        private void run() {
            SourcePolicy.check(source);
        }
    }
}
