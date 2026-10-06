import java.awt.GraphicsEnvironment;
import java.awt.Window;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;
import javax.swing.JDialog;
import javax.swing.JOptionPane;
import javax.swing.SwingUtilities;
import javax.swing.Timer;

/** Synthetic observer controls, never evidence that a GAT workflow was invoked. */
public final class CsbdeepTensorFlowDialogObserverTest {
    private static final CsbdeepTensorFlowDialogObserver.Scope ACTUAL =
            new CsbdeepTensorFlowDialogObserver.Scope("stardist", true,
                    CsbdeepTensorFlowDialogObserver.CALL_STAGE);

    private static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }

    private static boolean match(CsbdeepTensorFlowDialogObserver.Scope scope,
            boolean dialogShowing, boolean paneShowing, String title, Object text, int type) {
        return CsbdeepTensorFlowDialogObserver.matches(scope, dialogShowing, paneShowing, true, title, text, type);
    }

    private static void matcherControls() {
        String title = CsbdeepTensorFlowDialogObserver.TITLE;
        String text = CsbdeepTensorFlowDialogObserver.MESSAGE;
        int error = JOptionPane.ERROR_MESSAGE;
        require(match(ACTUAL, true, true, title, text, error), "Exact visible actual-call dialog must match");
        for (CsbdeepTensorFlowDialogObserver.Scope scope : new CsbdeepTensorFlowDialogObserver.Scope[]{
                null, new CsbdeepTensorFlowDialogObserver.Scope("alignment", true, ACTUAL.stage),
                new CsbdeepTensorFlowDialogObserver.Scope("stardist", false, ACTUAL.stage),
                new CsbdeepTensorFlowDialogObserver.Scope("stardist", true, "initializing_real_plugins"),
                new CsbdeepTensorFlowDialogObserver.Scope("stardist", true, "process_timeout"),
                new CsbdeepTensorFlowDialogObserver.Scope("stardist", true, null)}) {
            require(!match(scope, true, true, title, text, error), "Non-actual-StarDist scope must not match");
        }
        require(!match(ACTUAL, false, true, title, text, error), "Hidden dialog must not match");
        require(!match(ACTUAL, true, false, title, text, error), "Hidden pane must not match");
        require(!CsbdeepTensorFlowDialogObserver.matches(ACTUAL, true, true, false, title, text, error),
                "Nonmodal lookalike must not match");
        for (String nearTitle : new String[]{null, "Error", "Loading TensorFlow failed ", "Loading Tensorflow failed"})
            require(!match(ACTUAL, true, true, nearTitle, text, error), "Near title must not match");
        for (Object nearText : new Object[]{null, "Could not load TensorFlow.", text + " ",
                text.replace("<br/>", "<br>"), new Object[]{text}, new StringBuilder(text)})
            require(!match(ACTUAL, true, true, title, nearText, error), "Near message must not match");
        for (int type : new int[]{JOptionPane.WARNING_MESSAGE, JOptionPane.INFORMATION_MESSAGE,
                JOptionPane.QUESTION_MESSAGE, JOptionPane.PLAIN_MESSAGE})
            require(!match(ACTUAL, true, true, title, text, type), "Non-error message type must not match");
        System.out.println("PASS exact match and 23 negative matcher controls");
    }

    private static void verifyEvidence(Map<String, Object> evidence) {
        require(CsbdeepTensorFlowDialogObserver.TITLE.equals(evidence.get("title")), "Missing exact title");
        require(CsbdeepTensorFlowDialogObserver.MESSAGE.equals(evidence.get("message")), "Missing full raw HTML message");
        require(Integer.valueOf(JOptionPane.ERROR_MESSAGE).equals(evidence.get("message_type")), "Missing message type");
        require(ACTUAL.stage.equals(evidence.get("stage_at_observation")), "Missing stage");
        require(Boolean.TRUE.equals(evidence.get("dialog_showing")), "Dialog not visible");
        require(Boolean.TRUE.equals(evidence.get("option_pane_showing")), "Pane not visible");
        require(Boolean.TRUE.equals(evidence.get("modal")), "Expected actual modal showMessageDialog");
        require("JOptionPane.UNINITIALIZED_VALUE".equals(evidence.get("selected_value")), "Dialog was answered");
        require(evidence.get("dialog_components") != null, "Missing full component evidence");
        require(SwingUtilities.isEventDispatchThread(), "Swing inspection must run on EDT");
        boolean stillShowing = false;
        for (Window window : Window.getWindows()) {
            if (window instanceof JDialog && window.isShowing()
                    && CsbdeepTensorFlowDialogObserver.TITLE.equals(((JDialog) window).getTitle())) stillShowing = true;
        }
        require(stillShowing, "Observer dismissed the dialog");
    }

    private static void guiControl(String mode) throws Exception {
        require(!GraphicsEnvironment.isHeadless(), "GUI control requires a display");
        AtomicReference<CsbdeepTensorFlowDialogObserver.Scope> scope = new AtomicReference<>(ACTUAL);
        if (mode.equals("precall")) scope.set(new CsbdeepTensorFlowDialogObserver.Scope("stardist", false, ACTUAL.stage));
        if (mode.equals("alignment")) scope.set(new CsbdeepTensorFlowDialogObserver.Scope("alignment", true, ACTUAL.stage));
        if (mode.equals("setup")) scope.set(new CsbdeepTensorFlowDialogObserver.Scope("stardist", true, "initializing_real_plugins"));
        JDialog[] existing = new JDialog[1];
        if (mode.startsWith("preexisting")) SwingUtilities.invokeAndWait(() -> {
            JOptionPane pane = new JOptionPane(CsbdeepTensorFlowDialogObserver.MESSAGE, JOptionPane.ERROR_MESSAGE);
            existing[0] = pane.createDialog(CsbdeepTensorFlowDialogObserver.TITLE);
        });
        if (mode.equals("preexisting-visible")) SwingUtilities.invokeLater(() -> existing[0].setVisible(true));
        CsbdeepTensorFlowDialogObserver.start(scope::get, evidence -> {
            try {
                require(mode.equals("exact"), "Negative GUI control was misclassified: " + mode);
                verifyEvidence(evidence);
                System.out.println("PASS synthetic visible exact-dialog observer; no option selected or dialog dismissed");
                // Like the production callback, terminate only this isolated control JVM.
                System.out.flush();
                Runtime.getRuntime().halt(2);
            } catch (Throwable error) {
                error.printStackTrace();
                System.exit(10);
            }
        });
        SwingUtilities.invokeLater(() -> {
            Timer deadline = new Timer(mode.equals("exact") ? 3000 : 500, event -> {
                if (mode.equals("exact")) {
                    System.err.println("Exact visible dialog was not observed");
                    System.exit(11);
                }
                System.out.println("PASS unclassified GUI control: " + mode);
                System.exit(0);
            });
            deadline.setRepeats(false);
            deadline.start();
            if (existing[0] != null) {
                if (mode.equals("preexisting-hidden")) existing[0].setVisible(true);
                return;
            }
            String title = mode.equals("wrong-title") ? "Different failure" : CsbdeepTensorFlowDialogObserver.TITLE;
            String message = mode.equals("wrong-message") ? "Could not load TensorFlow." : CsbdeepTensorFlowDialogObserver.MESSAGE;
            int type = mode.equals("warning") ? JOptionPane.WARNING_MESSAGE : JOptionPane.ERROR_MESSAGE;
            if (mode.equals("nonmodal")) {
                JDialog dialog = new JOptionPane(message, type).createDialog(title);
                dialog.setModal(false);
                dialog.setVisible(true);
                return;
            }
            JOptionPane.showMessageDialog(null, message, title, type);
            System.err.println("Dialog returned; a Library Management action would now be reached");
            System.exit(12);
        });
    }

    public static void main(String[] args) throws Exception {
        if (args[0].equals("headless")) System.out.println(GraphicsEnvironment.isHeadless());
        else if (args[0].equals("matchers")) matcherControls();
        else guiControl(args[0]);
    }
}
