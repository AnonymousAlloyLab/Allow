package dev.allow.backend;

import dev.allow.dto.JobView;
import dev.allow.dto.WorkerRequest;

/** Package-private injection seam for supervisor tests, never selected by client input. */
interface JobRunner {
    /**
     * Identifies worker implementation/options for analysis provenance.
     * @return trusted implementation identity
     */
    default String identity() {
        return getClass().getName();
    }

    /**
     * Runs and reaps one isolated worker.
     * @param request exact input
     * @param control cancellation owner
     * @return terminal result
     * @throws Exception launch/protocol failure
     */
    JobView execute(WorkerRequest request, JobControl control) throws Exception;
}
