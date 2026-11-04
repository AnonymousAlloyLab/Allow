package dev.allow.document;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import edu.mit.csail.sdg.alloy4.A4Reporter;
import edu.mit.csail.sdg.parser.CompUtil;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertFalse;

/** Checks finite examples of independent nominal and forest validation. */
class ModuleCheckerTest {
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final String A = "draft:00000000-0000-4000-8000-000000000001";
    private static final String B = "draft:00000000-0000-4000-8000-000000000002";
    private static final String F = "draft:00000000-0000-4000-8000-000000000003";
    private static final String N = "draft:00000000-0000-4000-8000-000000000004";
    private static final String T = "draft:00000000-0000-4000-8000-000000000005";

    /**
     * Parses a complete small fixture.
     * @param fields field declarations
     * @param nodes expressions
     * @return candidate module
     * @throws Exception on invalid fixture
     */
    private JsonNode module(String fields, String nodes) throws Exception {
        String source = "{\"version\":1,\"signatures\":[{\"tag\":\"signature\",\"id\":\"" + A
            + "\",\"name\":\"A\",\"multiplicity\":\"set\"},{\"tag\":\"signature\",\"id\":\"" + B
            + "\",\"name\":\"B\",\"multiplicity\":\"set\"}],\"fields\":[" + fields
            + "],\"predicates\":[],\"facts\":[{\"tag\":\"fact\",\"id\":\"" + F
            + "\",\"name\":\"f\",\"bodyId\":\"" + T + "\"}],\"assertions\":[],\"commands\":[],\"nodes\":["
            + nodes + "]}";
        return MAPPER.readTree(source);
    }

    /**
     * Makes a multiplicity test and its reference.
     * @param ref referenced declaration
     * @return expression JSON array content
     */
    private String testNodes(String ref) {
        return "{\"tag\":\"signature_ref\",\"id\":\"" + N + "\",\"targetId\":\"" + ref
            + "\"},{\"tag\":\"some_test\",\"id\":\"" + T + "\",\"operandId\":\"" + N + "\"}";
    }

    /**
     * Accepts a well-scoped nominal relation test.
     * @throws Exception if fixture cannot be decoded
     */
    @Test
    void acceptsValidFormula() throws Exception {
        JsonNode value = module("", testNodes(A));
        assertDoesNotThrow(new ModuleChecker(value)::check);
    }

    /**
     * Rejects an unresolved reference.
     * @throws Exception if fixture cannot be decoded
     */
    @Test
    void rejectsUnknownSignature() throws Exception {
        JsonNode value = module("", testNodes(N));
        assertThrows(IllegalArgumentException.class, new ModuleChecker(value)::check);
    }

    /**
     * Rejects tuple field multiplicity outside the frozen fragment.
     * @throws Exception if fixture cannot be decoded
     */
    @Test
    void rejectsTupleOne() throws Exception {
        String field = "{\"tag\":\"field\",\"id\":\"draft:00000000-0000-4000-8000-000000000006\","
            + "\"name\":\"r\",\"ownerSignatureId\":\"" + A + "\",\"rangeColumns\":[\"" + A
            + "\",\"" + B + "\"],\"multiplicity\":\"one\"}";
        JsonNode value = module(field, testNodes(A));
        assertThrows(IllegalArgumentException.class, new ModuleChecker(value)::check);
    }

    /**
     * Rejects an unreachable expression node.
     * @throws Exception if fixture cannot be decoded
     */
    @Test
    void rejectsUnreachable() throws Exception {
        String extra = ",{\"tag\":\"signature_ref\",\"id\":\"draft:00000000-0000-4000-8000-000000000006\","
            + "\"targetId\":\"" + A + "\"}";
        JsonNode value = module("", testNodes(A) + extra);
        assertThrows(IllegalArgumentException.class, new ModuleChecker(value)::check);
    }
    /**
     * Ensures generated basic source is accepted by the pinned Alloy parser.
     * @throws Exception if the fixture or generated Alloy fails
     */
    @Test
    void printerProducesParsableSource() throws Exception {
        JsonNode value = module("", testNodes(A));
        new ModuleChecker(value).check();
        String source = new ModulePrinter(value).print();
        assertDoesNotThrow(new ParserAction(source)::run);
    }

    /**
     * Checks field declarations and bounded command syntax with Alloy.
     * @throws Exception if the parser rejects the generated source
     */
    @Test
    void printerFieldAndCommandParse() throws Exception {
        String field = "{\"tag\":\"field\",\"id\":\"draft:00000000-0000-4000-8000-000000000006\","
            + "\"name\":\"r\",\"ownerSignatureId\":\"" + A + "\",\"rangeColumns\":[\"" + A
            + "\",\"" + B + "\"],\"multiplicity\":\"set\"}";
        com.fasterxml.jackson.databind.node.ObjectNode value = (com.fasterxml.jackson.databind.node.ObjectNode)
            module(field, testNodes(A));
        com.fasterxml.jackson.databind.node.ArrayNode assertions = value.putArray("assertions");
        assertions.add(MAPPER.readTree("{\"tag\":\"assertion\",\"id\":\"draft:00000000-0000-4000-8000-000000000007\","
            + "\"name\":\"assertionA\",\"bodyId\":\"draft:00000000-0000-4000-8000-000000000009\"}"));
        ((com.fasterxml.jackson.databind.node.ArrayNode) value.path("nodes")).add(MAPPER.readTree(
            "{\"tag\":\"some_test\",\"id\":\"draft:00000000-0000-4000-8000-000000000009\","
            + "\"operandId\":\"draft:00000000-0000-4000-8000-000000000010\"}"));
        ((com.fasterxml.jackson.databind.node.ArrayNode) value.path("nodes")).add(MAPPER.readTree(
            "{\"tag\":\"field_ref\",\"id\":\"draft:00000000-0000-4000-8000-000000000010\","
            + "\"targetId\":\"draft:00000000-0000-4000-8000-000000000006\"}"));
        value.putArray("commands").add(MAPPER.readTree("{\"tag\":\"check\","
            + "\"id\":\"draft:00000000-0000-4000-8000-000000000008\","
            + "\"targetId\":\"draft:00000000-0000-4000-8000-000000000007\","
            + "\"uniformScope\":3,\"bitwidth\":4,\"maxseq\":3}"));
        new ModuleChecker(value).check();
        assertDoesNotThrow(new ParserAction(new ModulePrinter(value).print())::run);
    }

    /**
     * Verifies injected identity mapping preserves all references and the input.
     * @throws Exception if fixture decoding fails
     */
    @Test
    void remapsDraftIdentitiesConsistently() throws Exception {
        JsonNode original = module("", testNodes(A));
        new ModuleChecker(original).check();
        IdentityRemapper remapper = new IdentityRemapper(MAPPER.createObjectNode());
        JsonNode result = remapper.remap(original);
        new ModuleChecker(result).check();
        assertEquals(A, original.path("signatures").get(0).path("id").textValue());
        assertTrue(result.path("signatures").get(0).path("id").textValue().startsWith("server:"));
        assertEquals(5, remapper.mappings().size());
    }

