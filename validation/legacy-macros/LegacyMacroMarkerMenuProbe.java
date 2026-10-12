import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import ij.IJ;
import ij.ImagePlus;
import ij.Menus;
import ij.WindowManager;
import ij.gui.Roi;
import ij.gui.GenericDialog;
import ij.io.RoiDecoder;
import ij.plugin.PlugIn;
import ij.plugin.frame.RoiManager;
import ij.process.FloatPolygon;
import java.awt.*;
import java.awt.event.*;
import java.lang.reflect.Field;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;
import java.util.zip.*;
import javax.swing.*;
import org.scijava.Context;
import org.scijava.event.EventHandler;
import org.scijava.event.EventService;
import org.scijava.module.event.ModuleExecutedEvent;

/** Runs the real installed menu and unchanged script body with actual dialogs.
 * This is a validation-only IJ1 plugin, never a replacement production workflow.
 */
public final class LegacyMacroMarkerMenuProbe implements PlugIn {
    private static final Gson JSON = new GsonBuilder().serializeNulls().setPrettyPrinting().create();
    private final Map<String,Object> report = new LinkedHashMap<>();
    private final List<Object> events = new ArrayList<>();
    private final List<String> errors = Collections.synchronizedList(new ArrayList<>());
    private final Map<Long,String> workers = Collections.synchronizedMap(new LinkedHashMap<>());
    private final Set<Window> handled = Collections.newSetFromMap(new IdentityHashMap<Window,Boolean>());
    private final Map<Window,Long> unknown = new IdentityHashMap<>();
    private final Map<Window,Long> dashboardSeen = new IdentityHashMap<>();
    private final List<Object> scriptEvents = Collections.synchronizedList(new ArrayList<>());
    private final AtomicReference<Throwable> failure = new AtomicReference<>();
    private Map<String,Object> config;
    private Path output, input;
    private boolean nativeVariant, hasHu;
    private String menu;
    private final Map<String,Object> reviews = new LinkedHashMap<>();
    private volatile boolean dashboard, review, complete;
    private String target, scenario;
    private Observer observer;
    private volatile boolean watching;

    /** IJ1 run(command, options) does not forward options to PlugIn.run(arg). */
    public static String launch(String config) {
        new LegacyMacroMarkerMenuProbe().run(config);
        return "controller-started";
    }

    @Override public void run(String arg) {
        // Return from the driver macro before dispatching the actual menu; no
        // nested macro parameters or Macro.setOptions can suppress its dialogs.
        Thread thread = new Thread(() -> execute(arg), "public-topmenu-controller");
        thread.setDaemon(false); thread.start();
    }

    public final class Observer {
        @EventHandler public void lifecycle(org.scijava.module.event.ModuleEvent event) {
            org.scijava.module.Module module=event.getModule();
            String title=module.getInfo().getTitle();
            if(title==null || !title.contains("Analyse Neuron")) return;
            Map<String,Object> entry=map("event",event.getClass().getSimpleName(),"title",title,
                "delegate",module.getDelegateObject().getClass().getName(),"detail",event.toString());
            Map<String,Object> values=new LinkedHashMap<>();
            for(String key:Arrays.asList("path","cell_channel","ganglia_channel","batch_parameters","image_already_open","Cell_counts_per_ganglia","Finetune_Detection_Parameters"))
                values.put(key,String.valueOf(module.getInput(key)));
            entry.put("inputs",values); scriptEvents.add(entry);
        }
        int count;
        final List<Object> calls = new ArrayList<>();
        @EventHandler public void executed(ModuleExecutedEvent event) {
            org.scijava.module.Module module = event.getModule();
            if (!module.getDelegateObject().getClass().getName().equals(target)) return;
            count++;
            Map<String,Object> args = new LinkedHashMap<>();
            for (String name : Arrays.asList("modelChoice", "modelFile", "normalizeInput", "percentileBottom", "percentileTop", "probThresh", "nmsThresh", "nTiles", "excludeBoundary", "outputType", "roiPosition", "verbose", "showCsbdeepProgress", "showProbAndDist"))
                args.put(name, String.valueOf(module.getInput(name)));
            calls.add(args);
        }
    }

