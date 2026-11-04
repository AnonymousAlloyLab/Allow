package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import dev.allow.worker.JsonWire;
import edu.mit.csail.sdg.alloy4.Err;
import java.io.IOException;

/** Isolated-worker entry point for authoritative document validation. */
public final class DocumentEngine {
    /** Creates a stateless worker engine. */
    public DocumentEngine() {}

    /**
     * Validates a frozen candidate in an isolated worker.
     * @param candidate submitted complete candidate
     * @param baseArtifact authorized exact-base artifact
     * @param ownedIdInventory server-supplied identity-to-kind subset
     * @param policyVersion immutable policy identity
     * @return independent bounded checked result
     * @throws DocumentValidationException deterministic candidate denial
     * @throws IllegalStateException if worker infrastructure is unavailable
     */
    public JsonNode validate(JsonNode candidate, JsonNode baseArtifact, JsonNode ownedIdInventory,
            String policyVersion) throws DocumentValidationException {
        context(baseArtifact, ownedIdInventory, policyVersion);
        JsonNode frozen = candidate.deepCopy();
        try {
            JsonNode result = switch (frozen.path("mode").asText()) {
                case "BLOCK_SUPPORTED" -> new BlockValidation(frozen, baseArtifact.deepCopy(), ownedIdInventory.deepCopy()).validate();
                case "SOURCE" -> new SourceValidation(frozen).validate();
                default -> throw new IllegalArgumentException("unsupported candidate mode");
            };
            return bounded(result);
        } catch (Err rejected) {
            throw denial("INVALID_DRAFT", "Alloy rejected the candidate source.");
        } catch (IllegalArgumentException rejected) {
            throw denial(category(rejected.getMessage()), safe(rejected.getMessage()));
        } catch (IOException failure) {
            throw new IllegalStateException("Document validation infrastructure unavailable", failure);
        }
    }

    /**
     * Revalidates an authorized historical artifact without changing its content.
     * @param oldArtifact historical exact artifact content
     * @param ownedIdInventory server-supplied identity-to-kind subset
     * @param policyVersion immutable current policy identity
     * @return a fresh bounded checked result preserving historical content
     * @throws DocumentValidationException deterministic historical validation denial
     * @throws IllegalStateException if worker infrastructure is unavailable
     */
    public JsonNode revalidate(JsonNode oldArtifact, JsonNode ownedIdInventory, String policyVersion)
            throws DocumentValidationException {
        context(oldArtifact, ownedIdInventory, policyVersion);
        try {
            return bounded(new HistoryValidation(oldArtifact.deepCopy(), ownedIdInventory.deepCopy()).revalidate());
        } catch (Err | IllegalArgumentException rejected) {
            throw denial("INVALID_UNDO_TARGET", "Historical content is no longer valid under the current policy.");
        } catch (IOException failure) {
            throw new IllegalStateException("Historical validation infrastructure unavailable", failure);
        }
    }

    /**
     * Checks trusted worker context before candidate validation.
     * @param base authorized base artifact
     * @param inventory server-provided ID inventory
     * @param policy immutable policy identity
     * @throws IllegalStateException when internal context is absent
     */
    private void context(JsonNode base, JsonNode inventory, String policy) {
        if (base == null || !base.isObject() || inventory == null || !inventory.isObject() || policy == null || policy.isBlank()) {
            throw new IllegalStateException("Missing trusted document worker context");
        }
    }

    /**
     * Checks the complete provisional response size before it can be committed.
     * @param result independent worker result
     * @return defensive copy of bounded result
     * @throws IOException if JSON serialization fails or exceeds its bound
     */
    private JsonNode bounded(JsonNode result) throws IOException {
        if (JsonWire.encode(result).length > 1048576) throw new IOException("Document validation output limit");
        return result.deepCopy();
    }

    /**
     * Maps deterministic checker failures to closed public error categories.
     * @param message internal static diagnostic
     * @return closed error code
     */
    private String category(String message) {
        String text = message == null ? "" : message;
        if (text.contains("unbound") || text.contains("wrong-kind reference")) return "UNBOUND_SYMBOL";
        if (text.contains("schema") || text.contains("arity") || text.contains("endpoint")
                || text.contains("expected formula") || text.contains("expected relation") || text.contains("tuple multiplicity")) {
            return "TYPE_MISMATCH";
        }
        if (text.contains("Local policy") || text.contains("Imports are unsupported") || text.contains("AST node/depth")) {
            return "UNSUPPORTED_FRAGMENT";
        }
        return "INVALID_DRAFT";
    }

    /**
     * Bounds an internal static diagnostic before returning it to the caller.
     * @param message internal diagnostic
     * @return safe concise text
     */
    private String safe(String message) {
        if (message == null || message.isBlank()) return "The document candidate is invalid.";
        String value = message.replace('\n', ' ').replace('\r', ' ');
        return value.length() <= 160 ? value : value.substring(0, 160);
    }

    /**
     * Constructs a bounded deterministic denial.
     * @param code closed error category
     * @param message safe diagnostic text
     * @return typed denial
     */
    private DocumentValidationException denial(String code, String message) {
        ArrayNode diagnostics = JsonNodeFactory.instance.arrayNode();
        diagnostics.addObject().put("code", code).put("message", message);
        return new DocumentValidationException(code, diagnostics);
    }
}