    /**
     * Rejects a shared child even when the expression types match.
     * @throws Exception if fixture decoding fails
     */
    @Test
    void rejectsSharedExpression() throws Exception {
        String nodes = "{\"tag\":\"signature_ref\",\"id\":\"" + N + "\",\"targetId\":\"" + A
            + "\"},{\"tag\":\"equal\",\"id\":\"" + T + "\",\"leftId\":\"" + N
            + "\",\"rightId\":\"" + N + "\"}";
        JsonNode value = module("", nodes);
        assertThrows(IllegalArgumentException.class, new ModuleChecker(value)::check);
    }

    /**
     * Rejects equality across disjoint nominal signatures.
     * @throws Exception if fixture decoding fails
     */
    @Test
    void rejectsDifferentNominalSchemas() throws Exception {
        String other = "draft:00000000-0000-4000-8000-000000000006";
        String nodes = "{\"tag\":\"signature_ref\",\"id\":\"" + N + "\",\"targetId\":\"" + A
            + "\"},{\"tag\":\"signature_ref\",\"id\":\"" + other + "\",\"targetId\":\"" + B
            + "\"},{\"tag\":\"equal\",\"id\":\"" + T + "\",\"leftId\":\"" + N
            + "\",\"rightId\":\"" + other + "\"}";
        JsonNode value = module("", nodes);
        assertThrows(IllegalArgumentException.class, new ModuleChecker(value)::check);
    }

    /** Checks comment offsets and string exclusion using Unicode and CRLF. */
    @Test
    void textTriviaUsesByteOffsetsAndActualTokens() {
        String source = "// 😀\r\nsig A {} // é\r\n\"// not a comment\"";
        JsonNode tokens = new TextTriviaScanner(source).scan();
        assertEquals(2, tokens.size());
        assertEquals(7, tokens.get(0).path("endByte").intValue());
        assertEquals("module-leading", tokens.get(0).path("anchor").path("kind").textValue());
        assertEquals("module-trailing", tokens.get(1).path("anchor").path("kind").textValue());
    }

    /**
     * Reconstructs a resolved parser body through declaration object identity.
     * @throws Exception if Alloy rejects the fixture
     */
    @Test
    void readsParserExpressionByIdentity() throws Exception {
        edu.mit.csail.sdg.parser.CompModule parsed = CompUtil.parseEverything_fromString(A4Reporter.NOP,
            "sig A {} pred p { some A } run p");
        AlloyExpressionReader reader = new AlloyExpressionReader(false);
        reader.bind(parsed.getAllReachableUserDefinedSigs().get(0), A);
        String id = reader.read(parsed.getAllFunc().get(0).getBody());
        JsonNode nodes = reader.nodes();
        assertEquals("some_test", nodes.get(0).path("tag").textValue());
        assertEquals(id, nodes.get(0).path("id").textValue());
        assertEquals(A, nodes.get(1).path("targetId").textValue());
    }

    /**
     * Checks that the parser preserves scoped variable object identity.
     * @throws Exception if the parser rejects the fixture
     */
    @Test
    void readsQuantifiedBinder() throws Exception {
        edu.mit.csail.sdg.parser.CompModule parsed = CompUtil.parseEverything_fromString(A4Reporter.NOP,
            "sig A {} pred p { all x: A | x in A } run p");
        AlloyExpressionReader reader = new AlloyExpressionReader(false);
        reader.bind(parsed.getAllReachableUserDefinedSigs().get(0), A);
        reader.read(parsed.getAllFunc().get(0).getBody());
        JsonNode nodes = reader.nodes();
        assertEquals("all_quant", nodes.get(0).path("tag").textValue());
        assertEquals("variable_ref", nodes.get(2).path("tag").textValue());
        assertEquals(nodes.get(0).path("binder").path("id"), nodes.get(2).path("targetId"));
    }

    /**
     * Handles Alloy's field-owner restriction for trusted generated source.
     * @throws Exception if Alloy rejects the fixture
     */
    @Test
    void readsGeneratedFieldReference() throws Exception {
        edu.mit.csail.sdg.parser.CompModule parsed = CompUtil.parseEverything_fromString(A4Reporter.NOP,
            "sig B {} sig A { r: set B } pred p { some r } run p");
        AlloyExpressionReader reader = new AlloyExpressionReader(true);
        for (edu.mit.csail.sdg.ast.Sig sig : parsed.getAllReachableUserDefinedSigs()) {
            reader.bind(sig, sig.label.endsWith("/A") ? A : B);
            for (edu.mit.csail.sdg.ast.Sig.Field field : sig.getFields()) reader.bind(field, F);
        }
        reader.read(parsed.getAllFunc().get(0).getBody());
        assertEquals("field_ref", reader.nodes().get(1).path("tag").textValue());
        assertEquals(F, reader.nodes().get(1).path("targetId").textValue());
    }

    /**
     * Reads tuple field and parameter columns from declaration expressions.
     * @throws Exception if Alloy rejects the fixture
     */
    @Test
    void derivesSchemasFromDeclarationObjects() throws Exception {
        edu.mit.csail.sdg.parser.CompModule parsed = CompUtil.parseEverything_fromString(A4Reporter.NOP,
            "sig B {} sig C {} sig A { r: set (B -> C) } pred p[x: set (B -> C)] { some x } run p");
        java.util.Map<Object, String> ids = new java.util.IdentityHashMap<>();
        edu.mit.csail.sdg.ast.Sig.Field field = null;
        for (edu.mit.csail.sdg.ast.Sig sig : parsed.getAllReachableUserDefinedSigs()) {
            ids.put(sig, sig.label);
            if (!sig.getFields().isEmpty()) field = sig.getFields().get(0);
        }
        AlloySchemaReader reader = new AlloySchemaReader(ids);
        assertEquals("set", reader.fieldMultiplicity(field.decl().expr));
        assertEquals(java.util.List.of("this/B", "this/C"), reader.fieldColumns(field.decl().expr));
        assertEquals(java.util.List.of("this/B", "this/C"), reader.parameter(parsed.getAllFunc().get(0).decls.get(0).expr));
    }

    /**
     * Elaborates generated declarations and an authored formula.
     * @throws Exception if Alloy rejects the fixture
     */
    @Test
    void readsGeneratedModule() throws Exception {
        JsonNode original = module("", testNodes(A));
        new ModuleChecker(original).check();
        String source = new ModulePrinter(original).print();
        edu.mit.csail.sdg.parser.CompModule parsed = CompUtil.parseEverything_fromString(A4Reporter.NOP, source);
        JsonNode output = new AlloyModuleReader(parsed, true).read(0);
        assertEquals(2, output.path("signatures").size());
        assertEquals(1, output.path("facts").size());
        assertEquals(2, output.path("nodes").size());
    }