    @SuppressWarnings("unchecked") private void execute(String arg) {
        int exit = 2;
        try {
            config = JSON.fromJson(Files.readString(Path.of(arg)), Map.class);
            output = Path.of((String)config.get("output")); input = Path.of((String)config.get("input"));
            nativeVariant = "native".equals(config.get("variant")); scenario = (String)config.get("scenario");
            hasHu = "hu-one-marker".equals(config.get("family"));
            require(hasHu || "no-hu-one-marker".equals(config.get("family")), "Unknown marker family");
            require("unchanged".equals(scenario), "Only unchanged marker review is prepared");
            target = nativeVariant ? "Features.Macros.LegacyMacroStarDist" : "de.csbdresden.stardist.StarDist2D";
            report.put("schema_version", 1); report.put("scope", "real-top-menu-marker-whole-workflow");
            report.put("family", config.get("family")); report.put("reviews", reviews);
            report.put("variant", config.get("variant")); report.put("scenario", scenario);
            report.put("status", "SETTING_UP"); report.put("dialogs", events); report.put("whole_analysis_macro_executed", false);
            report.put("source_script_sha256", hash(Path.of((String)config.get("source_script"))));
            report.put("fixture_sha256", hash(Path.of((String)config.get("fixture"))));
            report.put("os", System.getProperty("os.name")); report.put("arch", System.getProperty("os.arch"));
            checkpoint();
            require(report.get("fixture_sha256").equals(config.get("fixture_sha256")), "Fixture changed");
            require(!GraphicsEnvironment.isHeadless(), "Real AWT is required");
            Thread.sleep(1000); // driver macro has returned before real menu dispatch
            require(!ij.macro.Interpreter.isBatchMode(), "Cannot run the interactive gate in batch mode");
            ClassLoader loader = IJ.getClassLoader();
            require((loader.getResource("Features/Macros/LegacyMacroStarDist.class") != null) == nativeVariant, "Fork class isolation failed");
            require(loader.getResource("org/tensorflow/types/TFloat32.class") == null, "Modern TensorFlow leaked into host");
            if (nativeVariant) {
                Class<?> backend = loader.loadClass("Features.Inference.InferenceBackend");
                String property = (String)backend.getField("PROPERTY").get(null);
                require("gat.stardist.backend".equals(property) && "native".equals(System.getProperty(property))
                        && Boolean.TRUE.equals(backend.getMethod("useNativeWorker").invoke(null)), "Native branch not forced");
                report.put("backend_property", property); report.put("backend_value", System.getProperty(property));
            }
            String actualImageJDirectory=IJ.getDirectory("imagej");
            Path actualSettings=Path.of(actualImageJDirectory,"scripts",nativeVariant?"GAT MacroFork":"GAT","Tools","commands",nativeVariant?"gat_settings [MacroFork].ijm":"gat_settings.ijm");
            String settingsOption="open="+(nativeVariant?"["+actualSettings+"]":actualSettings.toString());
            report.put("settings_path_preflight",map("imagej_directory",actualImageJDirectory,"settings_path",actualSettings.toString(),
                "settings_exists",Files.isRegularFile(actualSettings),"parsed_open_path",ij.Macro.getValue(settingsOption,"open","MISSING")));
            require(Files.isRegularFile(actualSettings) && ij.Macro.getValue(settingsOption,"open","MISSING").equals(actualSettings.toString()),"Actual resolved settings path is unusable");
            report.put("target_class", provenance(loader.loadClass(target)));
            report.put("command_bridge_class", provenance(loader.loadClass("de.csbdresden.CommandFromMacro")));
            menu = hasHu ? " Analyse Neuron (Multi-channel)" : " Analyse Neuron (Multi-channel - No Hu)";
            String expected = menu + (nativeVariant ? " [MacroFork]" : "");
            List<String> candidates = new ArrayList<>();
            for (Object key : Menus.getCommands().keySet()) if (String.valueOf(key).contains("Analyse Neuron")) candidates.add(String.valueOf(key));
            report.put("discovered_marker_menus", candidates);
            require(Menus.getCommands().containsKey(expected), "Exact registered top menu absent: " + expected);
            report.put("invoked_menu", expected); report.put("menu_binding", String.valueOf(Menus.getCommands().get(expected)));
            require(Menus.getCommands().containsKey("Command From Macro"), "Command From Macro not registered");
            Context context = (Context)IJ.runPlugIn("org.scijava.Context", "");
            require(context != null, "Global Fiji context absent");
            observer = new Observer(); context.service(EventService.class).subscribe(observer);
            IJ.setExceptionHandler(error -> { errors.add(error.toString()); error.printStackTrace(); });
            prepareInput();
            report.put("parameters", map("cell_channel", hasHu ? "1" : "NA", "image_already_open", false,
                    "Enter_channel_details_now", true, "marker_names_manual", "Marker", "marker_no_manual", "2",
                    "Cell_counts_per_ganglia", false, "Ganglia_detection", "DeepImageJ", "ganglia_channel", "NA",
                    "Perform_Spatial_Analysis", false, "Finetune_Detection_Parameters", !hasHu, "Contribute_to_GAT", false));
            report.put("status", "RUNNING_REAL_TOP_MENU"); checkpoint();
            watching = true;
            Thread poller = new Thread(() -> {
                while(watching) {
                    ProcessHandle.current().descendants().forEach(child -> {
                        String cmd = child.info().commandLine().orElse("");
                        if (cmd.contains("org.gatanalysis.inference.NativeInferenceMain")) workers.put(child.pid(), cmd);
                    });
                    try { Thread.sleep(20); } catch (InterruptedException ignored) { return; }
                }
            }, "observe-native-worker"); poller.setDaemon(true); poller.start();
            // This is the only entry point into the workflow under test.
            IJ.doCommand(expected);
            long deadline = System.currentTimeMillis() + ((Number)config.get("deadline_seconds")).longValue() * 1000;
            while (!complete && failure.get() == null && System.currentTimeMillis() < deadline) {
                EventQueue.invokeAndWait(() -> { try { handleDialogs(); } catch (Throwable error) { failure.compareAndSet(null, error); } });
                checkpoint(); Thread.sleep(50);
            }
            watching = false;
            if (failure.get() != null) throw failure.get();
            require(complete, "Deadline reached before exact source completion dialog");
            Thread.sleep(250);
            require(dashboard && reviews.size() == (hasHu ? 2 : 1), "Required real dashboard/reviews not executed");
            require(observer.count == (hasHu ? 2 : 1), "Unexpected actual StarDist target execution count");
            require(nativeVariant ? workers.size() == (hasHu ? 2 : 1) : workers.isEmpty(), "Worker provenance count inconsistent");
            require(errors.isEmpty(), "Unhandled runtime exceptions");
            report.put("exports", reopenExports());
            report.put("whole_analysis_macro_executed", true);
            report.put("status", "PASS_TOP_MENU_WORKFLOW_SCOPE"); exit = 0;
        } catch (Throwable error) {
            report.put("error", error.toString()); error.printStackTrace();
            report.put("status", "BLOCKED_SETUP".equals(report.get("status")) || "SETTING_UP".equals(report.get("status")) ? "BLOCKED_SETUP" : "FAIL_TOP_MENU_WORKFLOW_SCOPE");
        } finally {
            watching = false;
            report.put("errors", new ArrayList<>(errors)); report.put("worker_processes", new LinkedHashMap<>(workers));
            if (observer != null) { report.put("matching_module_executions", observer.count); report.put("actual_inference_calls", observer.calls); }
            if (output != null) try {
                String log = IJ.getLog(); Files.writeString(output.resolve("imagej.log"), log == null ? "" : log); checkpoint();
            } catch (Exception writeError) { writeError.printStackTrace(); exit = 3; }
        }
        System.exit(exit);
    }

