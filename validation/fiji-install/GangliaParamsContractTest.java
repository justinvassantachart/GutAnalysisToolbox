import Features.Core.Params;
/** Compiled against the repository's real Params.java, never a substitute test class. */
public final class GangliaParamsContractTest {
    public static void main(String[] ignored) throws Exception {
        Params params = new Params();
        for (String name : new String[]{"gangliaProbThresh01", "gangliaMinAreaUm2"}) {
            java.lang.reflect.Field field = Params.class.getField(name);
            if (field.getType() != Double.class) throw new AssertionError("Unexpected contract: " + name);
            try {
                field.setDouble(params, 0.6);
                throw new AssertionError("Historical primitive setter unexpectedly accepted boxed " + name);
            } catch (IllegalArgumentException expected) { /* Reproduces the original harness defect. */ }
        }
        if (Params.class.getField("gangliaOpenIterations").getType() != int.class
                || Params.class.getField("gangliaInteractiveReview").getType() != boolean.class)
            throw new AssertionError("Unexpected primitive field contract");
        Fresh_Ganglia_Params.configure(params);
        if (!Double.valueOf(0.6).equals(params.gangliaProbThresh01)
                || !Double.valueOf(1.0).equals(params.gangliaMinAreaUm2)
                || params.gangliaOpenIterations != 1 || params.gangliaInteractiveReview)
            throw new AssertionError("Probe configuration did not reach actual Params");
        if (!"7a7bf454c5f3cb1b9d9a20f81417f98d976fe3b3dd52c1b9968f02e89e7e8a2f".equals(Fresh_Ganglia_Evidence.sha256(new byte[]{0, -1, 0, -1})))
            throw new AssertionError("Unsigned-byte mask hash convention changed");
        System.out.println("PASS actual Params boxed Double and primitive int/boolean setup");
    }
}
