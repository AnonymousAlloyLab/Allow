package dev.allow.canonical;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.util.List;

/** Capability value constructed only by this package's resolved-slot mapper. */
public final class AnonymizedArtifact {
    private final String payload;

    /** Stores immutable canonical JSON without accepting presentation metadata.
     * @param payload internal structural serialization
     */
    private AnonymizedArtifact(String payload) {
        this.payload = payload;
    }

    /** Serializes a validated mapper tree; arbitrary callers cannot construct this value.
     * @param structure validated anonymous module node
     * @return typed anonymous artifact
     * @throws IllegalStateException if the closed JSON tree cannot serialize
     */
    static AnonymizedArtifact fromStructure(List<Object> structure) {
        try {
            return new AnonymizedArtifact(new ObjectMapper().writeValueAsString(structure));
        } catch (JsonProcessingException error) {
            throw new IllegalStateException("Structural JSON serialization failed", error);
        }
    }

    /** Returns immutable JSON containing structural slots only.
     * @return compact canonical structural payload
     */
    public String payload() {
        return payload;
    }

    /** Returns a fresh UTF-8 byte array so callers cannot mutate stored state.
     * @return independent canonical bytes
     */
    public byte[] bytes() {
        return payload.getBytes(StandardCharsets.UTF_8);
    }
}
