package dev.allow.canonical;

import java.util.List;

/** Public, immutable anonymous structural result; it contains no source-name map.
 * @param status AVAILABLE or UNSUPPORTED_CANONICAL
 * @param payload compact anonymous structural JSON, empty when unsupported
 * @param sha256 integrity digest, never an equivalence certificate
 * @param features immutable local retrieval baseline, empty when unsupported
 */
public record CanonicalView(String status, String payload, String sha256, List<Double> features, EgraphView egraph) {
    /** Keeps the existing four-field construction API.
     * @param status availability @param payload anonymous structure @param sha256 integrity digest
     * @param features local retrieval vector
     */
    public CanonicalView(String status, String payload, String sha256, List<Double> features) {
        this(status, payload, sha256, features, null);
    }

    /** Copies the feature collection to prevent mutable state escaping.
     * @param status profile availability
     * @param payload anonymous JSON
     * @param sha256 content integrity digest
     * @param features local feature values
     * @param egraph optional anonymous optimization results
     */
    public CanonicalView {
        features = List.copyOf(features);
    }
}
