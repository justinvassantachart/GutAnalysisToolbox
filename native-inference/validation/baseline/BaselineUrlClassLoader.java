import java.io.File;
import java.net.URL;
import java.net.URLClassLoader;

/** Validation-only Java 9+ system loader matching the URL-based assumption of Fiji's old TF plugin. */
public final class BaselineUrlClassLoader extends URLClassLoader {
    public BaselineUrlClassLoader(ClassLoader ignoredDefaultApplicationLoader) throws Exception {
        // The platform parent keeps all GAT/ImageJ/dependency classes in this URL
        // loader instead of delegating them back to the Java 9+ AppClassLoader.
        super(classpathURLs(), ClassLoader.getPlatformClassLoader());
    }
    private static URL[] classpathURLs() throws Exception {
        String[] paths = System.getProperty("java.class.path").split(File.pathSeparator);
        URL[] urls = new URL[paths.length];
        for (int i = 0; i < paths.length; i++) urls[i] = new File(paths[i]).toURI().toURL();
        return urls;
    }
}
