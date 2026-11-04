package dev.allow.backend;

import dev.allow.dto.JobView;
import dev.allow.dto.WorkerRequest;

/** Synchronized absorbing terminal state; subprocess lifecycle remains owned by the runner. */
final class JobRecord {
    private final WorkerRequest request;
    private final JobControl control = new JobControl();
    private JobView view;

    /**
     * Starts one queued job.
     * @param request exact input
     */
    JobRecord(WorkerRequest request) {
        this.request = request;
        view = ProcessRunner.outcome(request, "QUEUED", "Waiting for isolated worker.");
    }

    /**
     * Returns immutable state.
     * @return public snapshot
     */
    synchronized JobView view() {
        return view;
    }

    /**
     * Marks a queued job running unless cancellation already won.
     * @return whether to spawn
     */
    synchronized boolean start() {
        if (!view.status().equals("QUEUED")) return false;
        view = ProcessRunner.outcome(request, "RUNNING", "Analyzing in isolated worker.");
        return true;
    }

    /**
     * Accepts only the first terminal completion.
     * @param result validated terminal view
     */
    synchronized void finish(JobView result) {
        if (!terminal()) view = result;
    }

    /**
     * Cancels once without releasing a live worker permit.
     * @return resulting snapshot
     */
    synchronized JobView cancel() {
        if (!terminal()) {
            view = ProcessRunner.outcome(request, "CANCELLED", "Cancelled.");
            control.cancel();
        }
        return view;
    }

    /**
     * Reports absorbing state.
     * @return terminal state flag
     */
    synchronized boolean terminal() {
        return !view.status().equals("QUEUED") && !view.status().equals("RUNNING");
    }

    /**
     * Returns private supervisor request.
     * @return immutable input
     */
    WorkerRequest request() {
        return request;
    }

    /**
     * Returns the supervisor cancellation owner.
     * @return private control object
     */
    JobControl control() {
        return control;
    }
}
