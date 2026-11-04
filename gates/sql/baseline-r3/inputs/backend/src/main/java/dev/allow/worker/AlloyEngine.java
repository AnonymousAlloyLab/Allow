package dev.allow.worker;

import dev.allow.canonical.CanonicalView;
import dev.allow.canonical.Canonicalizer;
import dev.allow.dto.*;
import edu.mit.csail.sdg.alloy4.A4Reporter;
import edu.mit.csail.sdg.alloy4.Err;
import edu.mit.csail.sdg.ast.Command;
import edu.mit.csail.sdg.parser.CompModule;
import edu.mit.csail.sdg.parser.CompUtil;
import edu.mit.csail.sdg.translator.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import kodkod.engine.satlab.SATFactory;

/** Child-only Alloy API adapter; supervisor enforces its external wall deadline. */
final class AlloyEngine {
    /**
     * Executes one validated request; failures never become UNSAT.
     * @param request immutable input
     * @return identity-bound result
     */
    JobView execute(WorkerRequest request) {
        try {
            validate(request);
            Path file = Path.of("/tmp/model.als");
            Files.writeString(file, request.source(), StandardCharsets.UTF_8);
            CompModule world = CompUtil.parseEverything_fromFile(A4Reporter.NOP, null, file.toString());
            List<CommandView> commands = commands(world);
            if (request.commandIndex() < 0 || request.commandIndex() >= commands.size()) {
                return result(request, "INVALID", null, "Select a valid command.", commands, null, null);
            }
            Command command = world.getAllCommands().get(request.commandIndex());
            AstPolicy.check(world, command);
            CanonicalView canonical = new Canonicalizer().analyze(world, command);
            String kind = command.check ? "check" : "run";
            if (request.operation().equals("VALIDATE")) {
                return result(request, "VALIDATED", kind, "Parsed and type-checked.", commands, canonical, null);
            }
            return solve(request, world, command, commands, canonical);
        } catch (Err error) {
            return result(request, "INVALID", null, safe(error.getMessage()), List.of(), null, null);
        } catch (IllegalArgumentException error) {
            return result(request, "UNSUPPORTED", null, safe(error.getMessage()), List.of(), null, null);
        } catch (Exception | StackOverflowError error) {
            return result(request, "ERROR", null, "Worker could not complete this analysis.", List.of(), null, null);
        }
    }

    /**
     * Validates supervisor identity before parser use.
     * @param request wire input
     * @throws IllegalArgumentException invalid identity or operation
     */
    private void validate(WorkerRequest request) {
        SourcePolicy.check(request.source());
        if (request.protocol() != 1 || !Hashes.text(request.source()).equals(request.sourceHash())
                || !("VALIDATE".equals(request.operation()) || "ANALYZE".equals(request.operation()))) {
            throw new IllegalArgumentException("Invalid request identity or operation.");
        }
    }

    /**
     * Returns readable commands from the exact parsed module.
     * @param world parsed source
     * @return choices
     */
    private List<CommandView> commands(CompModule world) {
        List<CommandView> choices = new ArrayList<>();
        int index = 0;
        for (Command command : world.getAllCommands()) {
            choices.add(new CommandView(index++, command.label, command.check ? "check" : "run"));
        }
        return List.copyOf(choices);
    }

    /**
     * Solves using explicitly selected pure Java SAT4J.
     * @param request identity
     * @param world module
     * @param command selected bounds
     * @param choices commands
     * @param canonical optional structure
     * @return bounded evidence
     * @throws Err solver failure
     * @throws IllegalStateException solver returned no outcome
     */
    private JobView solve(WorkerRequest request, CompModule world, Command command,
                          List<CommandView> choices, CanonicalView canonical) throws Err {
        A4Options options = new A4Options();
        options.solver = SATFactory.get("sat4j");
        options.noOverflow = true;
        options.decompose_mode = 0;
        options.tempDirectory = "/tmp";
        A4Solution solution = TranslateAlloyToKodkod.execute_command(
                A4Reporter.NOP, world.getAllReachableSigs(), command, options);
        if (solution == null) throw new IllegalStateException("No solver outcome");
        boolean sat = solution.satisfiable();
        WitnessView witness = sat ? new WitnessProjector().project(solution) : null;
        return result(request, sat ? "SAT" : "UNSAT", command.check ? "check" : "run",
                sat ? "Witness found within declared bounds." : "No witness within declared bounds.",
                choices, canonical, witness);
    }

    /**
     * Creates an immutable response.
     * @param request identity
     * @param status state
     * @param kind command kind
     * @param message diagnostic
     * @param commands choices
     * @param canonical structure
     * @param witness instance
     * @return response
     */
    private JobView result(WorkerRequest request, String status, String kind, String message,
                           List<CommandView> commands, CanonicalView canonical, WitnessView witness) {
        return new JobView(request.jobId(), status, request.sourceHash(), request.revision(), request.epoch(),
                request.analysisKey(), kind, message, commands, canonical, witness);
    }

    /**
     * Bounds parser diagnostics without printing them to logs.
     * @param message parser text
     * @return safe length
     */
    private String safe(String message) {
        if (message == null) return "Invalid source.";
        return message.substring(0, Math.min(message.length(), 2000));
    }
}
