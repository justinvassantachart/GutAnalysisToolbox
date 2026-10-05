import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.*;

/** Validation-only structured evidence writer. No scientific result is inferred from class presence. */
public final class WorkflowReport {
    public interface CheckedAction { Map<String,Object> run() throws Exception; }
    private final String suite; private final Path directory; private final String filename;
    private final List<Map<String,Object>> checks = new ArrayList<>();
    public WorkflowReport(String suite, Path directory, String filename) throws Exception {
        this.suite=suite;this.directory=directory;this.filename=filename;Files.createDirectories(directory);
    }
    public void test(String id,String scope,String algorithm,CheckedAction action) {
        long start=System.nanoTime();Map<String,Object> row=values("id",id,"scope",scope,"algorithm",algorithm);
        try { Map<String,Object> metrics=action.run(); row.put("status","PASS");row.put("metrics",metrics); }
        catch(Throwable failure) { row.put("status","FAIL"); row.put("error",failure.toString());
            List<String> trace=new ArrayList<>();for(StackTraceElement e:failure.getStackTrace())trace.add(e.toString());row.put("trace",trace);failure.printStackTrace(System.err); }
        row.put("elapsed_seconds",(System.nanoTime()-start)/1e9);checks.add(row);
        System.out.println(id+": "+row.get("status"));
    }
    public void blocked(String id,String scope,String reason) { checks.add(values("id",id,"scope",scope,"status","BLOCKED","reason",reason)); }
    public void notRun(String id,String scope,String reason) { checks.add(values("id",id,"scope",scope,"status","NOT_RUN","reason",reason)); }
    public int failures() { int count=0;for(Map<String,Object> c:checks)if("FAIL".equals(c.get("status")))count++;return count; }
    public void write() throws Exception {
        Map<String,Object> result=values("schema_version",1,"suite",suite,"generated_at_utc",Instant.now().toString(),
                "os_name",System.getProperty("os.name"),"os_version",System.getProperty("os.version"),"os_arch",System.getProperty("os.arch"),
                "java_version",System.getProperty("java.version"),"java_vendor",System.getProperty("java.vendor"),"java_home",System.getProperty("java.home"),
                "available_processors",Runtime.getRuntime().availableProcessors(),"checks",checks,"unexpected_failures",failures(),
                "interpretation","Synthetic/public-input component or command tests as individually labeled; not full GAT GUI, biological accuracy, or a benchmark of the user's M1");
        Files.write(directory.resolve(filename),(json(result)+"\n").getBytes(StandardCharsets.UTF_8));
    }
    public static void check(boolean ok,String message) { if(!ok)throw new AssertionError(message); }
    public static Map<String,Object> values(Object... pairs) { Map<String,Object> result=new LinkedHashMap<>();for(int i=0;i<pairs.length;i+=2)result.put(String.valueOf(pairs[i]),pairs[i+1]);return result; }
    public static String json(Object x) {
        if(x==null)return "null";if(x instanceof Boolean)return x.toString();
        if(x instanceof Number){double n=((Number)x).doubleValue();return Double.isFinite(n)?x.toString():quote(x.toString());}
        if(x instanceof Map){List<String> a=new ArrayList<>();for(Object e0:((Map<?,?>)x).entrySet()){Map.Entry<?,?>e=(Map.Entry<?,?>)e0;a.add(quote(String.valueOf(e.getKey()))+":"+json(e.getValue()));}return "{"+String.join(",",a)+"}";}
        if(x instanceof Iterable){List<String>a=new ArrayList<>();for(Object e:(Iterable<?>)x)a.add(json(e));return "["+String.join(",",a)+"]";}
        if(x.getClass().isArray()){List<String>a=new ArrayList<>();for(int i=0;i<java.lang.reflect.Array.getLength(x);i++)a.add(json(java.lang.reflect.Array.get(x,i)));return "["+String.join(",",a)+"]";}
        return quote(x.toString());
    }
    private static String quote(String s){StringBuilder b=new StringBuilder("\"");for(char c:s.toCharArray()){switch(c){case '\\':b.append("\\\\");break;case '"':b.append("\\\"");break;case '\n':b.append("\\n");break;case '\r':b.append("\\r");break;case '\t':b.append("\\t");break;default:if(c<32)b.append(String.format("\\u%04x",(int)c));else b.append(c);}}return b.append('"').toString();}
}
