/** Pure readiness predicate for test observers; never substitutes plugin errors. */
public final class LegacyMacroModalState {
    private LegacyMacroModalState() { }
    public static boolean ready(Thread.State state, StackTraceElement[] trace) {
        if (state != Thread.State.WAITING && state != Thread.State.TIMED_WAITING) return false;
        boolean dialog = false, modalWait = false;
        for (StackTraceElement frame : trace) {
            dialog |= frame.getClassName().equals("java.awt.Dialog") && frame.getMethodName().equals("show");
            modalWait |= frame.getClassName().equals("java.awt.WaitDispatchSupport") && frame.getMethodName().equals("enter");
        }
        return dialog && modalWait;
    }
}
