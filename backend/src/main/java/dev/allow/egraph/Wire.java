package dev.allow.egraph;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.OutputStream;
import java.io.IOException;
import java.security.MessageDigest;
import java.util.HexFormat;
/** Deterministic internal serialization and catalog hashing.
     */
final class Wire {
    private static final ObjectMapper MAPPER = new ObjectMapper().enable(com.fasterxml.jackson.databind.SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS);
    /** Prevents utility construction.
     */
    private Wire() { }
    /** Encodes a closed value.
     * @param value immutable value
     * @return compact JSON
     * @throws IllegalArgumentException when validation or resource checks reject the operation
     */
    static String json(Object value) {
        try { return MAPPER.writeValueAsString(value); }
        catch (Exception error) { throw new IllegalArgumentException("Invalid artifact", error); }
    }
    /** Hashes exact bytes.
     * @param bytes input bytes
     * @return lowercase digest
     * @throws IllegalStateException when validation or resource checks reject the operation
     */
    static String digest(byte[] bytes) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
        catch (Exception error) { throw new IllegalStateException(error); }
    }
    /** Measures exact UTF-8 output.
     * @param value closed artifact
     * @return serialized byte count
     * @throws IllegalArgumentException when validation or resource checks reject the operation
     */
    static int size(Object value) {
        Counter counter = new Counter();
        try { MAPPER.writeValue(counter, value); return counter.count; }
        catch (Exception error) {
            if (counter.count > 262144) return 262145;
            throw new IllegalArgumentException("Invalid artifact", error);
        }
    }
    /** Allocation-free capped serialized-size sink.
     */
    private static final class Counter extends OutputStream {
        private int count;
        /** Counts one emitted byte.
     * @param value discarded byte
     * @throws IOException when cap is exceeded
     */
        @Override public void write(int value) throws IOException { charge(1); }
        /** Counts an emitted block.
     * @param bytes discarded bytes
     * @param offset block start
     * @param length block length
     * @throws IOException when cap is exceeded
     */
        @Override public void write(byte[] bytes, int offset, int length) throws IOException { charge(length); }
        /** Enforces the byte cap before further output.
     * @param length emitted length
     * @throws IOException when cap is exceeded
     */
        private void charge(int length) throws IOException {
            count += length; if (count > 262144) throw new IOException("Artifact limit");
        }
    }
}
