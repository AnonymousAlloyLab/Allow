package dev.allow.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dev.allow.worker.JsonWire;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.Set;

/** Closed document envelopes and strict text boundaries independent of browser claims. */
final class DocumentJson {
    /** Prevents construction of the stateless boundary helpers. */
    private DocumentJson() {}

    /** Decodes public input while keeping malformed requests distinct from private bridge failures.
     * @param bytes bounded original HTTP body
     * @return strictly decoded request
     * @throws IllegalArgumentException malformed UTF-8 or JSON supplied by the client
     */
    static JsonNode request(byte[] bytes) {
        try { return decode(bytes); }
        catch (IOException failure) { throw new IllegalArgumentException("Invalid request encoding", failure); }
    }

    /** Decodes strict UTF-8 JSON and rejects BOMs, replacement decoding and invalid surrogates.
     * @param bytes bounded raw request
     * @return parsed immutable-by-convention snapshot
     * @throws IOException invalid encoding or JSON
     */
    static JsonNode decode(byte[] bytes) throws IOException {
        String text = StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
        if (text.startsWith("\ufeff")) throw new IOException("Byte-order mark is unsupported");
        JsonNode value = JsonWire.decode(bytes, JsonNode.class);
        unicode(value);
        return value;
    }

    /** Checks every decoded key and string, including escaped surrogate pairs.
     * @param value parsed bounded-depth JSON
     * @throws IOException unpaired surrogate
     */
    private static void unicode(JsonNode value) throws IOException {
        if (value.isTextual()) text(value.textValue());
        if (value.isObject()) {
            var names = value.fieldNames();
            while (names.hasNext()) text(names.next());
        }
        for (JsonNode child : value) unicode(child);
    }

    /** Checks Unicode scalar boundaries without replacing invalid input.
     * @param value decoded text
     * @throws IOException unpaired surrogate
     */
    private static void text(String value) throws IOException {
        for (int index = 0; index < value.length(); index++) {
            char unit = value.charAt(index);
            if (Character.isHighSurrogate(unit)) {
                if (++index >= value.length() || !Character.isLowSurrogate(value.charAt(index))) {
                    throw new IOException("Invalid Unicode");
                }
            } else if (Character.isLowSurrogate(unit)) throw new IOException("Invalid Unicode");
        }
    }

    /** Enforces exact required fields; optional variants use separate explicit calls.
     * @param value object to inspect
     * @param names complete required field set
     * @throws IllegalArgumentException unknown, absent or duplicate effective fields
     */
    static void fields(JsonNode value, String... names) {
        Set<String> actual = new HashSet<>();
        value.fieldNames().forEachRemaining(actual::add);
        if (!value.isObject() || !actual.equals(Set.of(names))) throw new IllegalArgumentException("Invalid fields");
    }

    /** Reads a safe nonnegative browser-compatible integer without coercion.
     * @param node input object
     * @param key required property
     * @return exact integer
     * @throws IllegalArgumentException invalid integer
     */
    static long revision(JsonNode node, String key) {
        JsonNode value = node.path(key);
        if (!value.isIntegralNumber() || !value.canConvertToLong()
                || value.longValue() < 0 || value.longValue() > 9007199254740991L) {
            throw new IllegalArgumentException("Invalid revision");
        }
        return value.longValue();
    }

    /** Creates an envelope whose request identity is fixed before persistence.
     * @param requestId original server response identity
     * @param status closed operation status
     * @param data response payload
     * @return complete response
     */
    static ObjectNode envelope(String requestId, String status, JsonNode data) {
        ObjectNode result = JsonNodeFactory.instance.objectNode();
        result.put("protocol", 1).put("requestId", requestId).put("status", status);
        result.set("data", data.deepCopy());
        return result;
    }
}