    private void prepareInput() throws Exception {
        ImagePlus image = IJ.openImage((String)config.get("fixture"));
        require(image != null && image.getWidth() == 175 && image.getHeight() == 175 && image.getBitDepth() == 8, "Public fixture shape/type invalid");
        ij.ImageStack stack = new ij.ImageStack(175, 175);
        stack.addSlice("Hu", image.getProcessor().duplicate());
        ij.process.ByteProcessor shifted = new ij.process.ByteProcessor(175, 175);
        for (int y=0;y<175;y++) for (int x=3;x<175;x++) shifted.set(x,y,image.getProcessor().get(x-3,y));
        stack.addSlice("Marker", shifted);
        image.close();
        image = new ImagePlus("public_neurons", stack); image.setDimensions(2,1,1); image.setOpenAsHyperStack(true);
        image = new ij.CompositeImage(image, ij.CompositeImage.COMPOSITE);
        image.getCalibration().setUnit("microns"); image.getCalibration().pixelWidth = .568; image.getCalibration().pixelHeight = .568;
        IJ.saveAsTiff(image, input.toString());
        ImagePlus reopened = IJ.openImage(input.toString()); require(reopened != null, "Prepared input cannot reopen");
        report.put("input", snapshot(reopened)); report.put("prepared_input_sha256", hash(input));
        image.close(); reopened.close();
    }

