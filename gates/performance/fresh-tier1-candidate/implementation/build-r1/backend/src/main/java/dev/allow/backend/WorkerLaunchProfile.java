package dev.allow.backend;

/** Fixed trusted launch choices; no request or environment can supply JVM options. */
enum WorkerLaunchProfile {
    DEFAULT,
    DOCUMENT_ADVISORY_TIER1
}
