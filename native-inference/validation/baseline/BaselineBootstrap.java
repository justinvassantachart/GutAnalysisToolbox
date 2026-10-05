import java.lang.reflect.InvocationTargetException;
import java.net.URLClassLoader;
import java.util.Arrays;

/** No ij.* references: apply official patcher hooks before resolving the real probe. */
public final class BaselineBootstrap {
    public static void main(String[] args) throws Throwable {
        if (args.length < 2) throw new IllegalArgumentException("probe-main-class [probe arguments]");
        ClassLoader loader = ClassLoader.getSystemClassLoader();
        System.out.println("BOOTSTRAP system=" + loader.getClass().getName() + "; parent=" + loader.getParent());
        if (!(loader instanceof URLClassLoader)) throw new IllegalStateException("Expected explicit URL system loader");
        Thread.currentThread().setContextClassLoader(loader);
        // Component JNI checks intentionally avoid ImageJ initialization altogether.
        if (args[0].equals("BaselineNativeProbe") || args[0].equals("LegacyPluginProbe")) {
            Class<?> patcher = Class.forName("net.imagej.patcher.LegacyInjector", true, loader);
            patcher.getMethod("preinit", ClassLoader.class).invoke(null, loader);
        }
        try {
            Class.forName(args[0], true, loader).getMethod("main", String[].class)
                    .invoke(null, (Object) Arrays.copyOfRange(args, 1, args.length));
        } catch (InvocationTargetException error) { throw error.getCause(); }
    }
}