    private void handleDialogs() throws Exception {
        for (Window window : Window.getWindows()) {
            if (!(window instanceof Dialog) || !window.isShowing() || handled.contains(window)) continue;
            Dialog dialog = (Dialog)window;
            String title = dialog.getTitle(), text = componentText(window);
            Map<String,Object> event = map("title", title, "class", window.getClass().getName(), "text", text);
            if (title.trim().equals(menu.trim() + (nativeVariant ? " [MacroFork]" : ""))) {
                if(!dashboardSeen.containsKey(window)) { dashboardSeen.put(window,System.currentTimeMillis()); continue; }
                if(System.currentTimeMillis()-dashboardSeen.get(window)<500) continue;
                require(!dashboard, "Repeated dashboard");
                List<JTextField> fields = components(window, JTextField.class);
                List<JCheckBox> boxes = components(window, JCheckBox.class);
                List<JRadioButton> radios = components(window, JRadioButton.class);
                event.put("field_count", fields.size()); event.put("checkbox_labels", labels(boxes)); event.put("radio_labels", labels(radios));
                events.add(event); checkpoint();
                require(fields.size() == 5 && boxes.size() == (hasHu ? 6 : 5) && radios.size() == (hasHu ? 4 : 3), "Unrecognized real marker dashboard structure");
                require(text.contains("NEURONAL SUBTYPE ANALYSIS") || !hasHu, "Hu marker dashboard labels differ");
                String[] values = hasHu ? new String[]{input.toString(), "1", "Marker", "2", "NA"}
                                        : new String[]{input.toString(), "Marker", "2", "NA", "NA"};
                for (int i=0;i<values.length;i++) fields.get(i).setText(values[i]);
                for (JCheckBox box : boxes) box.setSelected(false);
                boxes.get(1).setSelected(true);
                require("DeepImageJ".equals(radios.get(0).getText()), "Ganglia radio order changed"); radios.get(0).setSelected(true);
                dashboard = true; event.put("action", "set documented parameters; click OK"); handled.add(window); click(window, "OK");
            } else if (title.equals("GAT v1.0") && text.contains("Thank you for using GAT")) {
                event.put("action", "acknowledge original first-run notice"); events.add(event); handled.add(window); click(window, "OK");
            } else if (title.equals("Save location already exists ") && text.contains("Custom Identifier")) {
                require(dashboard && !review, "Save identifier out of order");
                require(dialog instanceof GenericDialog, "Unexpected save dialog implementation");
                Vector<?> fields = ((GenericDialog)dialog).getStringFields(); require(fields.size() == 1, "Unexpected identifier fields");
                ((TextField)fields.get(0)).setText("_1");
                event.put("action", "set identifier _1; click OK"); events.add(event); handled.add(window); click(window, "OK");
            } else if (!hasHu && title.equals("Advanced Parameters") && text.contains("Default values shown below")) {
                require(dialog instanceof GenericDialog && dashboard && !review, "Unexpected no-Hu advanced dialog");
                GenericDialog gd=(GenericDialog)dialog;
                Vector<?> numbers=gd.getNumericFields(), checks=gd.getCheckboxes();
                require(numbers.size()==3 && checks.size()==1, "No-Hu advanced fields differ");
                double[] expected={1.0,0.4,0.3};
                for(int i=0;i<3;i++) require(Double.parseDouble(((TextField)numbers.get(i)).getText())==expected[i], "No-Hu default numeric value differs");
                require(!((Checkbox)checks.get(0)).getState(), "Custom ROI unexpectedly enabled");
                event.put("action", "accept exact original no-Hu defaults"); events.add(event); handled.add(window); click(window,"OK");
            } else if ((hasHu && text.contains("Correct Hu ROIs if needed. You can add or delete ROIs using the ROI Manager"))
                    || text.contains("Verify ROIs for Marker. Add or delete ROIs as needed using the ROI Manager.")) {
                String marker = text.contains("Correct Hu ROIs") ? "Hu" : "Marker";
                require(dashboard && !reviews.containsKey(marker) && (!marker.equals("Marker") || !hasHu || reviews.containsKey("Hu")), "Unexpected marker review order");
                RoiManager rm=RoiManager.getInstance(); require(rm!=null && rm==RoiManager.getInstance2(), "Actual global ROI Manager absent");
                require(rm.getCount()>0, "Positive marker review requires a nonempty actual output");
                List<Object> before=rois(Arrays.asList(rm.getRoisAsArray()));
                List<Object> after=rois(Arrays.asList(rm.getRoisAsArray()));
                reviews.put(marker,map("before",before,"after",after));
                event.put("marker",marker); event.put("action","unchanged marker review");
                events.add(event); handled.add(window); review=true; click(window,"OK");
            } else if (text.trim().equals("Multi-channel Neuron analysis complete") || text.replace("OK", "").trim().equals("Multi-channel Neuron analysis complete")) {
                require(reviews.size()==(hasHu?2:1), "Completion before all reviews");
                event.put("action", "acknowledge exact original completion exit"); events.add(event); handled.add(window); click(window, "OK"); complete = true;
            } else {
                if (!unknown.containsKey(window)) { unknown.put(window, System.currentTimeMillis()); event.put("action", "UNKNOWN_LEFT_UNTOUCHED"); events.add(event); checkpoint(); }
                require(System.currentTimeMillis() - unknown.get(window) < 10000, "Unknown dialog left untouched: " + title + " | " + text);
            }
        }
    }

