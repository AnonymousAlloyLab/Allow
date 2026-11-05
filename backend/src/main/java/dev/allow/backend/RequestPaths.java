package dev.allow.backend;

/** Rejects routing aliases and keeps public access confined to flat static assets. */
final class RequestPaths {
    private static final String DOCUMENT_SEGMENT = "^(/api/v1/documents/)server(?::|%3A)"
            + "([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?=/|$)";
    /** Prevents construction of the closed request-path policy. */
    private RequestPaths() { }

    /** Checks literal path syntax before container/controller routing can grant access.
     * @param path original request URI without query
     * @return true only for canonical literal path segments
     */
    static boolean canonical(String path) {
        if (path == null) return false;
        String checked = path.replaceFirst(DOCUMENT_SEGMENT, "$1server-$2");
        if (!checked.matches("/[A-Za-z0-9_./-]*") || checked.contains("//")) return false;
        for (String segment : path.split("/", -1)) {
            if (segment.equals(".") || segment.equals("..")) return false;
        }
        return true;
    }

    /** Grants anonymous read access only to canonical application entry and flat assets.
     * @param method exact HTTP method
     * @param path original request URI
     * @return whether this static request is exempt from bearer verification
     */
    static boolean publicRead(String method, String path) {
        if (!canonical(path) || !("GET".equals(method) || "HEAD".equals(method))) return false;
        return path.equals("/") || path.equals("/index.html")
                || path.matches("/assets/[A-Za-z0-9_-]+\\.(js|css|svg|png|ico|woff|woff2)");
    }
}
