package dev.allow.canonical;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Local allow-slot-feature-v1 baseline; it accepts no source or presentation object. */
public final class EmbeddingEncoder {
    private static final int DIMENSIONS = 128;

    /** Creates a stateless local feature encoder with no network dependencies. */
    public EmbeddingEncoder() { }

    /** Encodes anonymous structural bytes as normalized fixed-size chunk counts.
     * @param artifact canonical mapper output, excluding all name maps
     * @return immutable 128-dimensional deterministic retrieval baseline
     */
    public List<Double> encode(AnonymizedArtifact artifact) {
        byte[] bytes = artifact.bytes();
        double[] counts = new double[DIMENSIONS];
        for (int offset = 0; offset < bytes.length; offset += 4) {
            byte[] chunk = Arrays.copyOfRange(bytes, offset, Math.min(offset + 4, bytes.length));
            byte[] hash = CanonicalDigest.digest(chunk);
            int value = Byte.toUnsignedInt(hash[0]) * 256 + Byte.toUnsignedInt(hash[1]);
            counts[value % DIMENSIONS] += 1;
        }
        return normalized(counts);
    }

    /** Normalizes counts without changing ordering or exposing a mutable array.
     * @param counts nonnegative per-dimension chunk counts
     * @return immutable L2-normalized vector
     */
    private List<Double> normalized(double[] counts) {
        double squared = 0;
        for (double value : counts) {
            squared += value * value;
        }
        double norm = Math.sqrt(squared);
        List<Double> vector = new ArrayList<>(DIMENSIONS);
        for (double value : counts) {
            vector.add(norm == 0 ? 0.0 : value / norm);
        }
        return List.copyOf(vector);
    }
}
