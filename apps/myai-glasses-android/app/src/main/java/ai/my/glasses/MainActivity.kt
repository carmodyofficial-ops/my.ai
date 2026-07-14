package ai.my.glasses

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts.RequestMultiplePermissions
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import ai.my.glasses.core.Failure
import ai.my.glasses.ui.MyAiAccent
import ai.my.glasses.ui.MyAiBrand
import ai.my.glasses.ui.MyAiConnected
import ai.my.glasses.ui.MyAiTheme
import ai.my.glasses.wearables.GlassesHostFactory

/**
 * v1 UI: Home (status + ask + Look-and-Ask), inline pairing, privacy state,
 * failure recovery. Voice/vision controls light up only when the gateway's
 * /capabilities says the component is available — no dead buttons.
 */
class MainActivity : ComponentActivity() {

    companion object {
        // Android runtime permissions the DAT SDK requires (plus mic for voice).
        private val PERMISSIONS = arrayOf(
            Manifest.permission.BLUETOOTH,
            Manifest.permission.BLUETOOTH_CONNECT,
            Manifest.permission.CAMERA,
            Manifest.permission.RECORD_AUDIO,
        )
    }

    // Field initializer: the SDK's permission launcher must be registered
    // before the Activity starts (see GlassesHost). The host is per-Activity
    // because that launcher is; the adapter inside it is process-wide.
    private val glassesHost = GlassesHostFactory.create(this)

    private val vm: MainViewModel by viewModels {
        MainViewModel.factory(applicationContext, glassesHost.adapter)
    }

    private val permissionLauncher =
        registerForActivityResult(RequestMultiplePermissions()) { result ->
            // The SDK may only be initialized AFTER the runtime grants.
            if (result.values.all { it }) onGlassesPermissionsReady()
        }

    /** Notifications are for the listening indicator only — requested apart from
     *  [PERMISSIONS] so a denial cannot block the glasses from initializing. */
    private val notificationLauncher =
        registerForActivityResult(RequestMultiplePermissions()) { /* advisory */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // The retained ViewModel keeps the process-wide adapter AND the mic
        // session, but the DAT permission launcher dies with its Activity — so
        // re-point the ViewModel at THIS Activity's host on every recreation.
        vm.attachHost(glassesHost)

        // Only launch when something is actually missing. RequestMultiplePermissions
        // invokes its callback immediately (no UI) when everything is already
        // granted, so the unconditional launch re-ran the whole SDK bootstrap on
        // every rotation.
        if (PERMISSIONS.any { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }) {
            permissionLauncher.launch(PERMISSIONS)
        } else {
            onGlassesPermissionsReady()
        }
        requestNotificationPermissionIfNeeded()

        setContent { MyAiTheme { HomeScreen(vm) } }
        handlePairingIntent(intent)
    }

