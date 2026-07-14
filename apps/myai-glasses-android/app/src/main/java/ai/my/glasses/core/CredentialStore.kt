package ai.my.glasses.core

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Device credential storage backed by the Android Keystore (via
 * EncryptedSharedPreferences: AES256-GCM values, Keystore-held master key).
 * The raw ody_ token never touches plain prefs, logs, or backups
 * (android:allowBackup defaults off for this app's data path).
 */
class CredentialStore(context: Context) {
    private val prefs = EncryptedSharedPreferences.create(
        context,
        "myai_glasses_credentials",
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    var hostBaseUrl: String?
        get() = prefs.getString("host_base_url", null)
        set(v) = prefs.edit().putString("host_base_url", v).apply()

    var deviceToken: String?
        get() = prefs.getString("device_token", null)
        set(v) = prefs.edit().putString("device_token", v).apply()

    var tokenId: String?
        get() = prefs.getString("token_id", null)
        set(v) = prefs.edit().putString("token_id", v).apply()

    /** Pinned SHA-256 of the host's self-signed TLS cert (from the pairing
     *  payload); null when the host is plain HTTP or has a CA-signed cert. */
    var certSha256: String?
        get() = prefs.getString("cert_sha256", null)
        set(v) = prefs.edit().putString("cert_sha256", v).apply()

    val isPaired: Boolean get() = hostBaseUrl != null && deviceToken != null

    /** Wipe on revocation / re-pair. */
    fun clear() = prefs.edit().clear().apply()
}
