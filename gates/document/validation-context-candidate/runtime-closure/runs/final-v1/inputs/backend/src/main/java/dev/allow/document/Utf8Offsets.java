package dev.allow.document;

/** Converts exact valid Unicode UTF-16 scalar boundaries to UTF-8 byte offsets. */
final class Utf8Offsets {
    private final int[] offsets;

    /**
     * Builds linear-time offsets for a source already validated for Unicode.
     * @param source exact Unicode source
     */
    Utf8Offsets(String source) {
        offsets = new int[source.length() + 1];
        int bytes = 0;
        for (int i = 0; i < source.length();) {
            offsets[i] = bytes;
            int scalar = source.codePointAt(i);
            int width = Character.charCount(scalar);
            if (width == 2) offsets[i + 1] = -1;
            bytes += scalar <= 0x7f ? 1 : scalar <= 0x7ff ? 2 : scalar <= 0xffff ? 3 : 4;
            i += width;
            offsets[i] = bytes;
        }
    }

    /**
     * Returns a UTF-8 offset for an exact scalar boundary.
     * @param position UTF-16 source index
     * @return zero-based byte offset
     * @throws IllegalArgumentException if the index is not a scalar boundary
     */
    int at(int position) {
        if (position < 0 || position >= offsets.length || offsets[position] < 0) {
            throw new IllegalArgumentException("invalid Unicode boundary");
        }
        return offsets[position];
    }
}
