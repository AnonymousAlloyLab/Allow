package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Attaches exact source comments only to independently located syntax tokens. */
final class SourceTriviaAttacher {
    private final String source;
    private final Utf8Offsets offsets;
    private final JsonNode module;
    private final JsonNode occurrences;
    private final List<SourceLexer.Token> tokens;
    private final List<SourceLexer.Token> code = new ArrayList<>();
    private final Map<Integer, ObjectNode> owners = new HashMap<>();
    private final Map<Integer, SourceLexer.Token> codeAt = new HashMap<>();
    private final Map<Integer, Integer> widths = new HashMap<>();
    private final Map<String, String> declarationIds = new HashMap<>();

    /**
     * Creates an attacher for checked syntax and verified occurrence intervals.
     * @param source exact authored source
     * @param module complete checked module
     * @param occurrences verified source maps
     */
    SourceTriviaAttacher(String source, JsonNode module, JsonNode occurrences) {
        this.source = source;
        this.offsets = new Utf8Offsets(source);
        this.module = module;
        this.occurrences = occurrences;
        this.tokens = new SourceLexer(source).read();
    }

    /**
     * Produces exact comment tokens with conservative ownership.
     * @return ordered trivia records
     */
    ArrayNode attach() {
        for (SourceLexer.Token token : tokens) {
            if (!token.comment()) { code.add(token); codeAt.put(token.start(), token); }
        }
        indexDeclarations();
        markDeclarationTokens();
        markBinders();
        markCommands();
        markExpressionTokens();
        ArrayNode result = JsonNodeFactory.instance.arrayNode();
        for (SourceLexer.Token token : tokens) if (token.comment()) add(result, token);
        return result;
    }

    /** Indexes globally unique declaration names and IDs. */
    private void indexDeclarations() {
        for (String kind : List.of("signatures", "predicates", "facts", "assertions")) {
            for (JsonNode item : module.path(kind)) declarationIds.put(item.path("name").textValue(), item.path("id").textValue());
        }
    }

    /** Marks only syntactically verified top-level declaration header and closing tokens. */
    private void markDeclarationTokens() {
        int depth = 0;
        for (int i = 0; i < code.size(); i++) {
            String value = code.get(i).text();
            if (depth == 0 && List.of("sig", "pred", "fact", "assert").contains(value)) markDeclaration(i);
            if (value.equals("{")) depth++;
            else if (value.equals("}")) depth--;
        }
    }

    /**
     * Marks a declaration keyword/name/header and matching closing brace.
     * @param start keyword token index
     */
    private void markDeclaration(int start) {
        if (start + 1 >= code.size()) return;
        String id = declarationIds.get(code.get(start + 1).text());
        if (id == null) return;
        int open = findOpen(start + 2);
        if (open < 0) return;
        int close = matchingClose(open);
        if (close < 0) return;
        ObjectNode anchor = JsonNodeFactory.instance.objectNode().put("kind", "declaration").put("declarationId", id);
        for (int i = start; i <= open; i++) owners.put(code.get(i).start(), anchor);
        if (code.get(start).text().equals("sig") && start > 0
                && List.of("one", "lone", "some").contains(code.get(start - 1).text())) {
            owners.put(code.get(start - 1).start(), anchor);
        }
        owners.put(code.get(close).start(), anchor);
        if (code.get(start).text().equals("sig")) markFields(id, open, close);
        if (code.get(start).text().equals("pred")) markParameters(id, start, open);
    }

    /**
     * Locates the first opening declaration brace.
     * @param start first token after declaration name
     * @return opening brace index or -1
     */
    private int findOpen(int start) {
        for (int i = start; i < code.size(); i++) if (code.get(i).text().equals("{")) return i;
        return -1;
    }

    /**
     * Matches a declaration's brace by depth.
     * @param open opening brace index
     * @return closing brace index or -1
     */
    private int matchingClose(int open) {
        int depth = 0;
        for (int i = open; i < code.size(); i++) {
            if (code.get(i).text().equals("{")) depth++;
            else if (code.get(i).text().equals("}") && --depth == 0) return i;
        }
        return -1;
    }

