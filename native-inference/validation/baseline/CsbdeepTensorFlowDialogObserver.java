import java.awt.Component;
import java.awt.Container;
import java.awt.Window;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Consumer;
import java.util.function.Supplier;
import javax.swing.AbstractButton;
import javax.swing.JDialog;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.SwingUtilities;
import javax.swing.Timer;

/** Passive validation-only observer. Never dismisses a dialog or invokes its actions. */
final class CsbdeepTensorFlowDialogObserver implements AutoCloseable {
    static final String TITLE = "Loading TensorFlow failed";
    static final String MESSAGE = "<html>Could not load TensorFlow.<br/>Opening the TensorFlow Library Management tool.</html>";
    static final String CALL_STAGE = "calling_actual_GAT_StarDist";

    static final class Scope {
        final String probe;
        final boolean invoked;
        final String stage;

        Scope(String probe, boolean invoked, String stage) {
            this.probe = probe;
            this.invoked = invoked;
            this.stage = stage;
        }
    }

    private final Supplier<Scope> scope;
    private final Consumer<Map<String, Object>> onFailure;
    private final Set<Window> preexisting = Collections.newSetFromMap(new IdentityHashMap<>());
    private final Timer timer;
    private boolean observed;

    private CsbdeepTensorFlowDialogObserver(Supplier<Scope> scope,
            Consumer<Map<String, Object>> onFailure) {
        this.scope = scope;
        this.onFailure = onFailure;
        // Even an exact dialog from initialization is not actual-call evidence.
        Collections.addAll(preexisting, Window.getWindows());
        timer = new Timer(100, event -> scan());
        timer.start();
    }

    static CsbdeepTensorFlowDialogObserver start(Supplier<Scope> scope,
            Consumer<Map<String, Object>> onFailure) throws Exception {
        CsbdeepTensorFlowDialogObserver[] observer = new CsbdeepTensorFlowDialogObserver[1];
        Runnable start = () -> observer[0] = new CsbdeepTensorFlowDialogObserver(scope, onFailure);
        if (SwingUtilities.isEventDispatchThread()) start.run();
        else SwingUtilities.invokeAndWait(start);
        return observer[0];
    }

    static boolean matches(Scope scope, boolean dialogShowing, boolean paneShowing, boolean modal,
            String title, Object message, int messageType) {
        return scope != null && "stardist".equals(scope.probe) && scope.invoked
                && CALL_STAGE.equals(scope.stage) && dialogShowing && paneShowing && modal
                && TITLE.equals(title) && MESSAGE.equals(message)
                && messageType == JOptionPane.ERROR_MESSAGE;
    }

    private void scan() {
        if (observed) return;
        Scope current = scope.get();
        if (current == null || !"stardist".equals(current.probe) || !current.invoked
                || !CALL_STAGE.equals(current.stage)) return;
        for (Window window : Window.getWindows()) {
            if (!(window instanceof JDialog) || preexisting.contains(window) || !window.isShowing()) continue;
            JDialog dialog = (JDialog) window;
            JOptionPane pane = matchingPane(dialog.getContentPane(), dialog, current);
            if (pane == null) continue;
            observed = true;
            timer.stop();
            Map<String, Object> evidence = new LinkedHashMap<>();
            evidence.put("signature", "CSBDeep TensorFlowNetwork.loadLibrary error dialog");
            evidence.put("observed_at_utc", Instant.now().toString());
            evidence.put("probe", current.probe);
            evidence.put("actual_gat_method_invoked", current.invoked);
            evidence.put("stage_at_observation", current.stage);
            evidence.put("title", dialog.getTitle());
            evidence.put("message", pane.getMessage());
            evidence.put("message_type", pane.getMessageType());
            evidence.put("message_type_name", "ERROR_MESSAGE");
            evidence.put("dialog_class", dialog.getClass().getName());
            evidence.put("option_pane_class", pane.getClass().getName());
            evidence.put("dialog_showing", dialog.isShowing());
            evidence.put("option_pane_showing", pane.isShowing());
            evidence.put("modal", dialog.isModal());
            evidence.put("modality_type", dialog.getModalityType().name());
            evidence.put("option_type", pane.getOptionType());
            evidence.put("selected_value", value(pane.getValue()));
            evidence.put("initial_value", value(pane.getInitialValue()));
            evidence.put("preexisting_window", false);
            evidence.put("observer_thread", Thread.currentThread().getName());
            evidence.put("dialog_components", components(dialog.getContentPane()));
            evidence.put("action", "record_only_then_exit_isolated_probe_without_dismissing_dialog");
            onFailure.accept(evidence);
            return;
        }
    }

    private static JOptionPane matchingPane(Component component, JDialog dialog, Scope scope) {
        if (component instanceof JOptionPane) {
            JOptionPane pane = (JOptionPane) component;
            if (matches(scope, dialog.isShowing(), pane.isShowing(), dialog.isModal(), dialog.getTitle(),
                    pane.getMessage(), pane.getMessageType())) return pane;
        }
        if (component instanceof Container) {
            for (Component child : ((Container) component).getComponents()) {
                JOptionPane pane = matchingPane(child, dialog, scope);
                if (pane != null) return pane;
            }
        }
        return null;
    }

    private static Object value(Object value) {
        return value == null ? null : value == JOptionPane.UNINITIALIZED_VALUE
                ? "JOptionPane.UNINITIALIZED_VALUE" : String.valueOf(value);
    }

    private static List<Map<String, Object>> components(Container parent) {
        List<Map<String, Object>> result = new ArrayList<>();
        for (Component component : parent.getComponents()) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("class", component.getClass().getName());
            item.put("showing", component.isShowing());
            if (component instanceof JLabel) item.put("text", ((JLabel) component).getText());
            if (component instanceof AbstractButton) item.put("text", ((AbstractButton) component).getText());
            if (component instanceof Container) item.put("children", components((Container) component));
            result.add(item);
        }
        return result;
    }

    @Override
    public void close() throws Exception {
        if (SwingUtilities.isEventDispatchThread()) timer.stop();
        else SwingUtilities.invokeAndWait(timer::stop);
    }
}
