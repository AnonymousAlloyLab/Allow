package dev.allow.corpus;

import dev.allow.canonical.CorpusProjection;
import dev.allow.worker.SourcePolicy;
import edu.mit.csail.sdg.alloy4.A4Reporter;
import edu.mit.csail.sdg.ast.Command;
import edu.mit.csail.sdg.ast.Expr;
import edu.mit.csail.sdg.ast.Func;
import edu.mit.csail.sdg.parser.CompModule;
import edu.mit.csail.sdg.parser.CompUtil;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;

/** Isolated parse, proof and bounded witness-pool coordinator. */
final class CorpusEngine {
    /** Executes a request without leaking parser diagnostics.
     * @param request trusted supervisor envelope
     * @return bounded response
     */
    CorpusResponse execute(CorpusRequest request) {
        try { validate(request); }
        catch (IllegalArgumentException failure) { return rejected("SOURCE_OR_REQUEST_POLICY"); }
        catch (Exception failure) { return rejected("IDENTITY_ERROR"); }
        try {
            Path file = Files.createTempFile(Path.of("/tmp"), "corpus-", ".als");
            try { return parseAndProcess(request, file); }
            finally { Files.deleteIfExists(file); }
        } catch (Exception | StackOverflowError failure) { return rejected("WORKER_ERROR"); }
    }

    /** Parses the bounded source and maps parser failures to a closed reason.
     * @param request validated envelope
     * @param file private temporary file
     * @return discovery or pool outcome
     * @throws Exception local I/O failure
     */
    private CorpusResponse parseAndProcess(CorpusRequest request, Path file) throws Exception {
        Files.writeString(file, request.source(), StandardCharsets.UTF_8);
        CompModule world;
        try { world = CompUtil.parseEverything_fromFile(A4Reporter.NOP, null, file.toString()); }
        catch (edu.mit.csail.sdg.alloy4.Err failure) { return rejected("PARSE_OR_TYPE_ERROR"); }
        try { return process(request, world); }
        catch (CorpusProjection.Rejected failure) { return rejected(failure.reason()); }
        catch (IllegalArgumentException failure) { return rejected("TARGET_OR_PROJECTION_UNSUPPORTED"); }
        catch (RuntimeException failure) { return rejected("PROJECTION_ERROR"); }
    }

    /** Produces a fixed diagnostic without source-dependent content.
     * @param reason closed machine reason
     * @return rejected response
     */
    private CorpusResponse rejected(String reason) {
        return new CorpusResponse("REJECTED", List.of(), null, reason);
    }

    /** Validates source and provenance identity.
     * @param request input frame
     * @throws IllegalArgumentException invalid identity
     * @throws Exception invalid source or identity
     */
    private void validate(CorpusRequest request) throws Exception {
        SourcePolicy.check(request.source());
        String digest = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                .digest(request.source().getBytes(StandardCharsets.UTF_8)));
        if (request.protocol() != 1 || !digest.equals(request.sourceHash()) || request.targetSlot() < -1
                || request.N() < 3 || request.N() > 5 || request.requestId() == null
                || request.requestId().isBlank() || request.toolchain() == null || request.toolchain().isBlank()) {
            throw new IllegalArgumentException("identity");
        }
    }

    /** Discovers or executes a selected nullary target.
     * @param request input identity
     * @param world parsed source
     * @return response
     * @throws IllegalArgumentException invalid target
     * @throws Exception unsupported or execution failure
     */
    private CorpusResponse process(CorpusRequest request, CompModule world) throws Exception {
        var functions = CorpusProjection.sourceFunctions(world);
        if (request.targetSlot() == -1) {
            List<Integer> slots = new ArrayList<>();
            for (int i = 0; i < functions.size(); i++) {
                if (functions.get(i).isPred && functions.get(i).count() == 0 && functions.get(i).isPrivate == null) slots.add(i);
            }
            return new CorpusResponse("DISCOVERY", slots, null, "");
        }
        int slot = request.targetSlot();
        if (slot >= functions.size()) throw new IllegalArgumentException("target");
        Func target = functions.get(slot);
        if (!target.isPred || target.count() != 0 || target.isPrivate != null) throw new IllegalArgumentException("target");
        Expr facts = world.getAllReachableFacts();
        Expr body = target.getBody();
        Command positive = command(facts.and(target.call()));
        Command negative = command(facts.and(target.call().not()));
        CorpusProjection.Result projection = CorpusProjection.capture(world, positive, slot);
        PoolBuilder builder = new PoolBuilder();
        PoolBuilder.Pool pos = builder.build(world, positive, body, true, request.N());
        PoolBuilder.Pool neg = builder.build(world, negative, body, false, request.N());
        Map<String, Object> bounds = Map.of("overall", 3, "bitwidth", 4, "maxseq", 3, "noOverflow", true);
        Map<String, Object> provenance = Map.of("requestId", request.requestId(), "sourceHash", request.sourceHash(),
                "targetSlot", slot, "toolchain", request.toolchain(), "bounds", bounds);
        Map<String, Object> record = Map.of("context", projection.context(), "predicate", projection,
                "positive", pos, "negative", neg, "provenance", provenance,
                "trainingVariants", TrainingVariant.create(projection.island()));
        boolean full = pos.members().size() == request.N() && neg.members().size() == request.N();
        return new CorpusResponse(full ? "FULL" : "PARTIAL", List.of(), record, "");
    }

    /** Constructs fixed static bounds shared by both polarities.
     * @param expression complete facts and polarity formula
     * @return generated command
     * @throws Exception invalid generated formula
     */
    private Command command(Expr expression) throws Exception {
        return new Command(false, 3, 4, 3, null, expression);
    }
}