    /**
     * Elaborates set-valued predicate parameters and calls from parser objects.
     * @throws Exception if Alloy rejects the fixture
     */
    @Test
    void readsPredicatesAndCalls() throws Exception {
        String source = "sig A {} pred p[x: set A] { some x } pred q[] { p[A] } run q for 3 but 4 Int, 3 seq";
        edu.mit.csail.sdg.parser.CompModule parsed = CompUtil.parseEverything_fromString(A4Reporter.NOP, source);
        JsonNode output = new AlloyModuleReader(parsed, true).read(1);
        assertEquals(2, output.path("predicates").size());
        assertEquals(1, output.path("commands").size());
        assertEquals("predicate_call", output.path("nodes").get(2).path("tag").textValue());
    }

    /**
     * Preserves parser-specified scopes in text-only command descriptors.
     * @throws Exception if Alloy rejects the fixture
     */
    @Test
    void commandDescriptorsPreserveScopeDetails() throws Exception {
        String source = "sig A {} pred p { some A } run p for 4 but exactly 2 A";
        edu.mit.csail.sdg.parser.CompModule parsed = CompUtil.parseEverything_fromString(A4Reporter.NOP, source);
        JsonNode descriptors = new CommandDescriptors(parsed, null).read(1);
        JsonNode command = descriptors.get(0);
        assertEquals("run", command.path("kind").textValue());
        assertEquals(4, command.path("options").path("overall").intValue());
        assertTrue(command.path("options").path("scopes").get(0).path("isExact").booleanValue());
        assertEquals(2, command.path("options").path("scopes").get(0).path("endingScope").intValue());
    }

    /**
     * Suppresses Alloy's synthetic command for an author-empty module.
     * @throws Exception if Alloy rejects the fixture
     */
    @Test
    void noAuthoredCommandsHaveNoDescriptors() throws Exception {
        edu.mit.csail.sdg.parser.CompModule parsed = CompUtil.parseEverything_fromString(A4Reporter.NOP, "sig A {}");
        assertEquals(0, new CommandDescriptors(parsed, null).read(0).size());
    }

    /** Checks authored command counting ignores comments and nested strings. */
    @Test
    void countsOnlyTopLevelAuthoredCommands() {
        String source = "// run ignored\r\nsig A {} fact f { some A /* check ignored */ } "
            + "pred p { some A } run p for 3 check p";
        assertEquals(2, new CommandTokenCounter(source).count());
        assertEquals(0, new CommandTokenCounter("sig A {} // run p\n").count());
    }

    /**
     * Compares an Alloy-elaborated printer result by declaration identity.
     * @throws Exception if Alloy rejects the fixture
     */
    @Test
    void comparesPrintedAndParsedModule() throws Exception {
        JsonNode original = module("", testNodes(A));
        new ModuleChecker(original).check();
        String source = new ModulePrinter(original).print();
        edu.mit.csail.sdg.parser.CompModule parsed = CompUtil.parseEverything_fromString(A4Reporter.NOP, source);
        JsonNode output = new AlloyModuleReader(parsed, true).read(0);
        assertTrue(new ModuleEquivalence(original, output).matches());
        JsonNode changed = module("", testNodes(B));
        new ModuleChecker(changed).check();
        assertFalse(new ModuleEquivalence(changed, output).matches());
    }

    /**
     * Tracks distinct nested expression intervals in generated source.
     * @throws Exception if fixture decoding fails
     */
    @Test
    void printerRecordsExactExpressionSpans() throws Exception {
        JsonNode value = module("", testNodes(A));
        new ModuleChecker(value).check();
        ModulePrinter printer = new ModulePrinter(value);
        String source = printer.print();
        JsonNode spans = printer.occurrences();
        assertEquals(4, spans.size());
        JsonNode inner = spans.get(2);
        assertEquals(N, inner.path("nodeId").textValue());
        assertEquals("A", source.substring(inner.path("startUtf16").intValue(), inner.path("endUtf16").intValue()));
        JsonNode outer = spans.get(3);
        assertEquals(T, outer.path("nodeId").textValue());
        assertEquals("(some (A))", source.substring(outer.path("startUtf16").intValue(), outer.path("endUtf16").intValue()));
    }

    /**
     * Compares associative Boolean grouping without permuting operands.
     * @throws Exception if Alloy rejects either fixture
     */
    @Test
    void comparesAssociativeBooleanOrder() throws Exception {
        String head = "sig A {} pred p { ";
        String tail = " } run p for 3 but 4 Int, 3 seq";
        String a = head + "some A and (no A and one A)" + tail;
        String b = head + "(some A and no A) and one A" + tail;
        String c = head + "one A and no A and some A" + tail;
        JsonNode left = new AlloyModuleReader(CompUtil.parseEverything_fromString(A4Reporter.NOP, a), true).read(1);
        JsonNode right = new AlloyModuleReader(CompUtil.parseEverything_fromString(A4Reporter.NOP, b), true).read(1);
        JsonNode reordered = new AlloyModuleReader(CompUtil.parseEverything_fromString(A4Reporter.NOP, c), true).read(1);
        assertTrue(new ModuleEquivalence(left, right).matches());
        assertFalse(new ModuleEquivalence(left, reordered).matches());
    }

    /**
     * Round-trips set-valued parameters, calls, quantifiers and bounded commands.
     * @throws Exception if parsing or elaboration rejects the fixture
     */
    @Test
    void roundTripsScopedPredicatesAndCommands() throws Exception {
        String source = "sig A {} pred p[x: set A] { all z: A | z in x } "
            + "pred q[] { p[A] } run q for 3 but 4 Int, 3 seq";
        JsonNode first = new AlloyModuleReader(CompUtil.parseEverything_fromString(A4Reporter.NOP, source), true).read(1);
        String printed = new ModulePrinter(first).print();
        JsonNode second = new AlloyModuleReader(CompUtil.parseEverything_fromString(A4Reporter.NOP, printed), true).read(1);
        assertTrue(new ModuleEquivalence(first, second).matches());
    }

    /**
     * Preserves a Unicode comment while shifting generated expression spans.
     * @throws Exception if the generated source fails to parse
     */
    @Test
    void transportsCommentAndShiftsSpans() throws Exception {
        JsonNode value = module("", testNodes(A));
        new ModuleChecker(value).check();
        ModulePrinter printer = new ModulePrinter(value);
        String printed = printer.print();
        com.fasterxml.jackson.databind.node.ObjectNode base = MAPPER.createObjectNode();
        base.put("mode", "BLOCK_SUPPORTED");
        base.put("source", "/*é*/");
        com.fasterxml.jackson.databind.node.ObjectNode token = base.putArray("trivia").addObject();
        token.put("startByte", 0).put("endByte", 6).put("order", 0);
        token.putObject("anchor").put("kind", "expression").put("nodeId", N).put("role", "reference").put("side", "leading");
        JsonNode result = new TriviaTransport(printed, printer.occurrences(), printer)
            .apply(base, MAPPER.createArrayNode(), java.util.Map.of());
        String rendered = result.path("source").textValue();
        assertDoesNotThrow(new ParserAction(rendered)::run);
        assertEquals(1, result.path("trivia").size());
        assertEquals(0, result.path("orphaned").intValue());
        assertTrue(rendered.contains("/*é*/"));
        for (JsonNode span : result.path("occurrences")) {
            if (span.path("nodeId").asText().equals(N) && span.path("role").asText().equals("reference")) {
                assertEquals("A", rendered.substring(span.path("startUtf16").intValue(), span.path("endUtf16").intValue()));
            }
        }
    }

