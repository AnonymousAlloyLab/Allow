package dev.allow.backend;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.http.HttpResponse;
import java.nio.ByteBuffer;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.Flow;

/** Cancelling HTTP body subscriber with a strict allocation ceiling. */
final class AiAccessBody implements HttpResponse.BodySubscriber<byte[]> {
    private final ByteArrayOutputStream bytes = new ByteArrayOutputStream();
    private final CompletableFuture<byte[]> result = new CompletableFuture<>();
    private Flow.Subscription subscription;
    /** Supplies the bounded body handler.
     * @param info response headers
     * @return new bounded subscriber
     */
    static HttpResponse.BodySubscriber<byte[]> handler(HttpResponse.ResponseInfo info) { return new AiAccessBody(); }
    /** Returns completion of the entire response body.
     * @return bounded body future
     */
    @Override
    public CompletionStage<byte[]> getBody() { return result; }
    /** Requests one bounded flow batch.
     * @param value upstream subscription
     */
    @Override
    public void onSubscribe(Flow.Subscription value) { subscription = value; value.request(1); }
    /** Copies only bounded provider bytes, cancelling immediately on overflow.
     * @param buffers provider chunks
     */
    @Override
    public void onNext(List<ByteBuffer> buffers) {
        for (ByteBuffer buffer : buffers) {
            if (buffer.remaining() > 8192 - bytes.size()) {
                subscription.cancel(); result.completeExceptionally(new IOException("Provider response rejected")); return;
            }
            byte[] chunk = new byte[buffer.remaining()]; buffer.get(chunk); bytes.writeBytes(chunk);
        }
        subscription.request(1);
    }
    /** Completes failure without exposing provider text.
     * @param failure private transport failure
     */
    @Override
    public void onError(Throwable failure) { result.completeExceptionally(new IOException("Provider unavailable")); }
    /** Completes the fully bounded response.
     */
    @Override
    public void onComplete() { result.complete(bytes.toByteArray()); }
}
