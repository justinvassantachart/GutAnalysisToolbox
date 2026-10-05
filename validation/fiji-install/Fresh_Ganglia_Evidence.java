import java.security.MessageDigest;
/** Exact byte hashes for the public-fixture mask, independent of TIFF serialization. */
public final class Fresh_Ganglia_Evidence {
    private Fresh_Ganglia_Evidence() {}
    public static String sha256(byte[] bytes) throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(bytes);
        StringBuilder result = new StringBuilder(64);
        for (byte value : digest) result.append(String.format("%02x", value & 0xff));
        return result.toString();
    }
}