    private List<Object> reopenExports() throws Exception {
        Path folder = input.getParent().resolve("Analysis/public_neurons_1");
        List<String> required = new ArrayList<>(Arrays.asList("Marker_unmodified_ROIs_public_neurons_1.zip", "Marker_ROIs_public_neurons_1.zip",
            "Analysis_public_neurons_1_cell_counts.csv", "MAX_public_neurons_1.tif", "Log.txt"));
        if(hasHu) required.addAll(Arrays.asList("Hu_unmodified_ROIs_public_neurons_1.zip", "Hu_ROIs_public_neurons_1.zip", "Hu_label_MAX_public_neurons_1.tif"));
        List<Object> files = new ArrayList<>();
        for (String name : required) {
            Path path = folder.resolve(name); require(Files.isRegularFile(path) && Files.size(path) > 0, "Required export missing: " + name);
            Map<String,Object> row = map("path", name, "bytes", Files.size(path), "sha256", hash(path));
            if (name.endsWith(".tif") || name.endsWith(".jpg")) {
                ImagePlus image = IJ.openImage(path.toString()); require(image != null, "Saved image cannot reopen: " + name);
                row.put("reopened_image", snapshot(image)); image.close();
            } else if (name.endsWith(".zip")) {
                List<Roi> rois = new ArrayList<>();
                try (ZipInputStream zip = new ZipInputStream(Files.newInputStream(path))) {
                    ZipEntry entry; while((entry = zip.getNextEntry()) != null) {
                        require(entry.getName().endsWith(".roi"), "Unexpected ROI archive member");
                        Roi roi = new RoiDecoder(zip.readAllBytes(), entry.getName()).getRoi(); require(roi != null, "Saved ROI cannot reopen"); rois.add(roi);
                    }
                }
                row.put("reopened_rois", rois(rois));
                Map<?,?> reviewed=(Map<?,?>)reviews.get(name.startsWith("Hu_")?"Hu":"Marker");
                List<?> expected=(List<?>)reviewed.get(name.contains("unmodified")?"before":"after");
                require(rois.size() == expected.size(), "Saved/review ROI count differs");
            } else if (name.endsWith(".csv")) row.put("reopened_csv", Files.readString(path));
            files.add(row);
        }
        return files;
    }

