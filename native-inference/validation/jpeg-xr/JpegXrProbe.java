import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import loci.formats.FormatTools;
import loci.formats.codec.JPEGXRCodec;
import loci.formats.codec.CodecOptions;
import loci.formats.services.JPEGXRServiceImpl;
import ome.jxrlib.Decode;
import ome.jxrlib.ImageData;
import org.scijava.nativelib.NativeLibraryUtil;

/** Validation only: official golden pixels, unchanged published Java API, actual Bio-Formats codec. */
public final class JpegXrProbe {
    private static String hash(String algorithm, byte[] bytes) throws Exception {
        StringBuilder out = new StringBuilder();
        for (byte b : MessageDigest.getInstance(algorithm).digest(bytes)) out.append(String.format("%02x", b & 255));
        return out.toString();
    }
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    public static void main(String[] args) throws Exception {
        Path source = Paths.get(args[0]);
        Path manifest = Paths.get(args[1]);
        Path output = Paths.get(args[2]);
        System.out.println("java.version=" + System.getProperty("java.version"));
        System.out.println("os.name=" + System.getProperty("os.name") + " os.arch=" + System.getProperty("os.arch"));
        System.out.println("bioformats.version=" + FormatTools.VERSION);
        check("8.5.0".equals(FormatTools.VERSION), "Unexpected Bio-Formats version");
        String platform = NativeLibraryUtil.getPlatformLibraryPath("META-INF/lib/");
        check(platform.equals("META-INF/lib/" + args[3] + "/"), "JVM architecture does not match requested native platform: " + platform);
        String resource = platform + System.mapLibraryName("jxrjava");
        System.out.println("native.resource=" + Decode.class.getClassLoader().getResource(resource));
        System.out.println("loader.code=" + NativeLibraryUtil.class.getProtectionDomain().getCodeSource().getLocation());
        System.out.println("decode.code=" + Decode.class.getProtectionDomain().getCodeSource().getLocation());
        System.out.println("codec.code=" + JPEGXRCodec.class.getProtectionDomain().getCodeSource().getLocation());
        // Loading Decode must initialize the actual native library before vector helpers.
        Class.forName("ome.jxrlib.Decode");
        ImageData vector = new ImageData();
        check(vector.size() == 0 && vector.isEmpty(), "Legacy ImageData empty constructor");
        vector.reserve(12); vector.add('J'); vector.add('X');
        check(vector.capacity() >= 12 && vector.size() == 2 && vector.get(1) == 'X', "Legacy vector reserve/add/get");
        vector.set(1, 'R'); check(vector.get(1) == 'R', "Legacy vector set");
        vector.clear(); check(vector.isEmpty(), "Legacy vector clear"); vector.delete();
        ImageData sized = new ImageData(4); check(sized.size() == 4, "Legacy vector sized constructor"); sized.delete();
        List<String> rows = new ArrayList<>();
        rows.add("filename\twidth\theight\tbytes_per_pixel\tis_bgr\tinput_sha256\tdecoded_md5\tdecoded_sha256\tbioformats_sha256\tstatus");
        for (String line : Files.readAllLines(manifest, StandardCharsets.UTF_8)) {
            if (line.startsWith("filename") || line.trim().isEmpty()) continue;
            String[] fields = line.split("\t");
            String name = fields[0];
            int width = Integer.parseInt(fields[1]), height = Integer.parseInt(fields[2]), bpp = Integer.parseInt(fields[3]);
            byte[] encoded = Files.readAllBytes(source.resolve("fixtures/first-tiles").resolve(name));
            check(hash("SHA-256", encoded).equals(fields[5]), name + ": fixture SHA-256");
            Decode decoder = new Decode(encoded);
            check(decoder.getWidth() == width && decoder.getHeight() == height && decoder.getBytesPerPixel() == bpp,
                  name + ": dimensions / pixel depth");
            byte[] raw = Decode.decodeFirstFrame(encoded, 0, encoded.length);
            check(raw.length == width * height * bpp, name + ": length");
            check(hash("MD5", raw).equals(fields[4]), name + ": upstream golden-pixel MD5");
            ByteBuffer buf = ByteBuffer.allocateDirect(raw.length);
            decoder.toBytes(buf);
            byte[] viaBuffer = new byte[raw.length];
            buf.get(viaBuffer);
            check(Arrays.equals(raw, viaBuffer), name + ": ByteBuffer versus first-frame API");
            byte[] expected = raw.clone();
            if (decoder.isBGR()) {
                check(bpp == 3, name + ": expected three-channel BGR fixture");
                for (int i = 0; i < expected.length; i += 3) {
                    byte b = expected[i]; expected[i] = expected[i + 2]; expected[i + 2] = b;
                }
            }
            byte[] service = new JPEGXRServiceImpl().decompress(encoded);
            CodecOptions options = new CodecOptions();
            options.width = width; options.height = height; options.bitsPerSample = bpp == 3 ? 8 : 16;
            options.interleaved = true; options.littleEndian = true; options.maxBytes = raw.length;
            byte[] codec = new JPEGXRCodec().decompress(encoded, options);
            check(Arrays.equals(expected, service), name + ": Bio-Formats BGR-to-RGB normalization");
            check(Arrays.equals(service, codec), name + ": Bio-Formats codec/service equality");
            String row = name + "\t" + width + "\t" + height + "\t" + bpp + "\t" + decoder.isBGR() + "\t" +
                hash("SHA-256", encoded) + "\t" + hash("MD5", raw) + "\t" + hash("SHA-256", raw) + "\t" + hash("SHA-256", codec) + "\tPASS";
            rows.add(row);
            Files.write(output, rows, StandardCharsets.UTF_8);
            System.out.println(row);
        }
        check(rows.size() == 14, "Expected all 13 upstream golden fixtures");
        System.out.println("PASS: 13 official fixtures; native, direct-buffer, Bio-Formats service and codec decode");
    }
}
