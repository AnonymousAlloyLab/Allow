package dev.allow.egraph;
import java.util.List;
/** Exact anonymous relational schema or Boolean sort.
     */
public record Sort(String kind, List<List<String>> schema) {
    /** Copies nested alternatives.
     * @param kind closed sort kind
     * @param schema ordered nominal alternatives
     */
    public Sort {
        schema = schema.stream().map(List::copyOf).toList();
        if (!(kind.equals("BOOL") && schema.isEmpty()) && !(kind.equals("REL") && !schema.isEmpty())) {
            throw new IllegalArgumentException("Invalid sort");
        }
        if (kind.equals("REL")) {
            int arity = schema.get(0).size();
            if (arity < 1) throw new IllegalArgumentException("Empty schema");
            String previous = "";
            for (List<String> alternative : schema) {
                if (alternative.size() != arity) throw new IllegalArgumentException("Mixed arity");
                String key = String.join("\u0000", alternative);
                if (key.compareTo(previous) <= 0) throw new IllegalArgumentException("Schema order");
                previous = key;
                for (String column : alternative) {
                    if (!column.matches("sig:(0|[1-9][0-9]*)|UNIV|INT|SEQIDX")) throw new IllegalArgumentException("Schema token");
                }
            }
        }
    }
    /** Creates the Boolean sort.
     * @return Boolean sort
     */
    public static Sort bool() { return new Sort("BOOL", List.of()); }
    /** Creates an exact relation sort.
     * @param schema anonymous alternatives
     * @return relation sort
     */
    public static Sort relation(List<List<String>> schema) { return new Sort("REL", schema); }
}
