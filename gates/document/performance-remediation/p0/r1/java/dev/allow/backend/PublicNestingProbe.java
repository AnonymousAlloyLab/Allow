package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import java.nio.charset.StandardCharsets;

/** Independent public-codec nesting fixtures; private Python depth has a different convention. */
public final class PublicNestingProbe {
    /** Prevents construction of the isolated test entry point. */
    private PublicNestingProbe() { }

    /** Executes literal container depths against the unchanged public request decoder.
     * @param args unused arguments
     * @throws AssertionError unexpected decode or closed-shape result
     */
    public static void main(String[] args) {
        for (int depth : new int[]{95, 96, 97, 299, 300, 301}) check(depth);
    }

    /** Distinguishes the Jackson container-depth guard from closed public envelope validation.
     * @param depth independently constructed number of nested array containers
     * @throws AssertionError a decoder boundary or closed-shape invariant differs
     */
    private static void check(int depth) {
        byte[] raw = ("[".repeat(depth) + "0" + "]".repeat(depth)).getBytes(StandardCharsets.UTF_8);
        boolean decoded = false;
        boolean shapeRejected = false;
        try {
            JsonNode value = DocumentJson.request(raw);
            decoded = true;
            try { DocumentJson.fields(value, "draftId", "draftEpoch", "baseRevision", "candidate"); }
            catch (IllegalArgumentException expected) { shapeRejected = true; }
        } catch (IllegalArgumentException expected) {
            if (depth <= 300) throw expected;
        }
        if (decoded != (depth <= 300) || (decoded && !shapeRejected)) {
            throw new AssertionError("Public nesting boundary mismatch at " + depth);
        }
        System.out.println("depth=" + depth + " decoded=" + decoded + " shapeRejected=" + shapeRejected);
    }
}
