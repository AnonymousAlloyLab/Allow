package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import edu.mit.csail.sdg.ast.Command;
import edu.mit.csail.sdg.ast.CommandScope;
import edu.mit.csail.sdg.ast.Sig;
import edu.mit.csail.sdg.parser.CompModule;
import java.nio.charset.StandardCharsets;

/** Produces internal command descriptors before artifact-bound key allocation. */
final class CommandDescriptors {
    private final CompModule parsed;
    private final JsonNode commands;

    /**
     * Creates a descriptor reader for an exact parsed source.
     * @param parsed Alloy module
     * @param commands checked IR commands or null for text-only source
     */
    CommandDescriptors(CompModule parsed, JsonNode commands) {
        this.parsed = parsed;
        this.commands = commands;
    }

    /**
     * Describes all authored commands in parser order.
     * @param authored number of lexically verified authored commands
     * @return bounded internal descriptors with no artifact authority
     * @throws IllegalArgumentException if count, policy or labels are invalid
     */
    ArrayNode read(int authored) {
        if (authored < 0 || authored > 32 || (authored > 0 && parsed.getAllCommands().size() != authored)) {
            throw new IllegalArgumentException("invalid command count");
        }
        if (commands != null && (!commands.isArray() || commands.size() != authored)) {
            throw new IllegalArgumentException("command correspondence");
        }
        ArrayNode result = JsonNodeFactory.instance.arrayNode();
        for (int index = 0; index < authored; index++) add(result, index, parsed.getAllCommands().get(index));
        return result;
    }

    /**
     * Adds one closed internal descriptor.
     * @param result destination array
     * @param index parser-order index
     * @param command parsed command
     */
    private void add(ArrayNode result, int index, Command command) {
        check(command);
        ObjectNode item = result.addObject();
        item.put("index", index);
        item.put("kind", command.check ? "check" : "run");
        item.put("label", command.label);
        item.set("options", options(command));
        if (commands != null) item.put("irCommandId", commands.get(index).path("id").textValue());
    }

    /**
     * Checks the currently inherited selected-command policy bounds.
     * @param command resolved command
     * @throws IllegalArgumentException when bounds exceed local policy
     */
    private void check(Command command) {
        if (command.label == null || command.label.getBytes(StandardCharsets.UTF_8).length > 256
                || command.overall > 8 || command.bitwidth > 8 || command.maxseq > 8
                || command.minprefix > 10 || command.maxprefix > 10) {
            throw new IllegalArgumentException("unsupported command policy");
        }
        for (CommandScope scope : command.scope) {
            if (scope.endingScope > 8) throw new IllegalArgumentException("unsupported signature scope");
        }
    }

    /**
     * Captures parser options without replacing sentinel values.
     * @param command parsed command
     * @return complete internal option object
     */
    private ObjectNode options(Command command) {
        ObjectNode value = JsonNodeFactory.instance.objectNode();
        value.put("overall", command.overall);
        value.put("bitwidth", command.bitwidth);
        value.put("maxseq", command.maxseq);
        value.put("minprefix", command.minprefix);
        value.put("maxprefix", command.maxprefix);
        value.put("maxstring", command.maxstring);
        value.put("expects", command.expects);
        ArrayNode scopes = value.putArray("scopes");
        for (CommandScope scope : command.scope) scope(scopes, scope);
        ArrayNode exact = value.putArray("additionalExactScopes");
        for (Sig signature : command.additionalExactScopes) exact.add(signature.label);
        return value;
    }

    /**
     * Captures an exact per-signature scope.
     * @param scopes destination array
     * @param scope resolved scope
     */
    private void scope(ArrayNode scopes, CommandScope scope) {
        ObjectNode value = scopes.addObject();
        value.put("signatureLabel", scope.sig.label);
        value.put("isExact", scope.isExact);
        value.put("startingScope", scope.startingScope);
        value.put("endingScope", scope.endingScope);
        value.put("increment", scope.increment);
    }
}
