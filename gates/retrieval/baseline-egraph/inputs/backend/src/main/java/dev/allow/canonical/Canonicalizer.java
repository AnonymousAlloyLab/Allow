package dev.allow.canonical;

import edu.mit.csail.sdg.ast.Command;
import edu.mit.csail.sdg.parser.CompModule;
import java.util.List;

/** Entry point for the supported structural profile, separate from source presentation. */
public final class Canonicalizer {
    /** Creates a stateless canonicalization facade; module state is per invocation. */
    public Canonicalizer() { }

    /** Maps resolved AST identity to anonymous code and local retrieval features.
     * @param module fully parsed and type-checked module
     * @param command selected run/check command
     * @return anonymous result, or empty UNSUPPORTED_CANONICAL without a raw-source fallback
     */
    public CanonicalView analyze(CompModule module, Command command) {
        try {
            ModuleEncoder encoder = new ModuleEncoder(module);
            AnonymizedArtifact artifact = AnonymizedArtifact.fromStructure(encoder.encode(command));
            EgraphView graph = graph(encoder, artifact);
            return new CanonicalView("AVAILABLE", artifact.payload(), CanonicalDigest.hex(artifact),
                    new EmbeddingEncoder().encode(artifact), graph);
        } catch (UnsupportedCanonical unsupported) {
            return new CanonicalView("UNSUPPORTED_CANONICAL", "", "", List.of());
        }
    }
    /** Keeps optimization failures separate from the structural profile.
     * @param encoder completed single module traversal
     * @param artifact anonymous module
     * @return optional bounded graph result
     */
    private EgraphView graph(ModuleEncoder encoder, AnonymizedArtifact artifact) {
        try { return new IslandAdapter(encoder.slots()).analyze(artifact.payload(), encoder.islands()); }
        catch (RuntimeException failure) { return null; }
    }

}
