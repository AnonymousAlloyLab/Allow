package dev.allow.dto;

/** Wire envelope; only protocol version one is accepted. */
public record WorkerResponse(int protocol, JobView result) {}