    /**
     * Copies a deleted node's comment while retaining the original as an orphan.
     * @throws Exception if fixture decoding or source parsing fails
     */
    @Test
    void deletedSourceCommentIsOrphanedAndCopied() throws Exception {
        String target = "server:00000000-0000-4000-8000-000000000006";
        String draft = "draft:00000000-0000-4000-8000-000000000007";
        JsonNode value = module("", testNodes(A).replace(N, target));
        new ModuleChecker(value).check();
        ModulePrinter printer = new ModulePrinter(value);
        String printed = printer.print();
        com.fasterxml.jackson.databind.node.ObjectNode base = MAPPER.createObjectNode();
        base.put("mode", "BLOCK_SUPPORTED").put("source", "// old");
        com.fasterxml.jackson.databind.node.ObjectNode token = base.putArray("trivia").addObject();
        token.put("startByte", 0).put("endByte", 6).put("order", 0);
        token.putObject("anchor").put("kind", "expression").put("nodeId", N).put("role", "reference").put("side", "leading");
        com.fasterxml.jackson.databind.node.ArrayNode copies = MAPPER.createArrayNode();
        copies.addObject().put("sourceNodeId", N).put("targetNodeId", draft);
        JsonNode result = new TriviaTransport(printed, printer.occurrences(), printer)
            .apply(base, copies, java.util.Map.of(draft, target));
        assertEquals(2, result.path("trivia").size());
        assertEquals(1, result.path("orphaned").intValue());
        assertDoesNotThrow(new ParserAction(result.path("source").textValue())::run);
    }

    /**
     * Round-trips a checked module containing all 23 expression tags.
     * @throws Exception if parsing or elaboration fails
     */
    @Test
    void roundTripsEveryExpressionTag() throws Exception {
        String source = "sig A { r: set A } pred p[x: set A] { some x } pred q[] { "
            + "(some A and no A) and (one A or lone A) and (not no A) and "
            + "((some A) implies (no A)) and ((some A) iff (one A)) and "
            + "(A = A) and (A in A) and (some (A + A)) and (some (A & A)) and "
            + "(some (A - A)) and (some (A.r)) and (some (A -> A)) and (some (~r)) and "
            + "(all z: A | z in A) and (some w: A | w in A) and p[A] } "
            + "run q for 3 but 4 Int, 3 seq";
        JsonNode first = new AlloyModuleReader(CompUtil.parseEverything_fromString(A4Reporter.NOP, source), true).read(1);
        java.util.Set<String> tags = new java.util.HashSet<>();
        for (JsonNode node : first.path("nodes")) tags.add(node.path("tag").textValue());
        assertEquals(23, tags.size());
        String printed = new ModulePrinter(first).print();
        JsonNode second = new AlloyModuleReader(CompUtil.parseEverything_fromString(A4Reporter.NOP, printed), true).read(1);
        assertTrue(new ModuleEquivalence(first, second).matches());
    }

    /**
     * Parses exact CRLF source through the same file-based worker policy.
     * @throws Exception if parser or isolated I/O fails
     */
    @Test
    void parsesExactSourceThroughWorkerPolicy() throws Exception {
        String source = "// 😀\r\nsig A {}\r\npred p { some A }\r\nrun p for 3\r\n";
        edu.mit.csail.sdg.parser.CompModule parsed = SourceParser.parse(source);
        assertEquals(1, new CommandTokenCounter(source).count());
        assertEquals(1, parsed.getAllCommands().size());
    }

    /**
     * Maps exact file-parser reference tokens and declines unverified coordinates.
     * @throws Exception if Alloy rejects the fixture
     */
    @Test
    void mapsVerifiedSourceReferences() throws Exception {
        String source = "sig A {} pred p { some A } run p for 3 but 4 Int, 3 seq";
        AlloyModuleReader reader = new AlloyModuleReader(SourceParser.parse(source), false);
        JsonNode value = reader.read(1);
        JsonNode spans = new SourceReferenceMapper(source, value, reader.origins()).map();
        assertTrue(spans.size() >= 2);
        boolean found = false;
        for (JsonNode span : spans) {
            if (span.path("role").asText().equals("reference")) {
                assertEquals("A", source.substring(span.path("startUtf16").intValue(), span.path("endUtf16").intValue()));
                found = true;
            }
        }
        assertTrue(found);
        assertEquals(0, new SourceReferenceMapper("// displaced\n" + source, value, reader.origins()).map().size());
    }

    /**
     * Rejects interleaved owners and accepts the same grouped fields.
     * @throws Exception if fixture decoding fails
     */
    @Test
    void rejectsInterleavedFieldOwners() throws Exception {
        String prefix = "{\"tag\":\"field\",\"id\":\"draft:00000000-0000-4000-8000-00000000000";
        String a = prefix + "6\",\"name\":\"r\",\"ownerSignatureId\":\"" + A
            + "\",\"rangeColumns\":[\"" + A + "\"],\"multiplicity\":\"set\"}";
        String b = prefix + "7\",\"name\":\"s\",\"ownerSignatureId\":\"" + B
            + "\",\"rangeColumns\":[\"" + A + "\"],\"multiplicity\":\"set\"}";
        String c = prefix + "8\",\"name\":\"t\",\"ownerSignatureId\":\"" + A
            + "\",\"rangeColumns\":[\"" + A + "\"],\"multiplicity\":\"set\"}";
        JsonNode bad = module(a + "," + b + "," + c, testNodes(A));
        JsonNode good = module(a + "," + c + "," + b, testNodes(A));
        assertThrows(IllegalArgumentException.class, new ModuleChecker(bad)::check);
        assertDoesNotThrow(new ModuleChecker(good)::check);
    }

    /**
     * Ensures registry storage order does not affect printed tree semantics.
     * @throws Exception if fixture decoding fails
     */
    @Test
    void shuffledNodeRegistryHasSameRoundTrip() throws Exception {
        JsonNode original = module("", testNodes(A));
        com.fasterxml.jackson.databind.node.ObjectNode shuffled = original.deepCopy();
        com.fasterxml.jackson.databind.node.ArrayNode nodes = (com.fasterxml.jackson.databind.node.ArrayNode) shuffled.path("nodes");
        JsonNode first = nodes.remove(0);
        nodes.add(first);
        new ModuleChecker(original).check();
        new ModuleChecker(shuffled).check();
        assertEquals(new ModulePrinter(original).print(), new ModulePrinter(shuffled).print());
        assertTrue(new ModuleEquivalence(original, shuffled).matches());
    }

