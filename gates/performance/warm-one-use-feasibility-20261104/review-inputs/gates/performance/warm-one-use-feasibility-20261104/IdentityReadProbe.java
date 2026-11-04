import java.lang.reflect.Method;
import java.nio.file.Path;

/** Reads the installed logical identity only; no Alloy engine or worker request executes. */
final class IdentityReadProbe {
    /** Prevents construction of the gate-only identity reader. */
    private IdentityReadProbe() { }

    /** Reads the existing package-private production identity implementation.
     * @param arguments one trusted target directory
     * @throws Exception unavailable identity implementation or incomplete target
     */
    public static void main(String[] arguments) throws Exception {
        Class<?> type = Class.forName("dev.allow.backend.BuildIdentity");
        Method method = type.getDeclaredMethod("read", Path.class);
        method.setAccessible(true);
        System.out.println(method.invoke(null, Path.of(arguments[0])));
        System.out.println(System.getProperty("java.runtime.version"));
    }
}
