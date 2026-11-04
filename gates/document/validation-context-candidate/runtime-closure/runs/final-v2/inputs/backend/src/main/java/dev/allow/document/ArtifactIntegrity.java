package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import dev.allow.worker.SourcePolicy;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HashMap;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.Map;
import java.util.Set;

/** Checks source-bound stored artifact contents before historical revalidation. */
final class ArtifactIntegrity {
    private final JsonNode artifact;
    private final String source;
    private Utf8Offsets offsets;
    private final Map<String, JsonNode> nodes = new HashMap<>();
    private final Map<String, String> names = new HashMap<>();
    private final Set<String> declarations = new HashSet<>();
    private final Set<String> binders = new HashSet<>();

    /**
     * Creates a verifier over an authorized immutable artifact.
     * @param artifact stored artifact snapshot
     */
    ArtifactIntegrity(JsonNode artifact) {
        this.artifact = artifact;
        this.source = artifact.path("source").asText();
    }

    /**
     * Checks exact source digest, scope-free map bounds and comment token bytes.
     * @throws IllegalArgumentException when stored content is inconsistent
     */
    void check() {
        if (!artifact.path("source").isTextual() || !artifact.path("sourceHash").isTextual()) {
            throw new IllegalArgumentException("missing source identity");
        }
        SourcePolicy.check(source);
        offsets = new Utf8Offsets(source);
        if (!hash(source).equals(artifact.path("sourceHash").asText())) throw new IllegalArgumentException("source hash");
        String mode = artifact.path("mode").asText();
        if (!mode.equals("BLOCK_SUPPORTED") && !mode.equals("TEXT_ONLY")) throw new IllegalArgumentException("artifact mode");
        if (mode.equals("BLOCK_SUPPORTED")) indexModule();
        else if (!artifact.path("module").isNull() || !artifact.path("occurrences").isEmpty()) {
            throw new IllegalArgumentException("text-only graph");
        }
        checkOccurrences();
        checkTrivia();
    }

    /** Indexes identities from a previously checked historical module. */
    private void indexModule() {
        JsonNode module = artifact.path("module");
        new ModuleChecker(module).check();
        for (String key : new String[]{"signatures", "fields", "predicates", "facts", "assertions", "commands"}) {
            for (JsonNode declaration : module.path(key)) {
                declarations.add(declaration.path("id").asText());
                if (declaration.has("name")) names.put(declaration.path("id").asText(), declaration.path("name").asText());
            }
        }
        for (JsonNode pred : module.path("predicates")) {
            for (JsonNode parameter : pred.path("parameters")) {
                binders.add(parameter.path("id").asText());
                names.put(parameter.path("id").asText(), parameter.path("name").asText());
            }
        }
        for (JsonNode node : module.path("nodes")) {
            nodes.put(node.path("id").asText(), node);
            if (node.has("binder")) {
                JsonNode binder = node.path("binder");
                binders.add(binder.path("id").asText());
                names.put(binder.path("id").asText(), binder.path("name").asText());
            }
        }
    }

    /**
     * Checks each stored occurrence's identity, role and Unicode boundaries.
     * @throws IllegalArgumentException if any occurrence is malformed
     */
    private void checkOccurrences() {
        JsonNode spans = artifact.path("occurrences");
        if (!spans.isArray() || spans.size() > 2048) throw new IllegalArgumentException("occurrence array");
        Set<String> seen = new HashSet<>();
        for (JsonNode span : spans) {
            if (!span.isObject() || span.size() != 5 || !integer(span.path("startUtf16"))
                    || !integer(span.path("endUtf16"))) throw new IllegalArgumentException("occurrence shape");
            String id = span.path("nodeId").asText();
            String role = span.path("role").asText();
            String occurrenceId = span.path("occurrenceId").asText();
            int start = span.path("startUtf16").asInt(-1);
            int end = span.path("endUtf16").asInt(-1);
            if (!nodes.containsKey(id) || !Set.of("expression", "operator", "reference", "binder").contains(role)
                    || !occurrenceId.equals(id + ":" + role) || !seen.add(occurrenceId)
                    || start < 0 || end <= start || end > source.length() || !boundary(start) || !boundary(end)) {
                throw new IllegalArgumentException("occurrence bounds or identity");
            }
            checkOccurrenceText(nodes.get(id), role, start, end);
        }
    }

    /**
     * Checks identifiable token roles against exact source bytes.
     * @param node checked expression node
     * @param role stored occurrence role
     * @param start inclusive UTF-16 start
     * @param end exclusive UTF-16 end
     * @throws IllegalArgumentException if a token role is inconsistent
     */
    private void checkOccurrenceText(JsonNode node, String role, int start, int end) {
        String tag = node.path("tag").asText();
        String actual = source.substring(start, end);
        if (role.equals("reference")) {
            String key = tag.equals("predicate_call") ? "predicateId" : "targetId";
            if ((!tag.endsWith("_ref") && !tag.equals("predicate_call")) || !actual.equals(names.get(node.path(key).asText()))) {
                throw new IllegalArgumentException("reference occurrence");
            }
        }
        if (role.equals("binder") && (!node.has("binder") || !actual.equals(node.path("binder").path("name").asText()))) {
            throw new IllegalArgumentException("binder occurrence");
        }
        if (role.equals("operator") && !actual.equals(operator(tag))) throw new IllegalArgumentException("operator occurrence");
    }

