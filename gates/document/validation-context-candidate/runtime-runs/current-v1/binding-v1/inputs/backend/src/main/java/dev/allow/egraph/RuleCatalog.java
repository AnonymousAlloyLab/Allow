package dev.allow.egraph;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
/** Pinned closed registry shared as data by matcher and independent replay.
     */
public final class RuleCatalog {
    private static final String APPROVED_SHA256 = "a017b226b0643e81a118b2e9879dcba2d5dadbe8dd54939d23ace8b725f30f34";
    private final List<Rewrite> rules;
    private final String digest;
    /** Loads the embedded catalog only; clients cannot provide rules.
     * @throws IllegalStateException when validation or resource checks reject the operation
     */
    public RuleCatalog() { this(loadEmbedded()); }
    /** Admits only exact frozen registry bytes, including through the test seam.
     * @param bytes candidate embedded catalog bytes
     * @throws IllegalStateException when catalog integrity or parsing fails
     */
    RuleCatalog(byte[] bytes) {
        byte[] snapshot = bytes.clone();
        digest = Wire.digest(snapshot);
        if (!APPROVED_SHA256.equals(digest)) throw new IllegalStateException("Unapproved rule registry");
        try {
            JsonNode tree = new ObjectMapper().readTree(snapshot);
            List<Rewrite> result = new ArrayList<>();
            for (JsonNode rule : tree.get("rules")) {
                result.add(new Rewrite(rule.get("id").asText(), rule.get("family").asText(),
                        rule.get("left"), rule.get("right")));
            }
            rules = List.copyOf(result);
            if (rules.size() != 34) throw new IllegalStateException("Invalid registry size");
        } catch (java.io.IOException error) { throw new IllegalStateException("Invalid registry", error); }
    }
    /** Reads the build-bound production resource without accepting caller paths.
     * @return exact embedded catalog bytes
     * @throws IllegalStateException when the embedded resource cannot be read
     */
    private static byte[] loadEmbedded() {
        try (var stream = RuleCatalog.class.getResourceAsStream("/profiles/egraph-rules.json")) {
            if (stream == null) throw new IllegalStateException("Missing rule registry");
            return stream.readAllBytes();
        } catch (java.io.IOException error) { throw new IllegalStateException("Unreadable rule registry", error); }
    }
    /** Returns immutable rules.
     * @return ordered registry
     */
    public List<Rewrite> rules() { return rules; }
    /** Returns exact registry identity.
     * @return catalog digest
     */
    public String digest() { return digest; }
    /** Looks up a closed rule identifier.
     * @param id registered identifier
     * @return matching rule
     * @throws IllegalArgumentException when validation or resource checks reject the operation
     */
    Rewrite rule(String id) {
        for (Rewrite rule : rules) if (rule.id().equals(id)) return rule;
        throw new IllegalArgumentException("Unknown rule");
    }
    /** Instantiates a finite pattern using one exact sort.
     * @param pattern pattern tree
     * @param bindings ground substitution
     * @param sort rule sort
     * @return concrete term
     * @throws IllegalArgumentException when validation or resource checks reject the operation
     */
    static Term instantiate(JsonNode pattern, Map<String, Term> bindings, Sort sort) {
        if (pattern.isTextual()) {
            Term result = bindings.get(pattern.asText());
            if (result == null || !result.sort().equals(sort)) throw new IllegalArgumentException("Bad substitution");
            return result;
        }
        List<Term> children = new ArrayList<>();
        for (int i = 1; i < pattern.size(); i++) children.add(instantiate(pattern.get(i), bindings, sort));
        return Term.node(pattern.get(0).asText(), sort, children);
    }
    /** Collects exact pattern variables.
     * @param pattern closed pattern
     * @return insertion ordered names
     */
    static Map<String, Boolean> variables(JsonNode pattern) {
        Map<String, Boolean> result = new LinkedHashMap<>();
        collect(pattern, result); return result;
    }
    /** Visits variable names.
     * @param pattern closed pattern
     * @param result accumulated names
     */
    private static void collect(JsonNode pattern, Map<String, Boolean> result) {
        if (pattern.isTextual()) result.put(pattern.asText(), true);
        else for (int i = 1; i < pattern.size(); i++) collect(pattern.get(i), result);
    }
    /** One frozen forward pattern pair.
     * @param id identifier
     * @param family sort family
     * @param left pattern
     * @param right replacement
     */
    public record Rewrite(String id, String family, JsonNode left, JsonNode right) {
        /** Copies mutable constructor patterns before retaining them.
         * @param id frozen rule identifier
         * @param family closed sort family
         * @param left source pattern tree
         * @param right replacement pattern tree
         */
        public Rewrite(String id, String family, JsonNode left, JsonNode right) {
            this.id = id;
            this.family = family;
            this.left = left.deepCopy();
            this.right = right.deepCopy();
        }
        /** Returns an independent pattern tree.
     * @return source pattern
     */
        public JsonNode left() { return left.deepCopy(); }
        /** Returns an independent replacement tree.
     * @return target pattern
     */
        public JsonNode right() { return right.deepCopy(); }
    }
}
