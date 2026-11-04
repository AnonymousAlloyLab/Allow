package dev.allow.worker;

import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.StreamReadConstraints;
import com.fasterxml.jackson.core.StreamReadFeature;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.MapperFeature;
import java.io.IOException;

/** Strict JSON codec shared by HTTP and the one-shot subprocess wire. */
public final class JsonWire {
    private static final ObjectMapper MAPPER = create();

    /** Prevents construction of the stateless codec. */
    private JsonWire() {}

    /**
     * Creates a strict codec without exposing shared mutable state.
     * @return codec
     */
    private static ObjectMapper create() {
        JsonFactory factory = JsonFactory.builder()
                .enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION)
                .streamReadConstraints(StreamReadConstraints.builder()
                        .maxNestingDepth(140).maxStringLength(2097152).build()).build();
        return new ObjectMapper(factory)
                .disable(MapperFeature.ALLOW_COERCION_OF_SCALARS)
                .disable(DeserializationFeature.ACCEPT_FLOAT_AS_INT)
                .enable(DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES)
                .enable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
                .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS)
                .enable(DeserializationFeature.FAIL_ON_MISSING_CREATOR_PROPERTIES);
    }

    /**
     * Serializes one compact JSON value.
     * @param value data
     * @return UTF-8 bytes
     * @throws IOException encoding failure
     */
    public static byte[] encode(Object value) throws IOException {
        return MAPPER.writeValueAsBytes(value);
    }

    /**
     * Decodes strict complete JSON.
     * @param bytes input
     * @param type expected schema
     * @param <T> schema type
     * @return decoded value
     * @throws IOException malformed JSON
     */
    public static <T> T decode(byte[] bytes, Class<T> type) throws IOException {
        return MAPPER.readValue(bytes, type);
    }
}
