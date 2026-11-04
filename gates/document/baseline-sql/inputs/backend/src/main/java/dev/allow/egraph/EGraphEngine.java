package dev.allow.egraph;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
/** Context-confined complete bounded egraph mechanics with independently checked output.
     */
public final class EGraphEngine {
    private final RuleCatalog catalog;
    /** Loads the build-bound closed registry.
     */
    public EGraphEngine() { catalog = new RuleCatalog(); }
    /** Returns exact registry identity for result binding.
     * @return ruleset SHA-256
     */
    public String rulesetDigest() { return catalog.digest(); }
    /** Runs one anonymous root against a shared job deadline.
     * @param input trusted mapper output
     * @param deadlineNanos absolute monotonic deadline
     * @return bounded checked island result
     */
    public IslandResult analyze(EngineInput input, long deadlineNanos) {
        Run run = new Run(input, catalog, deadlineNanos);
        try { return run.execute(); }
        catch (RunBudget.Limit limit) { return run.finish(limit.getMessage()); }
        catch (RuntimeException error) { return run.unavailable("ERROR"); }
    }
    /** Per-invocation state never crosses roots.
     */
    private static final class Run {
        private final EngineInput input;
        private final RuleCatalog catalog;
        private final RunBudget budget;
        private final ProofChecker checker;
        private final ProofStore proofs;
        private final EGraph graph;
        private int root = -1;
        private long rounds;
        /** Creates private invocation state.
     * @param input typed root
     * @param catalog closed registry
     * @param deadline shared time bound
     */
        Run(EngineInput input, RuleCatalog catalog, long deadline) {
            this.input = input; this.catalog = catalog; budget = new RunBudget(deadline);
            checker = new ProofChecker(catalog); proofs = new ProofStore(checker, input.context()); graph = new EGraph(proofs, budget);
        }
        /** Validates, saturates and extracts.
     * @return checked bounded result
     * @throws RunBudget.Limit when the input exceeds the admitted finite term bound
     */
        IslandResult execute() {
            ProofChecker.validateContext(input.context());
            try { ProofChecker.term(input.root(), input.context(), 0); }
            catch (IllegalArgumentException error) {
                if ("Term limit".equals(error.getMessage())) throw new RunBudget.Limit("INPUT_LIMIT");
                throw error;
            }
            root = graph.add(input.root()); graph.rebuild();
            for (int iteration = 0; iteration < 12; iteration++) {
                rounds++; int before = graph.size(); long unions = budget.unions();
                List<Application> applications = search();
                for (Application application : applications) apply(application);
                graph.rebuild();
                if (before == graph.size() && unions == budget.unions()) return finish("SATURATED");
            }
            return finish("ITERATION_LIMIT");
        }
        /** Searches a rebuilt snapshot in stable registry/class order.
     * @return finite applicable matches
     */
        private List<Application> search() {
            List<Application> applications = new ArrayList<>(); Matcher matcher = new Matcher(graph, budget);
            int size = graph.size();
            for (RuleCatalog.Rewrite rule : catalog.rules()) for (int id = 0; id < size; id++) {
                if (graph.find(id) != id || !graph.node(id).sort().kind().equals(rule.family())) continue;
                for (Map<String, Integer> binding : matcher.match(rule.left(), id, Map.of())) {
                    Map<String, Term> terms = new LinkedHashMap<>();
                    for (Map.Entry<String, Integer> entry : binding.entrySet()) terms.put(entry.getKey(), graph.node(entry.getValue()));
                    applications.add(new Application(rule, graph.node(id).sort(), Map.copyOf(terms)));
                }
            }
            return applications;
        }
        /** Instantiates and checks a ground rule before union.
     * @param application frozen match
     */
        private void apply(Application application) {
            budget.tick(); RuleCatalog.Rewrite rule = application.rule();
            Term left = RuleCatalog.instantiate(rule.left(), application.bindings(), application.sort());
            Term right = RuleCatalog.instantiate(rule.right(), application.bindings(), application.sort());
            int a = graph.add(left), b = graph.add(right);
            if (graph.find(a) == graph.find(b)) return;
            int proof = proofs.append("RULE", left, right, List.of(), rule.id(), application.bindings());
            graph.merge(a, b, proof);
        }
        /** Produces finite checked extraction, including an original-root fallback after limits.
     * @param reason honest termination
     * @return result
     */
        IslandResult finish(String reason) {
            if (root < 0) return unavailable(reason);
            try {
                Term extracted = reason.equals("TIME_LIMIT") ? input.root() : Extractor.extract(graph, root, budget);
                int target = graph.add(extracted); int conclusion = graph.equality(root, target);
                Certificate certificate = certificate(extracted, conclusion);
                if (!checker.check(certificate, input)) return unavailable(reason);
                return checked(reason, extracted, certificate);
            } catch (RunBudget.Limit limit) { return original(limit.getMessage()); }
            catch (RuntimeException error) { return unavailable("ERROR"); }
        }
        /** Falls back to a fresh reflexivity certificate without relying on partial graph state.
     * @param reason termination
     * @return checked original or unavailable
     */
        private IslandResult original(String reason) {
            try {
                ProofStep refl = new ProofStep("REFL", input.root(), input.root(), List.of(), "", Map.of());
                Certificate certificate = new Certificate("allow-egraph-proof-v1", input.context(), catalog.digest(),
                        input.root(), input.root(), List.of(refl), 0);
                return checker.check(certificate, input) ? checked(reason, input.root(), certificate) : unavailable(reason);
            } catch (RuntimeException error) { return unavailable(reason); }
        }
        /** Binds an exact root proof.
     * @param extracted target root
     * @param conclusion proof index
     * @return certificate
     */
        private Certificate certificate(Term extracted, int conclusion) {
            return CertificateSlice.compact(new Certificate("allow-egraph-proof-v1", input.context(), catalog.digest(),
                    input.root(), extracted, proofs.steps(), conclusion));
        }
        /** Creates a replay-accepted result.
     * @param reason termination
     * @param extracted finite root
     * @param certificate accepted artifact
     * @return island result
     */
        private IslandResult checked(String reason, Term extracted, Certificate certificate) {
            return new IslandResult(input.context().rootPath(), "CHECKED", reason, input.root(), extracted,
                    input.root().cost(), extracted.cost(), stats(), preview(),
                    Map.of("steps", certificate.steps().size(), "bytes", Wire.size(certificate)), certificate);
        }
        /** Creates a fixed unavailable response without unproved terms.
     * @param reason closed reason
     * @return unavailable island
     */
        IslandResult unavailable(String reason) {
            return new IslandResult(input.context().rootPath(), "UNAVAILABLE", reason, null, null, null, null,
                    stats(), Map.of("classes", List.of(), "truncated", false), Map.of(), null);
        }
        /** Summarizes finite engine work.
     * @return immutable counters
     */
        private Map<String, Long> stats() {
            long classes = 0; for (int i = 0; i < graph.size(); i++) if (graph.find(i) == i) classes++;
            return Map.of("nodes", (long) graph.size(), "classes", classes, "unions", budget.unions(),
                    "matches", budget.matches(), "rounds", rounds, "rebuilds", graph.rebuilds());
        }
        /** Produces bounded textual graph inspection.
     * @return class preview and truncation
     */
        private Map<String, Object> preview() {
            List<Map<String, Object>> classes = new ArrayList<>();
            List<Integer> shown = new ArrayList<>();
            int count = 0;
            for (int i = 0; i < graph.size() && classes.size() < 24 && count < 48; i++) {
                if (graph.find(i) != i) continue;
                List<Term> terms = new ArrayList<>();
                for (int member : graph.members(i)) {
                    if (count >= 48) break;
                    terms.add(graph.node(member));
                    shown.add(member);
                    count++;
                }
                classes.add(Map.of("id", i, "nodes", List.copyOf(terms)));
            }
            List<Map<String, Integer>> edges = previewEdges(classes, shown);
            return Map.of("classes", List.copyOf(classes), "edges", edges, "truncated", count < graph.size());
        }
        /** Extracts ordered links whose endpoint cards are visible.
         * @param classes bounded visible classes
         * @param shown concrete displayed enodes
         * @return deduplicated directed operand links
         */
        private List<Map<String, Integer>> previewEdges(List<Map<String, Object>> classes, List<Integer> shown) {
            List<Map<String, Integer>> result = new ArrayList<>();
            List<Integer> visible = new ArrayList<>();
            for (Map<String, Object> value : classes) visible.add((Integer) value.get("id"));
            for (int node : shown) {
                int position = 0;
                for (int child : graph.children(node)) {
                    int target = graph.find(child);
                    if (visible.contains(target)) {
                        Map<String, Integer> edge = Map.of("from", graph.find(node), "to", target, "position", position);
                        if (!result.contains(edge)) result.add(edge);
                    }
                    position++;
                }
            }
            return List.copyOf(result);
        }

    }
    /** Frozen ground match.
     * @param rule admitted schema
     * @param sort exact family instance
     * @param bindings concrete values
     */
    private record Application(RuleCatalog.Rewrite rule, Sort sort, Map<String, Term> bindings) { }
}