    /**
     * Marks field declaration tokens within their owning signature.
     * @param owner signature identity
     * @param open signature opening brace
     * @param close signature closing brace
     */
    private void markFields(String owner, int open, int close) {
        for (JsonNode field : module.path("fields")) {
            if (!field.path("ownerSignatureId").asText().equals(owner)) continue;
            markNamedRange(field.path("name").asText(), field.path("id").asText(), "declaration", open + 1, close);
        }
    }

    /**
     * Marks parameter declarations in a predicate header.
     * @param owner predicate identity
     * @param start predicate keyword index
     * @param open predicate opening brace
     */
    private void markParameters(String owner, int start, int open) {
        for (JsonNode predicate : module.path("predicates")) {
            if (!predicate.path("id").asText().equals(owner)) continue;
            for (JsonNode parameter : predicate.path("parameters")) {
                markNamedRange(parameter.path("name").asText(), parameter.path("id").asText(), "binder", start, open);
            }
        }
    }

    /**
     * Marks a uniquely named field or binder declaration up to its delimiter.
     * @param name unique declaration name
     * @param id declaration identity
     * @param kind declaration or binder
     * @param start inclusive token range
     * @param end exclusive token range
     */
    private void markNamedRange(String name, String id, String kind, int start, int end) {
        for (int i = start; i + 1 < end; i++) {
            if (!code.get(i).text().equals(name) || !code.get(i + 1).text().equals(":")) continue;
            ObjectNode anchor = kind(kind);
            anchor.put(kind.equals("binder") ? "binderId" : "declarationId", id);
            int depth = 0;
            for (int j = i; j < end; j++) {
                String value = code.get(j).text();
                if (depth == 0 && (value.equals(",") || value.equals("]") || value.equals("|") || value.equals("}"))) break;
                owners.put(code.get(j).start(), anchor);
                if (value.equals("(")) depth++;
                else if (value.equals(")")) depth--;
            }
            return;
        }
    }

    /** Marks quantifier binder token triples using their globally unique names. */
    private void markBinders() {
        for (JsonNode node : module.path("nodes")) {
            if (!node.has("binder")) continue;
            JsonNode binder = node.path("binder");
            markNamedRange(binder.path("name").asText(), binder.path("id").asText(), "binder", 0, code.size());
        }
    }

    /** Marks authored command tokens in parser order. */
    private void markCommands() {
        int depth = 0;
        int commandIndex = 0;
        for (int i = 0; i < code.size(); i++) {
            String text = code.get(i).text();
            if (depth == 0 && (text.equals("run") || text.equals("check"))) {
                if (commandIndex < module.path("commands").size()) markCommand(i, commandIndex++);
            }
            if (text.equals("{")) depth++;
            else if (text.equals("}")) depth--;
        }
    }

    /**
     * Marks a command up to the next top-level declaration or command.
     * @param start command keyword index
     * @param index command ordinal
     */
    private void markCommand(int start, int index) {
        String id = module.path("commands").get(index).path("id").asText();
        ObjectNode anchor = kind("declaration").put("declarationId", id);
        for (int i = start; i < code.size(); i++) {
            String token = code.get(i).text();
            if (i > start && List.of("sig", "pred", "fact", "assert", "run", "check").contains(token)) break;
            if (i > start && List.of("one", "lone", "some").contains(token) && i + 1 < code.size()
                    && code.get(i + 1).text().equals("sig")) break;
            owners.put(code.get(i).start(), anchor);
        }
    }

    /** Assigns verified reference/operator spans precedence over declaration ownership. */
    private void markExpressionTokens() {
        for (JsonNode occurrence : occurrences) if (occurrence.path("role").asText().equals("expression")) markEnclosing(occurrence);
        for (JsonNode occurrence : occurrences) {
            String role = occurrence.path("role").asText();
            if (!role.equals("reference") && !role.equals("operator") && !role.equals("binder")) continue;
            int start = occurrence.path("startUtf16").intValue();
            int end = occurrence.path("endUtf16").intValue();
            SourceLexer.Token token = codeAt.get(start);
            if (token == null || token.end() != end) continue;
            ObjectNode anchor = JsonNodeFactory.instance.objectNode();
            anchor.put("kind", "expression");
            anchor.put("nodeId", occurrence.path("nodeId").textValue());
            anchor.put("role", role);
            owners.put(start, anchor);
        }
    }