    /** Checks lexical screening avoids inventing IR for excluded source forms. */
    @Test
    void sourceFragmentGuardRejectsUnsupportedSyntax() {
        assertTrue(new SourceFragmentGuard("// 😀\r\nsig A {} pred p { some A } run p for 3 but 4 Int, 3 seq").supports());
        assertFalse(new SourceFragmentGuard("sig A, B {} run {} ").supports());
        assertFalse(new SourceFragmentGuard("sig A {} fact f { some (A <: A) }").supports());
        assertFalse(new SourceFragmentGuard("module example\nsig A {} ").supports());
    }

    /**
     * Anchors source comments to a verified reference and declaration boundary.
     * @throws Exception if parser or lexical analysis rejects the fixture
     */
    @Test
    void attachesSourceCommentsToVerifiedTokens() throws Exception {
        String source = "sig A {} // signature\npred p { some\n// before ref\nA } run p for 3 but 4 Int, 3 seq";
        AlloyModuleReader reader = new AlloyModuleReader(SourceParser.parse(source), false);
        JsonNode value = reader.read(1);
        JsonNode spans = new SourceReferenceMapper(source, value, reader.origins()).map();
        JsonNode tokens = new SourceTriviaAttacher(source, value, spans).attach();
        assertEquals(2, tokens.size());
        assertEquals("declaration", tokens.get(0).path("anchor").path("kind").textValue());
        assertEquals("trailing", tokens.get(0).path("anchor").path("side").textValue());
        assertEquals("expression", tokens.get(1).path("anchor").path("kind").textValue());
        assertEquals("reference", tokens.get(1).path("anchor").path("role").textValue());
    }

    /**
     * Attaches field, parameter, quantifier and command comments to owners.
     * @throws Exception if parser rejects the fixture
     */
    @Test
    void attachesDeclarationAndBinderTrivia() throws Exception {
        String source = "sig A { r: set A /*field*/ } "
            + "pred p[x: set A /*param*/] { all y: A /*quant*/ | y in x } "
            + "pred q { p[A] } run q for 3 /*command*/ but 4 Int, 3 seq";
        AlloyModuleReader reader = new AlloyModuleReader(SourceParser.parse(source), false);
        JsonNode value = reader.read(1);
        JsonNode spans = new SourceReferenceMapper(source, value, reader.origins()).map();
        JsonNode trivia = new SourceTriviaAttacher(source, value, spans).attach();
        assertEquals(4, trivia.size());
        assertEquals("declaration", trivia.get(0).path("anchor").path("kind").textValue());
        assertEquals("binder", trivia.get(1).path("anchor").path("kind").textValue());
        assertEquals("binder", trivia.get(2).path("anchor").path("kind").textValue());
        assertEquals("declaration", trivia.get(3).path("anchor").path("kind").textValue());
    }

    /**
     * Rejects repeated destinations and foreign source nodes in comment copies.
     * @throws Exception if fixture decoding fails
     */
    @Test
    void validatesExplicitCopyIdentityAndUniqueness() throws Exception {
        String oldId = N.replace("draft:", "server:");
        com.fasterxml.jackson.databind.node.ObjectNode base = MAPPER.createObjectNode();
        base.put("mode", "BLOCK_SUPPORTED");
        base.set("module", module("", testNodes(A).replace(N, oldId)));
        JsonNode candidate = module("", testNodes(A));
        com.fasterxml.jackson.databind.node.ArrayNode copies = MAPPER.createArrayNode();
        copies.addObject().put("sourceNodeId", oldId).put("targetNodeId", N);
        assertDoesNotThrow(new CopyAction(base, candidate, copies)::run);
        copies.addObject().put("sourceNodeId", oldId).put("targetNodeId", N);
        assertThrows(IllegalArgumentException.class, new CopyAction(base, candidate, copies)::run);
    }

    /** Captures arguments for a documented copy-validator test callback. */
    private static final class CopyAction {
        private final JsonNode base;
        private final JsonNode candidate;
        private final JsonNode copies;

        /**
         * Creates a copy test callback.
         * @param base authorized base
         * @param candidate candidate module
         * @param copies explicit mappings
         */
        private CopyAction(JsonNode base, JsonNode candidate, JsonNode copies) {
            this.base = base;
            this.candidate = candidate;
            this.copies = copies;
        }

        /** Runs copy validation. */
        private void run() {
            new CopyValidator(base, candidate).check(copies);
        }
    }

    /**
     * Reprints a supported source with declaration and binder comments intact.
     * @throws Exception if parsing or elaboration fails
     */
    @Test
    void sourceCommentsSurviveBlockReprint() throws Exception {
        String source = "sig A { r: set A /*field*/ } "
            + "pred p[x: set A /*param*/] { all y: A /*quant*/ | y in x } "
            + "pred q { p[A] } run q for 3 /*command*/ but 4 Int, 3 seq";
        assertTrue(new SourceFragmentGuard(source).supports());
        AlloyModuleReader reader = new AlloyModuleReader(SourceParser.parse(source), false);
        JsonNode first = reader.read(1);
        JsonNode maps = new SourceReferenceMapper(source, first, reader.origins()).map();
        JsonNode trivia = new SourceTriviaAttacher(source, first, maps).attach();
        com.fasterxml.jackson.databind.node.ObjectNode base = MAPPER.createObjectNode();
        base.put("mode", "BLOCK_SUPPORTED").put("source", source);
        base.set("trivia", trivia);
        ModulePrinter printer = new ModulePrinter(first);
        String printed = printer.print();
        JsonNode result = new TriviaTransport(printed, printer.occurrences(), printer)
            .apply(base, MAPPER.createArrayNode(), java.util.Map.of());
        String reprinted = result.path("source").asText();
        JsonNode second = new AlloyModuleReader(SourceParser.parse(reprinted), true).read(1);
        assertTrue(new ModuleEquivalence(first, second).matches());
        assertEquals(4, result.path("trivia").size());
        assertEquals(0, result.path("orphaned").intValue());
    }

    /**
     * Verifies historical source, map boundaries and exact comment inventory.
     * @throws Exception if fixture decoding fails
     */
    @Test
    void historicalArtifactIntegrityChecksSourceAndMaps() throws Exception {
        JsonNode value = module("", testNodes(A));
        new ModuleChecker(value).check();
        ModulePrinter printer = new ModulePrinter(value);
        String source = printer.print();
        com.fasterxml.jackson.databind.node.ObjectNode artifact = MAPPER.createObjectNode();
        artifact.put("mode", "BLOCK_SUPPORTED").put("source", source).put("sourceHash", ArtifactIntegrity.hash(source));
        artifact.set("module", value);
        artifact.set("occurrences", printer.occurrences());
        artifact.putArray("trivia");
        assertDoesNotThrow(new ArtifactIntegrity(artifact)::check);
        artifact.put("sourceHash", "0".repeat(64));
        assertThrows(IllegalArgumentException.class, new ArtifactIntegrity(artifact)::check);
    }