    private static List<Object> rois(List<Roi> rois) {
        List<Object> result = new ArrayList<>();
        for (Roi roi : rois) { List<Object> points = new ArrayList<>(); FloatPolygon p = roi.getFloatPolygon();
            for(int i=0;i<p.npoints;i++) points.add(Arrays.asList(p.xpoints[i], p.ypoints[i]));
            result.add(Arrays.asList(roi.getName(), roi.getType(), roi.getPosition(), roi.getCPosition(), roi.getZPosition(), roi.getTPosition(), points)); }
        return result;
    }
    private static Map<String,Object> snapshot(ImagePlus image) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256"); Map<Integer,Integer> areas = new TreeMap<>();
        for(int z=1;z<=image.getStackSize();z++)for(int p=0;p<image.getWidth()*image.getHeight();p++) {
            float value=image.getStack().getProcessor(z).getf(p); int bits=Float.floatToIntBits(value);
            digest.update(new byte[]{(byte)(bits>>>24),(byte)(bits>>>16),(byte)(bits>>>8),(byte)bits});
            if(value>0&&value==Math.rint(value)) areas.merge((int)value,1,Integer::sum);
        }
        return map("width", image.getWidth(), "height", image.getHeight(), "channels", image.getNChannels(), "slices", image.getNSlices(),
            "frames", image.getNFrames(), "bits", image.getBitDepth(), "pixel_width", image.getCalibration().pixelWidth,
            "pixel_height", image.getCalibration().pixelHeight, "unit", image.getCalibration().getUnit(),
            "pixel_f32be_sha256", hex(digest.digest()), "positive_integer_areas", areas);
    }
    private static List<String> labels(List<? extends AbstractButton> buttons) { List<String> out = new ArrayList<>(); for(AbstractButton b:buttons)out.add(b.getText());return out; }
    private static <T extends Component> List<T> components(Component c, Class<T> type) {
        List<T> result = new ArrayList<>(); if(type.isInstance(c))result.add(type.cast(c));
        if(c instanceof Container)for(Component child:((Container)c).getComponents())result.addAll(components(child,type)); return result;
    }
    private static String componentText(Component c) throws Exception {
        String text = c instanceof JLabel ? ((JLabel)c).getText() : c instanceof Label ? ((Label)c).getText() : "";
        if(c instanceof TextComponent)text += ((TextComponent)c).getText();
        if(c.getClass().getName().equals("ij.gui.MultiLineLabel")) { Field f = c.getClass().getDeclaredField("lines"); f.setAccessible(true); text += String.join("\n", (String[])f.get(c)); }
        if(c instanceof JOptionPane)text += String.valueOf(((JOptionPane)c).getMessage());
        if(c instanceof Container)for(Component child:((Container)c).getComponents())text += "\n" + componentText(child);
        return text.trim();
    }
    private static void click(Component c,String label) {
        for(AbstractButton b:components(c,AbstractButton.class))if(label.equals(b.getText().trim())){b.doClick();return;}
        for(Button b:components(c,Button.class))if(label.equals(b.getLabel().trim())) { for(ActionListener listener:b.getActionListeners())listener.actionPerformed(new ActionEvent(b,ActionEvent.ACTION_PERFORMED,b.getActionCommand())); return; }
        throw new AssertionError("Required actual dialog button absent: " + label);
    }
    private static void require(boolean condition,String message){if(!condition)throw new AssertionError(message);}
    private static Map<String,Object> map(Object... values){Map<String,Object> m=new LinkedHashMap<>();for(int i=0;i<values.length;i+=2)m.put((String)values[i],values[i+1]);return m;}
    private static String hash(Path p)throws Exception{return hex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(p)));}
    private static String hex(byte[] bytes){StringBuilder s=new StringBuilder();for(byte b:bytes)s.append(String.format("%02x",b&255));return s.toString();}
    private static Map<String,Object> provenance(Class<?> c)throws Exception{try(java.io.InputStream s=c.getResourceAsStream("/"+c.getName().replace('.','/')+".class")){return map("name",c.getName(),"code_source",c.getProtectionDomain().getCodeSource().getLocation().toString(),"class_sha256",hex(MessageDigest.getInstance("SHA-256").digest(s.readAllBytes())));}}
    private synchronized void checkpoint()throws Exception{synchronized(scriptEvents){report.put("script_module_events",new ArrayList<>(scriptEvents));} Files.writeString(output.resolve("report.json"),JSON.toJson(report)+"\n");}
}