    /** Idempotent: initialize() and the bootstrap both no-op when already done. */
    private fun onGlassesPermissionsReady() {
        glassesHost.adapter.initialize(this)
        vm.onAndroidPermissionsGranted(this)
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
        val perm = Manifest.permission.POST_NOTIFICATIONS
        if (checkSelfPermission(perm) != PackageManager.PERMISSION_GRANTED) {
            notificationLauncher.launch(arrayOf(perm))
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handlePairingIntent(intent)
    }

    /** myai-glasses://pair?p=<base64url(payload JSON)> — deep link from the
     *  host's /pair-glasses page. This scheme is BROWSABLE and exported, so any
     *  web page or app can send it; the payload is untrusted. Stage it for
     *  explicit confirmation (proposePairing) — never pair silently. The DAT
     *  registration callback shares the scheme but not the host. */
    private fun handlePairingIntent(intent: Intent?) {
        val uri = intent?.data ?: return
        if (uri.scheme != "myai-glasses" || uri.host != "pair") return
        // Consume it: singleTop re-delivers the same intent on every recreation,
        // so without this the prompt would re-appear on each rotation.
        setIntent(Intent())
        val encoded = uri.getQueryParameter("p") ?: return
        val json = runCatching {
            String(java.util.Base64.getUrlDecoder().decode(encoded), Charsets.UTF_8)
        }.getOrNull() ?: return
        vm.proposePairing(json)
    }

    // No audio teardown here on purpose. The mic now lives in the ViewModel, and
    // onCleared() closes it — which fires when the user really leaves, not on a
    // rotation. Tearing it down from onDestroy cut the SCO route mid-utterance on
    // every configuration change (and re-toned the glasses); doing it only when
    // !isChangingConfigurations was worse still, because the abandoned Activity's
    // VoiceSession kept a hot AudioRecord the new one knew nothing about.
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(vm: MainViewModel) {
    val ui by vm.ui.collectAsState()
    val drawer = rememberDrawerState(DrawerValue.Closed)
    val scope = rememberCoroutineScope()

    ModalNavigationDrawer(
        drawerState = drawer,
        gesturesEnabled = ui.paired,              // history exists only once paired
        drawerContent = { HistoryDrawer(vm, ui) { scope.launch { drawer.close() } } },
    ) {
        // Pull down anywhere to re-probe host health/capabilities and re-poke
        // the glasses connection — the "why is Talk greyed out" recovery gesture.
        PullToRefreshBox(
            isRefreshing = ui.refreshing,
            onRefresh = vm::refresh,
            // statusBarsPadding on the BOX (not just the inner column) so the app
            // draws edge-to-edge but the header AND the pull-to-refresh spinner both
            // clear the system clock/notifications.
            modifier = Modifier.fillMaxSize().statusBarsPadding(),
        ) {
            Column(
                Modifier.fillMaxSize().verticalScroll(rememberScrollState())
                    .padding(start = 20.dp, end = 20.dp, bottom = 20.dp, top = 16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                BrandHeader(
                    connected = ui.paired,
                    onMenu = if (ui.paired) {
                        { vm.refreshHistory(); scope.launch { drawer.open() } }
                    } else null,
                )
                // Setup gates the app: connect glasses + host first, then the
                // main experience (assistant + productivity) takes over.
                if (!ui.paired) SetupScreen(vm, ui) else MainScreen(vm, ui)
            }
        }
    }
    // A staged pairing (from a deep link, QR, or paste) must be confirmed here
    // before any credential is written — see MainViewModel.proposePairing.
    ui.pairingPrompt?.let { PairingConfirmDialog(it, vm) }
}

/** Left nav: recent chats and Look-and-Ask history for this device's owner. */
@Composable
private fun HistoryDrawer(vm: MainViewModel, ui: UiState, onClose: () -> Unit) {
    val ctx = LocalContext.current
    ModalDrawerSheet(
        drawerContainerColor = MaterialTheme.colorScheme.surface,
        modifier = Modifier.fillMaxWidth(0.82f),
    ) {
        Column(
            Modifier.fillMaxSize().statusBarsPadding()
                .verticalScroll(rememberScrollState()).padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("my.ai", style = MaterialTheme.typography.headlineMedium, color = MyAiBrand)
            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)

            Text("Conversations", style = MaterialTheme.typography.titleMedium)
            if (ui.chatHistory.isEmpty()) {
                Text("No conversations yet", style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            ui.chatHistory.forEach { c ->
                DrawerRow(c.name, "${c.messages} messages") {
                    // View the full thread in the my.ai web chat (same host/login).
                    vm.hostUrl()?.let {
                        ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(it.trimEnd('/') + "/")))
                    }
                    onClose()
                }
            }

            Spacer(Modifier.height(6.dp))
            Text("Look & Ask", style = MaterialTheme.typography.titleMedium)
            if (ui.visionHistory.isEmpty()) {
                Text("Nothing captured yet", style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            ui.visionHistory.forEach { v ->
                DrawerRow(v.question.ifBlank { "What am I looking at?" }, v.answer)
            }
        }
    }
}

@Composable
private fun DrawerRow(title: String, subtitle: String, onClick: (() -> Unit)? = null) {
    Column(
        Modifier
            .fillMaxWidth()
            .then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier)
            .padding(vertical = 6.dp),
    ) {
        Text(title, style = MaterialTheme.typography.bodyMedium,
            maxLines = 1, overflow = TextOverflow.Ellipsis)
        Text(subtitle, style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 2, overflow = TextOverflow.Ellipsis)
    }
}

/** One checkable row (a note or task) in a home card. */
private data class ChecklistRow(
    val id: String, val label: String, val sub: String? = null, val done: Boolean = false,
)

/** A home card: a checklist of items (tap the box to complete one) plus an
 *  inline quick-add with an optional date. Notes and tasks both live here. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ChecklistCard(
    title: String, items: List<ChecklistRow>, empty: String, hint: String,
    onCheck: (String) -> Unit,
    onAdd: (text: String, date: String?) -> Unit,
    // Notes are reference text (no completion); tasks are checkable. Notes pass
    // false so no checkbox renders (completion for notes would collide with the
    // web app's Archive flag).
    showChecks: Boolean = true,
) {
    var draft by remember { mutableStateOf("") }
    var dateMillis by remember { mutableStateOf<Long?>(null) }
    var showPicker by remember { mutableStateOf(false) }

    fun isoDate(ms: Long): String {
        // UTC calendar date (YYYY-MM-DD) — a plain due date, timezone-free.
        val d = java.util.Calendar.getInstance(java.util.TimeZone.getTimeZone("UTC"))
        d.timeInMillis = ms
        return "%04d-%02d-%02d".format(
            d.get(java.util.Calendar.YEAR),
            d.get(java.util.Calendar.MONTH) + 1,
            d.get(java.util.Calendar.DAY_OF_MONTH))
    }
    val submit = {
        if (draft.isNotBlank()) {
            onAdd(draft, dateMillis?.let { isoDate(it) }); draft = ""; dateMillis = null
        }
    }

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            if (items.isEmpty()) {
                Text(empty, style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            } else {
                items.take(8).forEach { row ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        // Tapping toggles done both ways — a completed task stays
                        // visible (greyed + struck through) and can be re-activated.
                        if (showChecks) {
                            Checkbox(checked = row.done, onCheckedChange = { onCheck(row.id) })
                        }
                        val labelColor = if (row.done)
                            MaterialTheme.colorScheme.onSurfaceVariant
                        else MaterialTheme.colorScheme.onSurface
                        val strike = if (row.done)
                            TextDecoration.LineThrough else null
                        Column(Modifier.weight(1f)) {
                            Text(row.label, style = MaterialTheme.typography.bodyMedium,
                                color = labelColor, textDecoration = strike,
                                maxLines = 1, overflow = TextOverflow.Ellipsis)
                            row.sub?.let {
                                Text(it, style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                }
            }
            Spacer(Modifier.height(4.dp))
            OutlinedTextField(
                value = draft, onValueChange = { draft = it },
                label = { Text(hint) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                keyboardActions = KeyboardActions(onDone = { submit() }),
            )
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                OutlinedButton(onClick = { showPicker = true }, modifier = Modifier.weight(1f)) {
                    Text(dateMillis?.let { isoDate(it) } ?: "Pick date")
                }
                Button(enabled = draft.isNotBlank(), onClick = submit) { Text("Add") }
            }
        }
    }

    if (showPicker) {
        val state = rememberDatePickerState()
        DatePickerDialog(
            onDismissRequest = { showPicker = false },
            confirmButton = {
                Button(onClick = { dateMillis = state.selectedDateMillis; showPicker = false }) {
                    Text("OK")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { dateMillis = null; showPicker = false }) { Text("Clear") }
            },
        ) { DatePicker(state = state) }
    }
}

/** my.ai wordmark + a live connection dot — the brand anchor on every screen. */
@Composable
private fun BrandHeader(connected: Boolean, onMenu: (() -> Unit)? = null) {
    Row(
        Modifier.fillMaxWidth().padding(bottom = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        onMenu?.let {
            Text(
                "☰",
                style = MaterialTheme.typography.headlineSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier
                    .clip(CircleShape)
                    .clickable(onClick = it)
                    .padding(end = 12.dp),
            )
        }
        Text(
            "my.ai",
            style = MaterialTheme.typography.headlineMedium,
            color = MyAiBrand,
        )
        Text(
            "  glasses",
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.weight(1f))
        Box(
            Modifier
                .size(9.dp)
                .clip(CircleShape)
                .background(if (connected) MyAiConnected else MaterialTheme.colorScheme.outline),
        )
    }
    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
}

/** First screen: both connection events, nothing else. */
@Composable
private fun SetupScreen(vm: MainViewModel, ui: UiState) {
    Text("Connect", style = MaterialTheme.typography.headlineMedium)
    Text("Link your glasses and your my.ai host — then you're in.")

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("1 · Glasses", style = MaterialTheme.typography.titleMedium)
            StatusRow("Status", ui.glassesLabel)
            ui.glassesDetail?.let {
                Text("Glasses report: $it", color = MaterialTheme.colorScheme.error)
            }
            Text("Pair the glasses in the Meta AI app (Bluetooth), then pull " +
                "down here to refresh. Voice also works with just the phone — " +
                "glasses can join later.")
        }
    }

    // Host pairing: find the my.ai host on Wi-Fi and approve on the host. No
    // QR/JSON to copy. (A myai-glasses:// deep link from the host's browser
    // page still works too, routed through the confirm dialog — but there's no
    // in-app QR scan or JSON paste to fiddle with.)
    HostDiscoverySection(vm, ui)

    ui.failure?.let {
        Text(recoveryHint(it), color = MaterialTheme.colorScheme.error)
    }
}

@Composable
private fun HostDiscoverySection(vm: MainViewModel, ui: UiState) {
    // While awaiting approval, show the verify code prominently.
    ui.enroll?.let { e ->
        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("2 · Approve on ${e.hostName}", style = MaterialTheme.typography.titleMedium)
                if (e.verifyCode.isNotBlank()) {
                    Text("Verification code",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(e.verifyCode,
                        style = MaterialTheme.typography.displaySmall,
                        color = MyAiAccent)
                }
                Text(e.status)
                Text("On your my.ai host, open the pair-glasses page and approve this " +
                    "device — confirm the code above matches.",
                    style = MaterialTheme.typography.bodySmall)
                OutlinedButton(onClick = vm::cancelEnroll) { Text("Cancel") }
            }
        }
        return
    }

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("2 · my.ai host", style = MaterialTheme.typography.titleMedium)
            Text("Find your my.ai host on this Wi-Fi and approve this device on the " +
                "host — no code to copy.", style = MaterialTheme.typography.bodySmall)
            Button(
                onClick = vm::discoverHosts,
                enabled = !ui.scanning,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(if (ui.scanning) "Scanning…" else "Find my.ai host on Wi-Fi") }
            ui.discoveredHosts.forEach { h ->
                OutlinedButton(
                    onClick = { vm.enrollWith(h) },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("${h.name} · ${h.host}:${h.port}${if (h.tls) " · TLS" else ""}") }
            }
            if (!ui.scanning && ui.discoveredHosts.isEmpty()) {
                Text("Tap to scan. Make sure the phone is on the same Wi-Fi as the host.",
                    style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

/** Confirm dialog for a staged pairing. Pairing never proceeds without it. */
@Composable
private fun PairingConfirmDialog(prompt: PairingPrompt, vm: MainViewModel) {
    androidx.compose.material3.AlertDialog(
        onDismissRequest = vm::dismissPairingPrompt,
        title = { Text(if (prompt.replacesExisting) "Replace pairing?" else "Pair with host?") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Host: ${prompt.host}")
                Text(if (prompt.tls) "Connection: TLS (pinned)" else "Connection: plaintext")
                if (prompt.replacesExisting) {
                    Text(
                        "This REPLACES your current pairing. All voice and camera " +
                            "data will go to this host. Only continue if you started " +
                            "this yourself.",
                        color = MaterialTheme.colorScheme.error,
                    )
                }
            }
        },
        confirmButton = { Button(onClick = vm::confirmPairingPrompt) { Text("Pair") } },
        dismissButton = { OutlinedButton(onClick = vm::dismissPairingPrompt) { Text("Cancel") } },
    )
}

/** The application proper: assistant + productivity, entered once paired. */
@Composable
private fun MainScreen(vm: MainViewModel, ui: UiState) {

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            StatusRow("Glasses", ui.glassesLabel)
            StatusRow("my.ai host", ui.hostLabel)
            StatusRow("Model", ui.modelLabel)
            StatusRow("Voice", ui.voiceLabel)
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Column(Modifier.weight(1f)) {
                    Text("Keep session context", style = MaterialTheme.typography.bodyMedium)
                    Text(
                        if (ui.storeTranscript) "Follow-ups remembered in RAM this session"
                        else "No storage — words aren't retained or logged",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                androidx.compose.material3.Switch(
                    checked = ui.storeTranscript,
                    onCheckedChange = vm::setStoreTranscript,
                )
            }
            ui.failure?.let {
                Text(recoveryHint(it), color = MaterialTheme.colorScheme.error)
            }
            ui.glassesDetail?.let {
                Text("Glasses report: $it", color = MaterialTheme.colorScheme.error)
            }
        }
    }

    // Glasses touchpad control needs Notification Access to drive the user's
    // music (single tap = play/pause). Prompt until granted — re-checked on
    // ON_RESUME so the card disappears the moment the user returns from Settings
    // having granted it (composition wouldn't otherwise re-read the setting).
    val mediaCtx = LocalContext.current
    if (!rememberNotificationAccess(mediaCtx)) {
        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Enable glasses touchpad control", style = MaterialTheme.typography.titleMedium)
                Text("Grant Notification access so a single tap on the glasses plays/pauses " +
                    "your music (a 3-second hold talks to my.ai).",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                Button(onClick = {
                    mediaCtx.startActivity(
                        Intent("android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS")
                            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                }) { Text("Grant access") }
            }
        }
    }

    run {
            var draft by remember { mutableStateOf("") }
            // Text chat needs the host's chat model serving. If the host is up but
            // Ollama/the model isn't, the inputs are disabled and we show why + a
            // retry — a tap must not fail silently (UAT #2).
            val chatReady = ui.canTalk && ui.llmReady
            val send = {
                if (chatReady && draft.isNotBlank() && !ui.busy) {
                    vm.ask(draft); draft = ""
                }
            }
            if (ui.canTalk && !ui.llmReady) {
                Card(Modifier.fillMaxWidth()) {
                    Row(
                        Modifier.padding(12.dp).fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text("No model available on the host — is Ollama running?",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.error,
                            modifier = Modifier.weight(1f))
                        OutlinedButton(enabled = !ui.refreshing, onClick = vm::refresh) {
                            Text("Retry")
                        }
                    }
                }
            }
            OutlinedTextField(
                value = draft, onValueChange = { draft = it },
                label = { Text("Ask my.ai") },
                enabled = chatReady,
                modifier = Modifier.fillMaxWidth(),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { send() }),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    enabled = chatReady && draft.isNotBlank() && !ui.busy,
                    onClick = send,
                ) { Text(if (ui.busy) "Answering…" else "Ask") }
                OutlinedButton(enabled = ui.busy, onClick = vm::cancel) { Text("Stop") }
                // Reset to a fresh conversation (drops server context + clears the
                // panel). Enabled once there's something to clear (UAT #5).
                OutlinedButton(
                    enabled = !ui.busy &&
                        (ui.lastResponse.isNotBlank() || ui.lastQuestion.isNotBlank()),
                    onClick = { vm.newChat(); draft = "" },
                ) { Text("New chat") }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                // Push-to-talk: hold to record, release to send. Needs STT AND the
                // chat model (the transcript is answered by it).
                Button(
                    enabled = chatReady && ui.sttAvailable && !ui.busy,
                    onClick = { if (ui.listening) vm.stopListening() else vm.startListening() },
                ) { Text(if (ui.listening) "Listening — tap to send" else "Talk") }
                OutlinedButton(
                    enabled = ui.canTalk && ui.visionAvailable && !ui.busy,
                    onClick = vm::lookAndAsk,
                ) { Text("Look & Ask") }
            }

            // Response panel: show the Q&A pair (question + answer), not a bare
            // answer with no context (UAT #4).
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp)) {
                    if (ui.lastQuestion.isNotBlank()) {
                        Text("You", style = MaterialTheme.typography.labelLarge)
                        Spacer(Modifier.height(2.dp))
                        Text(ui.lastQuestion)
                        Spacer(Modifier.height(10.dp))
                    }
                    Text("my.ai", style = MaterialTheme.typography.labelLarge)
                    Spacer(Modifier.height(2.dp))
                    Text(ui.lastResponse.ifBlank { if (ui.busy) "…" else "—" })
                }
            }
    }

    // Productivity: live previews + quick-add against the my.ai host.
    ChecklistCard(
        title = "Notes",
        items = ui.notes.map {
            ChecklistRow(it.id, it.title.ifBlank { it.snippet }.ifBlank { "(untitled)" })
        },
        empty = "No notes yet",
        hint = "Quick note",
        onCheck = {},                 // notes aren't completable
        onAdd = vm::addNote,
        showChecks = false,
    )
    ChecklistCard(
        title = "Tasks",
        items = ui.tasks.map { t ->
            ChecklistRow(t.id, t.title, t.dueDate?.take(10)?.let { "due $it" },
                done = t.completed)
        },
        empty = "No tasks",
        hint = "Add a task",
        onCheck = vm::completeItem,
        onAdd = vm::addTask,
    )

    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        // Disabled mid-turn: deleting the session out from under a running stream
        // left it running against a deleted session with busy stuck true (L2).
        OutlinedButton(enabled = !ui.busy, onClick = vm::deleteConversation) {
            Text("Delete conversation")
        }
        OutlinedButton(onClick = vm::unpair) { Text("Unpair host") }
    }
}