    /**
     * Associates tokens with their smallest verified enclosing expression span.
     * @param occurrence verified expression occurrence
     */
    private void markEnclosing(JsonNode occurrence) {
        int start = occurrence.path("startUtf16").intValue();
        int end = occurrence.path("endUtf16").intValue();
        int width = end - start;
        for (int index = firstAfter(start - 1); index < code.size(); index++) {
            SourceLexer.Token token = code.get(index);
            if (token.start() >= end) break;
            if (token.start() < start || token.end() > end || token.text().equals("{") || token.text().equals("}")) continue;
            ObjectNode current = owners.get(token.start());
            if (current != null && !current.path("kind").asText().equals("expression")) continue;
            int previous = widths.getOrDefault(token.start(), Integer.MAX_VALUE);
            if (width < previous) assignExpression(token, occurrence, width);
            else if (width == previous && current != null
                    && !current.path("nodeId").equals(occurrence.path("nodeId"))) owners.remove(token.start());
        }
    }

    /**
     * Assigns a token to a verified expression occurrence.
     * @param token code token
     * @param occurrence expression occurrence
     * @param width source interval length
     */
    private void assignExpression(SourceLexer.Token token, JsonNode occurrence, int width) {
        ObjectNode owner = JsonNodeFactory.instance.objectNode();
        owner.put("kind", "expression");
        owner.put("nodeId", occurrence.path("nodeId").textValue());
        owner.put("role", "expression");
        owners.put(token.start(), owner);
        widths.put(token.start(), width);
    }

    /**
     * Creates one immutable-source token and its deterministic anchor.
     * @param result destination array
     * @param comment exact lexical comment
     */
    private void add(ArrayNode result, SourceLexer.Token comment) {
        ObjectNode item = result.addObject();
        item.put("commentId", "server:" + UUID.randomUUID());
        item.put("startByte", bytes(comment.start()));
        item.put("endByte", bytes(comment.end()));
        item.put("order", result.size() - 1);
        item.set("anchor", anchor(comment));
    }

    /**
     * Finds adjacent code and selects leading/trailing or orphan attachment.
     * @param comment comment token
     * @return closed anchor object
     */
    private ObjectNode anchor(SourceLexer.Token comment) {
        int nextIndex = firstAfter(comment.start());
        SourceLexer.Token previous = nextIndex == 0 ? null : code.get(nextIndex - 1);
        SourceLexer.Token next = nextIndex == code.size() ? null : code.get(nextIndex);
        if (previous == null) return kind("module-leading");
        if (next == null) return kind("module-trailing");
        boolean trailing = sameLine(previous.end(), comment.start());
        SourceLexer.Token selected = trailing ? previous : next;
        ObjectNode owner = owners.get(selected.start());
        if (owner == null) return kind("orphan");
        ObjectNode result = owner.deepCopy();
        result.put("side", trailing ? "trailing" : "leading");
        return result;
    }

    /**
     * Finds the first code token after a disjoint comment interval.
     * @param position comment start
     * @return next code-token index
     */
    private int firstAfter(int position) {
        int low = 0;
        int high = code.size();
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (code.get(middle).end() <= position) low = middle + 1;
            else high = middle;
        }
        return low;
    }

    /**
     * Determines whether a range contains a logical line break.
     * @param start range start
     * @param end range end
     * @return true if both offsets share a line
     */
    private boolean sameLine(int start, int end) {
        for (int i = start; i < end; i++) if (source.charAt(i) == '\n' || source.charAt(i) == '\r') return false;
        return true;
    }

    /**
     * Constructs a module or orphan anchor.
     * @param name closed anchor kind
     * @return anchor
     */
    private ObjectNode kind(String name) {
        return JsonNodeFactory.instance.objectNode().put("kind", name);
    }

    /**
     * Converts a UTF-16 boundary into an exact UTF-8 byte offset.
     * @param index UTF-16 boundary
     * @return UTF-8 prefix length
     */
    private int bytes(int index) {
        return offsets.at(index);
    }
}
