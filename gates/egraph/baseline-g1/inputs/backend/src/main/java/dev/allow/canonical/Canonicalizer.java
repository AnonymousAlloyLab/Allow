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
            AnonymizedArtifact artifact = AnonymizedArtifact.fromStructure(new ModuleEncoder(module).encode(command));
            return new CanonicalView("AVAILABLE", artifact.payload(), CanonicalDigest.hex(artifact),
                    new EmbeddingEncoder().encode(artifact));
        } catch (UnsupportedCanonical unsupported) {
            return new CanonicalView("UNSUPPORTED_CANONICAL", "", "", List.of());
        }
    }
}