    /**
     * Validates a full block candidate through identity remapping and reparse.
     * @throws Exception if validation fails
     */
    @Test
    void validatesBlockCandidateWithoutPublicAcceptance() throws Exception {
        com.fasterxml.jackson.databind.node.ObjectNode candidate = MAPPER.createObjectNode();
        candidate.put("mode", "BLOCK_SUPPORTED");
        candidate.set("module", module("", testNodes(A)));
        candidate.putArray("presentationCopies");
        com.fasterxml.jackson.databind.node.ObjectNode base = MAPPER.createObjectNode();
        base.put("mode", "TEXT_ONLY").put("source", "").put("sourceHash", ArtifactIntegrity.hash(""));
        base.putNull("module");
        base.putArray("occurrences");
        base.putArray("trivia");
        JsonNode result = new BlockValidation(candidate, base, MAPPER.createObjectNode()).validate();
        assertEquals("BLOCK_SUPPORTED", result.path("mode").textValue());
        assertEquals(5, result.path("idRemapping").size());
        assertEquals(0, result.path("analysisDescriptors").size());
        new ArtifactIntegrity(result).check();
    }

    /**
     * Preserves exact source bytes for both supported and text-only syntax.
     * @throws Exception if validation fails
     */
    @Test
    void validatesSourceVariantsWithoutPublicAcceptance() throws Exception {
        String source = "// 😀\r\nsig A {} pred p { some A } run p for 3 but 4 Int, 3 seq\r\n";
        com.fasterxml.jackson.databind.node.ObjectNode candidate = MAPPER.createObjectNode();
        candidate.put("mode", "SOURCE").put("source", source);
        JsonNode block = new SourceValidation(candidate).validate();
        assertEquals("BLOCK_SUPPORTED", block.path("mode").textValue());
        assertEquals(source, block.path("source").textValue());
        new ArtifactIntegrity(block).check();
        String unsupported = "sig A, B {} run {} for 3";
        candidate.put("source", unsupported);
        JsonNode text = new SourceValidation(candidate).validate();
        assertEquals("TEXT_ONLY", text.path("mode").textValue());
        assertTrue(text.path("module").isNull());
        assertEquals(unsupported, text.path("source").textValue());
        new ArtifactIntegrity(text).check();
    }

    /**
     * Revalidates a historical block without altering immutable content.
     * @throws Exception if validation fails
     */
    @Test
    void historyPreservesBlockContent() throws Exception {
        com.fasterxml.jackson.databind.node.ObjectNode candidate = MAPPER.createObjectNode();
        candidate.put("mode", "BLOCK_SUPPORTED");
        candidate.set("module", module("", testNodes(A)));
        candidate.putArray("presentationCopies");
        com.fasterxml.jackson.databind.node.ObjectNode base = MAPPER.createObjectNode();
        base.put("mode", "TEXT_ONLY").put("source", "").put("sourceHash", ArtifactIntegrity.hash(""));
        base.putNull("module");
        base.putArray("occurrences");
        base.putArray("trivia");
        JsonNode historical = new BlockValidation(candidate, base, MAPPER.createObjectNode()).validate();
        JsonNode fresh = new HistoryValidation(historical, simpleInventory(historical.path("module"))).revalidate();
        for (String key : java.util.List.of("source", "sourceHash", "module", "occurrences", "trivia")) {
            assertEquals(historical.path(key), fresh.path(key));
        }
        assertEquals(0, fresh.path("idRemapping").size());
    }

    /**
     * Builds inventory for a fixture with signatures, facts and expressions.
     * @param module checked module
     * @return server identity inventory
     */
    private JsonNode simpleInventory(JsonNode module) {
        com.fasterxml.jackson.databind.node.ObjectNode inventory = MAPPER.createObjectNode();
        for (JsonNode signature : module.path("signatures")) inventory.put(signature.path("id").asText(), "signature");
        for (JsonNode fact : module.path("facts")) inventory.put(fact.path("id").asText(), "fact");
        for (JsonNode node : module.path("nodes")) inventory.put(node.path("id").asText(), "expression");
        return inventory;
    }

    /**
     * Keeps exact authored CRLF and comments for an unchanged block candidate.
     * @throws Exception if validation fails
     */
    @Test
    void unchangedBlocksPreserveAuthoredBytes() throws Exception {
        String source = "// 😀\r\nsig A {}\r\nfact f { some A }\r\n";
        com.fasterxml.jackson.databind.node.ObjectNode text = MAPPER.createObjectNode();
        text.put("mode", "SOURCE").put("source", source);
        JsonNode old = new SourceValidation(text).validate();
        com.fasterxml.jackson.databind.node.ObjectNode candidate = MAPPER.createObjectNode();
        candidate.put("mode", "BLOCK_SUPPORTED");
        candidate.set("module", old.path("module").deepCopy());
        candidate.putArray("presentationCopies");
        JsonNode result = new BlockValidation(candidate, old, simpleInventory(old.path("module"))).validate();
        assertEquals(source, result.path("source").textValue());
        assertEquals(old.path("trivia"), result.path("trivia"));
        assertEquals(old.path("occurrences"), result.path("occurrences"));
    }

    /**
     * Preserves text-only historical source and its no-graph status.
     * @throws Exception if validation fails
     */
    @Test
    void historyPreservesTextOnlyContent() throws Exception {
        com.fasterxml.jackson.databind.node.ObjectNode text = MAPPER.createObjectNode();
        text.put("mode", "SOURCE").put("source", "// note\r\nsig A, B {} run {} for 3");
        JsonNode old = new SourceValidation(text).validate();
        assertEquals("TEXT_ONLY", old.path("mode").asText());
        JsonNode fresh = new HistoryValidation(old, MAPPER.createObjectNode()).revalidate();
        for (String key : java.util.List.of("source", "sourceHash", "module", "occurrences", "trivia")) {
            assertEquals(old.path(key), fresh.path(key));
        }
    }

    /**
     * Validates an empty source as the valid empty block module.
     * @throws Exception if the parser rejects the fixture
     */
    @Test
    void emptySourceIsSupported() throws Exception {
        com.fasterxml.jackson.databind.node.ObjectNode text = MAPPER.createObjectNode();
        text.put("mode", "SOURCE").put("source", "");
        JsonNode result = new SourceValidation(text).validate();
        assertEquals("BLOCK_SUPPORTED", result.path("mode").asText());
        assertEquals(0, result.path("analysisDescriptors").size());
        assertEquals(0, result.path("module").path("nodes").size());
    }

