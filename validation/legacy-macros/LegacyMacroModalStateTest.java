/** Standalone pure Java regression; no AWT, Fiji, JNI, models or display. */
public final class LegacyMacroModalStateTest {
    static StackTraceElement frame(String type, String method) { return new StackTraceElement(type,method,"test",1); }
    static void check(boolean condition) { if (!condition) throw new AssertionError("Modal readiness predicate regressed"); }
    public static void main(String[] args) {
        StackTraceElement dialog = frame("java.awt.Dialog","show"), wait = frame("java.awt.WaitDispatchSupport","enter");
        int checks = 0;
        for (Thread.State state : Thread.State.values()) {
            check(LegacyMacroModalState.ready(state,new StackTraceElement[]{dialog,wait})
                    == (state==Thread.State.WAITING || state==Thread.State.TIMED_WAITING)); checks++;
            check(!LegacyMacroModalState.ready(state,new StackTraceElement[]{dialog})); checks++;
            check(!LegacyMacroModalState.ready(state,new StackTraceElement[]{wait})); checks++;
            check(!LegacyMacroModalState.ready(state,new StackTraceElement[]{})); checks++;
        }
        check(!LegacyMacroModalState.ready(Thread.State.WAITING,new StackTraceElement[]{frame("other.Dialog","show"),wait}));checks++;
        check(!LegacyMacroModalState.ready(Thread.State.WAITING,new StackTraceElement[]{dialog,frame("java.awt.WaitDispatchSupport","other")}));checks++;
        System.out.println("PASS_MODAL_READINESS " + checks + " checks");
    }
}