@Composable
private fun StatusRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, style = MaterialTheme.typography.bodyMedium)
        Text(value, style = MaterialTheme.typography.bodyMedium)
    }
}

/** Notification-access state that re-checks on every ON_RESUME, so the "grant
 *  access" card dismisses as soon as the user returns from system Settings
 *  having granted it — a plain composition read of the setting would not. */
@Composable
private fun rememberNotificationAccess(context: android.content.Context): Boolean {
    val lifecycleOwner = LocalLifecycleOwner.current
    var granted by remember {
        mutableStateOf(ai.my.glasses.audio.MediaControl.hasNotificationAccess(context))
    }
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                granted = ai.my.glasses.audio.MediaControl.hasNotificationAccess(context)
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }
    return granted
}

private fun recoveryHint(f: Failure): String = when (f) {
    Failure.GLASSES_NOT_CONNECTED -> "Glasses not connected — open the Meta AI app and reconnect."
    Failure.GLASSES_PERMISSION_DENIED -> "Grant the camera permission in the Meta AI app."
    Failure.META_DEVELOPER_MODE_REQUIRED -> "Enable Developer Mode in the Meta AI app (Settings → App Info → tap version 5×), then register this app."
    Failure.BLUETOOTH_AUDIO_UNAVAILABLE -> "Glasses audio unavailable — check the Bluetooth connection."
    Failure.MYAI_HOST_UNREACHABLE -> "Can't reach your my.ai host — same Wi-Fi? Host running?"
    Failure.TLS_UNTRUSTED -> "Host TLS certificate mismatch — find the host again and re-approve."
    Failure.AUTHENTICATION_REQUIRED, Failure.DEVICE_CREDENTIAL_REVOKED ->
        "This device was revoked or expired — find the host again and re-approve."
    Failure.STT_UNAVAILABLE -> "Speech-to-text isn't available on the host right now."
    Failure.LLM_UNAVAILABLE -> "No model available on the host — is Ollama running?"
    Failure.VISION_MODEL_NOT_CONFIGURED -> "No local vision model configured on the host."
    Failure.TTS_UNAVAILABLE -> "Host speech synthesis is unavailable; showing text only."
    Failure.REQUEST_TIMEOUT -> "The host took too long — try again."
    Failure.SESSION_CANCELLED -> "Cancelled."
    Failure.UNSAFE_ACTION_BLOCKED -> "That action is blocked from the glasses channel."
    Failure.APPROVAL_REQUIRED -> "This action needs approval in the my.ai desktop UI."
    Failure.RATE_LIMITED -> "Slow down a moment — too many requests. Try again shortly."
    Failure.PAYLOAD_TOO_LARGE -> "That was too large to send — try a shorter request."
    Failure.BAD_REQUEST -> "The host couldn't read that request."
    Failure.SESSION_NOT_FOUND -> "That conversation expired — start a new one."
}