    /**
     * Rejects an unknown wire field for each of the 23 constructor tags.
     * @throws Exception if the Alloy fixture fails
     */
    @Test
    void everyTagRejectsUnknownFields() throws Exception {
        String source = "sig A { r: set A } pred p[x: set A] { some x } pred q[] { "
            + "(some A and no A) and (one A or lone A) and (not no A) and "
            + "((some A) implies (no A)) and ((some A) iff (one A)) and "
            + "(A = A) and (A in A) and (some (A + A)) and (some (A & A)) and "
            + "(some (A - A)) and (some (A.r)) and (some (A -> A)) and (some (~r)) and "
            + "(all z: A | z in A) and (some w: A | w in A) and p[A] } "
            + "run q for 3 but 4 Int, 3 seq";
        JsonNode module = new AlloyModuleReader(SourceParser.parse(source), true).read(1);
        java.util.Set<String> tags = new java.util.HashSet<>();
        for (JsonNode node : module.path("nodes")) {
            String tag = node.path("tag").textValue();
            if (!tags.add(tag)) continue;
            com.fasterxml.jackson.databind.node.ObjectNode changed = module.deepCopy();
            for (JsonNode item : changed.path("nodes")) {
                if (item.path("id").equals(node.path("id"))) ((com.fasterxml.jackson.databind.node.ObjectNode) item).put("unexpected", true);
            }
            assertThrows(IllegalArgumentException.class, new ModuleChecker(changed)::check);
        }
        assertEquals(23, tags.size());
    }

    /**
     * Exercises the public source and history APIs without changing content.
     * @throws Exception if validation fails
     */
    @Test
    void publicSourceAndHistoryPreserveExactBytes() throws Exception {
        String source = "// 😀\r\nsig A {}\r\nfact f { some A }\r\n";
        com.fasterxml.jackson.databind.node.ObjectNode candidate = MAPPER.createObjectNode();
        candidate.put("mode", "SOURCE").put("source", source);
        DocumentEngine engine = new DocumentEngine();
        JsonNode first = engine.validate(candidate, MAPPER.createObjectNode(), MAPPER.createObjectNode(), "policy");
        JsonNode history = engine.revalidate(first, simpleInventory(first.path("module")), "policy");
        assertEquals("BLOCK_SUPPORTED", first.path("mode").asText());
        for (String key : java.util.List.of("source", "sourceHash", "module", "occurrences", "trivia")) {
            assertEquals(first.path(key), history.path(key));
        }
    }

    /**
     * Exercises typed INVALID_DRAFT for an interleaved field array.
     * @throws Exception if fixture decoding fails
     */
    @Test
    void publicEngineDeniesInterleavedFieldOwners() throws Exception {
        String prefix = "{\"tag\":\"field\",\"id\":\"draft:00000000-0000-4000-8000-00000000000";
        String a = prefix + "6\",\"name\":\"r\",\"ownerSignatureId\":\"" + A
            + "\",\"rangeColumns\":[\"" + A + "\"],\"multiplicity\":\"set\"}";
        String b = prefix + "7\",\"name\":\"s\",\"ownerSignatureId\":\"" + B
            + "\",\"rangeColumns\":[\"" + A + "\"],\"multiplicity\":\"set\"}";
        String c = prefix + "8\",\"name\":\"t\",\"ownerSignatureId\":\"" + A
            + "\",\"rangeColumns\":[\"" + A + "\"],\"multiplicity\":\"set\"}";
        com.fasterxml.jackson.databind.node.ObjectNode candidate = MAPPER.createObjectNode();
        candidate.put("mode", "BLOCK_SUPPORTED");
        candidate.set("module", module(a + "," + b + "," + c, testNodes(A)));
        candidate.putArray("presentationCopies");
        DocumentValidationException denied = assertThrows(DocumentValidationException.class, new EngineAction(candidate)::run);
        assertEquals("INVALID_DRAFT", denied.code());
    }

    /** Captures a candidate for the public-engine denial test. */
    private static final class EngineAction {
        private final JsonNode candidate;

        /**
         * Creates the callback.
         * @param candidate complete candidate
         */
        private EngineAction(JsonNode candidate) {
            this.candidate = candidate;
        }

        /**
         * Runs candidate validation.
         * @throws DocumentValidationException when the candidate is invalid
         */
        private void run() throws DocumentValidationException {
            new DocumentEngine().validate(candidate, MAPPER.createObjectNode(), MAPPER.createObjectNode(), "policy");
        }
    }

    /**
     * Maps verified non-BMP, combining-mark and CRLF source references.
     * @throws Exception if file parser rejects the fixture
     */
    @Test
    void mapsVerifiedUnicodeAndCrLfReferences() throws Exception {
        String source = "// 😀 é\r\nsig A {}\r\npred p { some A }\r\nrun p for 3 but 4 Int, 3 seq\r\n";
        AlloyModuleReader reader = new AlloyModuleReader(SourceParser.parse(source), false);
        JsonNode value = reader.read(1);
        JsonNode spans = new SourceReferenceMapper(source, value, reader.origins()).map();
        boolean found = false;
        for (JsonNode span : spans) {
            if (span.path("role").asText().equals("reference")) {
                assertEquals("A", source.substring(span.path("startUtf16").intValue(), span.path("endUtf16").intValue()));
                found = true;
            }
        }
        assertTrue(found);
    }

    /**
     * Maps a reference after a supplementary character on the same CRLF line.
     * @throws Exception if the file parser rejects the fixture
     */
    @Test
    void mapsReferenceAfterNonBmpOnSameLine() throws Exception {
        String source = "sig A {}\r\npred p { /* 😀 */ some A }\r\nrun p for 3 but 4 Int, 3 seq";
        AlloyModuleReader reader = new AlloyModuleReader(SourceParser.parse(source), false);
        JsonNode value = reader.read(1);
        JsonNode spans = new SourceReferenceMapper(source, value, reader.origins()).map();
        boolean found = false;
        for (JsonNode span : spans) {
            if (span.path("role").asText().equals("reference")) {
                assertEquals(source.lastIndexOf('A'), span.path("startUtf16").intValue());
                found = true;
            }
        }
        assertTrue(found);
    }

    /**
     * Revalidates a block edit while retaining authored comment bytes.
     * @throws Exception if validation fails
     */
    @Test
    void publicBlockEditPreservesComments() throws Exception {
        String source = "// 😀\r\nsig A {}\r\nfact f { some A } // trailing\r\n";
        com.fasterxml.jackson.databind.node.ObjectNode text = MAPPER.createObjectNode();
        text.put("mode", "SOURCE").put("source", source);
        DocumentEngine engine = new DocumentEngine();
        JsonNode old = engine.validate(text, MAPPER.createObjectNode(), MAPPER.createObjectNode(), "policy");
        com.fasterxml.jackson.databind.node.ObjectNode module = old.path("module").deepCopy();
        ((com.fasterxml.jackson.databind.node.ObjectNode) module.path("signatures").get(0)).put("name", "NewA");
        com.fasterxml.jackson.databind.node.ObjectNode candidate = MAPPER.createObjectNode();
        candidate.put("mode", "BLOCK_SUPPORTED").set("module", module);
        candidate.putArray("presentationCopies");
        JsonNode result = engine.validate(candidate, old, simpleInventory(module), "policy");
        assertTrue(result.path("source").asText().contains("// 😀"));
        assertTrue(result.path("source").asText().contains("// trailing"));
        assertEquals(2, result.path("trivia").size());
        assertEquals(source, old.path("source").asText());
        new ArtifactIntegrity(result).check();
    }

