package dev.allow.dto;

/** Single versioned sandbox request, created by the trusted supervisor. */
public record WorkerRequest(int protocol, String jobId, String source, String sourceHash,
                            String analysisKey, int commandIndex, long revision, long epoch,
                            String operation) {}
