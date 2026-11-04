package dev.allow.dto;

/** Browser candidate; identity values are echoes rather than authorization. */
public record JobRequest(String source, int commandIndex, long revision, long epoch, String operation) {}