    /**
     * Rejects a variable reference moved outside its predicate's lexical scope.
     * @throws Exception if the parser fixture fails
     */
    @Test
    void rejectsBinderEscapeAcrossPredicates() throws Exception {
        String source = "sig A {} pred p[x: set A] { some x } pred q[] { some A } run q for 3 but 4 Int, 3 seq";
        com.fasterxml.jackson.databind.node.ObjectNode module = new AlloyModuleReader(SourceParser.parse(source), true).read(1);
        String binder = module.path("predicates").get(0).path("parameters").get(0).path("id").asText();
        for (JsonNode node : module.path("nodes")) {
            if (!node.path("tag").asText().equals("signature_ref")) continue;
            ((com.fasterxml.jackson.databind.node.ObjectNode) node).put("tag", "variable_ref").put("targetId", binder);
        }
        assertThrows(IllegalArgumentException.class, new ModuleChecker(module)::check);
    }

    /**
     * Rejects a recursive predicate dependency despite matching argument types.
     * @throws Exception if the parser fixture fails
     */
    @Test
    void rejectsRecursivePredicateDependency() throws Exception {
        String source = "sig A {} pred p[x: set A] { some x } pred q[] { p[A] } run q for 3 but 4 Int, 3 seq";
        com.fasterxml.jackson.databind.node.ObjectNode module = new AlloyModuleReader(SourceParser.parse(source), true).read(1);
        JsonNode predicate = module.path("predicates").get(0);
        for (JsonNode node : module.path("nodes")) {
            if (!node.path("id").equals(predicate.path("bodyId"))) continue;
            com.fasterxml.jackson.databind.node.ObjectNode call = (com.fasterxml.jackson.databind.node.ObjectNode) node;
            String child = call.remove("operandId").asText();
            call.put("tag", "predicate_call").put("predicateId", predicate.path("id").asText());
            call.putArray("arguments").add(child);
        }
        assertThrows(IllegalArgumentException.class, new ModuleChecker(module)::check);
    }

    /**
     * Maps a reference following a tab when file-parser coordinates agree.
     * @throws Exception if Alloy rejects the fixture
     */
    @Test
    void mapsReferenceAfterTab() throws Exception {
        String source = "sig A {}\npred p {\t some A }\nrun p for 3 but 4 Int, 3 seq";
        AlloyModuleReader reader = new AlloyModuleReader(SourceParser.parse(source), false);
        JsonNode value = reader.read(1);
        JsonNode spans = new SourceReferenceMapper(source, value, reader.origins()).map();
        boolean found = false;
        for (JsonNode span : spans) {
            if (span.path("role").asText().equals("reference")) {
                assertEquals(source.lastIndexOf('A'), span.path("startUtf16").intValue());
                found = true;
            }
        }
        assertTrue(found);
    }

    /**
     * Retains more than 2048 comments without an invented occurrence-map cap.
     * @throws Exception if source or history validation fails
     */
    @Test
    void historyRetainsManyBoundedComments() throws Exception {
        String source = "//\n".repeat(2100) + "sig A {}";
        com.fasterxml.jackson.databind.node.ObjectNode text = MAPPER.createObjectNode();
        text.put("mode", "SOURCE").put("source", source);
        JsonNode original = new SourceValidation(text).validate();
        assertEquals(2100, original.path("trivia").size());
        JsonNode restored = new HistoryValidation(original, simpleInventory(original.path("module"))).revalidate();
        assertEquals(original.path("trivia"), restored.path("trivia"));
        assertEquals(source, restored.path("source").asText());
    }

    /**
     * Keeps historical text-only mode even if its syntax is now block-supported.
     * @throws Exception if current policy rejects the fixture
     */
    @Test
    void historyDoesNotReinterpretTextOnlyMode() throws Exception {
        String source = "sig A {}";
        com.fasterxml.jackson.databind.node.ObjectNode artifact = MAPPER.createObjectNode();
        artifact.put("mode", "TEXT_ONLY").put("source", source).put("sourceHash", ArtifactIntegrity.hash(source));
        artifact.putNull("module");
        artifact.putArray("occurrences");
        artifact.putArray("trivia");
        JsonNode restored = new DocumentEngine().revalidate(artifact, MAPPER.createObjectNode(), "policy");
        assertEquals("TEXT_ONLY", restored.path("mode").asText());
        assertTrue(restored.path("module").isNull());
        assertEquals(source, restored.path("source").asText());
    }

    /**
     * Excludes declaration braces from a verified authored formula occurrence.
     * @throws Exception if the file parser rejects the fixture
     */
    @Test
    void sourceExpressionSpanExcludesDeclarationBraces() throws Exception {
        String source = "sig A {} pred p { some A } run p for 3 but 4 Int, 3 seq";
        AlloyModuleReader reader = new AlloyModuleReader(SourceParser.parse(source), false);
        JsonNode value = reader.read(1);
        String root = value.path("predicates").get(0).path("bodyId").asText();
        JsonNode spans = new SourceReferenceMapper(source, value, reader.origins()).map();
        boolean found = false;
        for (JsonNode span : spans) {
            if (span.path("nodeId").asText().equals(root) && span.path("role").asText().equals("expression")) {
                assertEquals("some A", source.substring(span.path("startUtf16").intValue(), span.path("endUtf16").intValue()));
                found = true;
            }
        }
        assertTrue(found);
    }

    /** Ensures invalid candidates produce a typed denial. */
    @Test
    void invalidEngineCandidateIsDenied() {
        assertThrows(DocumentValidationException.class, new UnavailableAction()::run);
    }

    /** Provides a named callback for an invalid engine candidate. */
    private static final class UnavailableAction {
        /**
         * Calls the adapter with an invalid candidate.
         * @throws DocumentValidationException if candidate validation rejects
         */
        private void run() throws DocumentValidationException {
            new DocumentEngine().validate(MAPPER.createObjectNode(), MAPPER.createObjectNode(),
                MAPPER.createObjectNode(), "test-policy");
        }
    }

    /** Wraps a parser invocation in a named test callback. */
    private static final class ParserAction {
        private final String source;

        /**
         * Retains the source to parse.
         * @param source generated Alloy
         */
        private ParserAction(String source) {
            this.source = source;
        }

        /**
         * Parses the source using the pinned parser.
         * @throws Exception if Alloy rejects the source
         */
        private void run() throws Exception {
            CompUtil.parseEverything_fromString(A4Reporter.NOP, source);
        }
    }

}
