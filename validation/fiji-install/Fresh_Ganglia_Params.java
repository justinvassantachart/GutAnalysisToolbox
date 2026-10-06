/** Reflection setup shared by the installed-Fiji probe and its actual-Params contract test. */
public final class Fresh_Ganglia_Params {
    private Fresh_Ganglia_Params() {}
    public static void configure(Object params) throws ReflectiveOperationException {
        Class<?> type = params.getClass();
        type.getField("gangliaInteractiveReview").setBoolean(params, false);
        // Params deliberately uses nullable boxed Double fields. Field.setDouble
        // accepts a primitive double field, but cannot assign a java.lang.Double.
        type.getField("gangliaProbThresh01").set(params, Double.valueOf(0.6));
        type.getField("gangliaOpenIterations").setInt(params, 1);
        type.getField("gangliaMinAreaUm2").set(params, Double.valueOf(1.0));
    }
}
