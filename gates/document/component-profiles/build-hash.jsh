// Read-only timing of the existing exact build hash; no production mutations.
import java.nio.file.Path;
var operation = Class.forName("dev.allow.backend.BuildIdentity").getDeclaredMethod("read", Path.class);
operation.setAccessible(true);
for (int i = 0; i < 15; i++) { long start = System.nanoTime(); operation.invoke(null, Path.of("backend/target")); long end = System.nanoTime(); if (i >= 5) System.out.println("HASH_MS=" + (end-start)/1000000.0); }
/exit