    /**
     * Returns canonical syntax for an operator token.
     * @param tag expression tag
     * @return canonical token, or empty string for non-operators
     */
    private String operator(String tag) {
        return switch (tag) {
            case "and", "or", "not", "implies", "iff" -> tag;
            case "some_test", "some_quant" -> "some";
            case "no_test" -> "no";
            case "one_test" -> "one";
            case "lone_test" -> "lone";
            case "all_quant" -> "all";
            case "equal" -> "=";
            case "subset" -> "in";
            case "union" -> "+";
            case "intersection" -> "&";
            case "difference" -> "-";
            case "join" -> ".";
            case "product" -> "->";
            case "transpose" -> "~";
            default -> "";
        };
    }

    /**
     * Checks an integer fits the bounded source representation.
     * @param value JSON number
     * @return whether it is a representable integer
     */
    private boolean integer(JsonNode value) {
        return value.isIntegralNumber() && value.canConvertToInt();
    }

    /**
     * Checks a UTF-16 position does not split a surrogate pair.
     * @param position source boundary
     * @return whether the boundary is valid
     */
    private boolean boundary(int position) {
        return position == 0 || position == source.length()
            || !(Character.isHighSurrogate(source.charAt(position - 1)) && Character.isLowSurrogate(source.charAt(position)));
    }

    /**
     * Checks that stored comments exactly cover the actual lexical comments in order.
     * @throws IllegalArgumentException when comments, byte intervals or anchors differ
     */
    private void checkTrivia() {
        JsonNode trivia = artifact.path("trivia");
        if (!trivia.isArray()) throw new IllegalArgumentException("trivia array");
        int index = 0;
        Set<String> ids = new HashSet<>();
        for (SourceLexer.Token token : new SourceLexer(source).read()) {
            if (!token.comment()) continue;
            if (index >= trivia.size()) throw new IllegalArgumentException("missing comment");
            JsonNode item = trivia.get(index);
            if (!item.isObject() || item.size() != 5 || !integer(item.path("order"))
                    || !integer(item.path("startByte")) || !integer(item.path("endByte"))
                    || !item.path("commentId").isTextual() || item.path("commentId").asText().isEmpty()
                    || item.path("order").asInt(-1) != index || item.path("startByte").asInt(-1) != byteOffset(token.start())
                    || item.path("endByte").asInt(-1) != byteOffset(token.end())
                    || !ids.add(item.path("commentId").asText())) throw new IllegalArgumentException("comment token");
            checkAnchor(item.path("anchor"));
            index++;
        }
        if (index != trivia.size()) throw new IllegalArgumentException("extra comment");
    }

    /**
     * Checks a closed trivia anchor against artifact identities.
     * @param anchor stored anchor
     * @throws IllegalArgumentException when malformed or dangling
     */
    private void checkAnchor(JsonNode anchor) {
        if (!anchor.isObject()) throw new IllegalArgumentException("anchor shape");
        String kind = anchor.path("kind").asText();
        if (artifact.path("mode").asText().equals("TEXT_ONLY") && !Set.of("module-leading", "module-trailing").contains(kind)) {
            throw new IllegalArgumentException("text-only anchor");
        }
        if (Set.of("module-leading", "module-trailing", "orphan").contains(kind)) {
            if (anchor.size() != 1) throw new IllegalArgumentException("module anchor");
            return;
        }
        if (!anchor.path("side").asText().matches("leading|trailing")) throw new IllegalArgumentException("anchor side");
        boolean valid = switch (kind) {
            case "declaration" -> anchor.size() == 3 && declarations.contains(anchor.path("declarationId").asText());
            case "binder" -> anchor.size() == 3 && binders.contains(anchor.path("binderId").asText());
            case "expression" -> expressionAnchor(anchor);
            default -> false;
        };
        if (!valid) throw new IllegalArgumentException("anchor identity");
    }

    /**
     * Checks expression anchor fields and identity.
     * @param anchor expression anchor
     * @return whether the anchor has a supported role and valid node
     */
    private boolean expressionAnchor(JsonNode anchor) {
        JsonNode node = nodes.get(anchor.path("nodeId").asText());
        if (anchor.size() != 4 || node == null) return false;
        String role = anchor.path("role").asText();
        String tag = node.path("tag").asText();
        if (role.equals("expression")) return true;
        if (role.equals("reference")) return tag.endsWith("_ref") || tag.equals("predicate_call");
        if (role.equals("binder")) return node.has("binder");
        return role.equals("operator") && !tag.endsWith("_ref") && !tag.equals("predicate_call");
    }

    /**
     * Computes the exact UTF-8 offset of a source boundary.
     * @param index UTF-16 source offset
     * @return byte offset
     */
    private int byteOffset(int index) {
        return offsets.at(index);
    }

    /**
     * Computes lowercase SHA-256 of exact UTF-8 bytes.
     * @param text source text
     * @return digest
     * @throws IllegalStateException if the required digest provider is missing
     */
    static String hash(String text) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 unavailable", error);
        }
    }
}
