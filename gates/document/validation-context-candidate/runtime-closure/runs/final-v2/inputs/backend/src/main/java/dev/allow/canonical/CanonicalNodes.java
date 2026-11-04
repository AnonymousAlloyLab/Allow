package dev.allow.canonical;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/** Builds positional nodes with explicit tags and immutable child arrays. */
final class CanonicalNodes {
    /** Prevents instantiation of the structural node utility. */
    private CanonicalNodes() { }

    /** Builds one tagged node, retaining null as an explicit optional field.
     * @param tag trusted closed grammar tag
     * @param values ordered structural children
     * @return immutable positional node
     */
    static List<Object> node(String tag, Object... values) {
        List<Object> node = new ArrayList<>();
        node.add(tag);
        node.addAll(Arrays.asList(values));
        return Collections.unmodifiableList(node);
    }
}
