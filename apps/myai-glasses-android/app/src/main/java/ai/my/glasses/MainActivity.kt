package ai.my.glasses

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts.RequestMultiplePermissions
import androidx.activity.viewModels
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.automirrored.rounded.Send
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.Build
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.Menu
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.rememberDrawerState
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
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
    var showDiag by remember { mutableStateOf(false) }

    ModalNavigationDrawer(
        drawerState = drawer,
        gesturesEnabled = ui.paired && !showDiag,   // history exists only once paired
        drawerContent = {
            HistoryDrawer(vm, ui,
                onDiagnostics = { showDiag = true; scope.launch { drawer.close() } },
                onClose = { scope.launch { drawer.close() } })
        },
    ) {
        if (showDiag) DiagnosticsScreen(vm, ui) { showDiag = false }
        // Pull down anywhere to re-probe host health/capabilities and re-poke
        // the glasses connection — the "why is Talk greyed out" recovery gesture.
        else PullToRefreshBox(
            isRefreshing = ui.refreshing,
            onRefresh = vm::refresh,
            // statusBarsPadding on the BOX (not just the inner column) so the app
            // draws edge-to-edge but the header AND the pull-to-refresh spinner both
            // clear the system clock/notifications.
            modifier = Modifier.fillMaxSize().statusBarsPadding(),
        ) {
            Column(
                // Extra top padding ON TOP of the status-bar inset (applied to the
                // box) so the brand header + hamburger sit well clear of the phone
                // clock/notifications, not just below them.
                Modifier.fillMaxSize().verticalScroll(rememberScrollState())
                    .padding(start = 20.dp, end = 20.dp, bottom = 28.dp, top = 40.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
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
private fun HistoryDrawer(vm: MainViewModel, ui: UiState,
                          onDiagnostics: () -> Unit, onClose: () -> Unit) {
    val ctx = LocalContext.current
    ModalDrawerSheet(
        drawerContainerColor = MaterialTheme.colorScheme.surface,
        modifier = Modifier.fillMaxWidth(0.84f),
    ) {
        Column(
            Modifier.fillMaxSize().statusBarsPadding()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 18.dp, vertical = 22.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Row(verticalAlignment = Alignment.Bottom,
                modifier = Modifier.padding(bottom = 10.dp)) {
                Text("my.ai", style = MaterialTheme.typography.titleLarge, color = MyAiBrand)
                Spacer(Modifier.width(6.dp))
                Text("GLASSES", style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(bottom = 2.dp))
            }

            Text("CONVERSATIONS", style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 6.dp, bottom = 2.dp))
            if (ui.chatHistory.isEmpty()) {
                Text("No conversations yet", style = MaterialTheme.typography.bodyMedium,
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

            Text("LOOK & ASK", style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 14.dp, bottom = 2.dp))
            if (ui.visionHistory.isEmpty()) {
                Text("Nothing captured yet", style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            ui.visionHistory.forEach { v ->
                DrawerRow(v.question.ifBlank { "What am I looking at?" }, v.answer)
            }

            Spacer(Modifier.height(16.dp))
            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
            Row(
                Modifier.fillMaxWidth().clip(MaterialTheme.shapes.small)
                    .clickable(onClick = onDiagnostics)
                    .padding(vertical = 12.dp, horizontal = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Icon(Icons.Rounded.Build, contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(20.dp))
                Column {
                    Text("Diagnostics", style = MaterialTheme.typography.bodyLarge)
                    Text("Validate glasses audio + gesture on hardware",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

/** "Look & Ask" control that distinguishes a tap (identify the main subject) from
 *  a long-press (freeze the frame, then speak a specific question). Material3's
 *  Button has no long-press hook, so this is a Surface styled to match a
 *  FilledTonalButton exactly, so it sits proportioned next to Talk. */
@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun LookAndAskButton(
    enabled: Boolean, onTap: () -> Unit, onLongPress: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val container = if (enabled) MaterialTheme.colorScheme.secondaryContainer
                    else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
    val content = if (enabled) MaterialTheme.colorScheme.onSecondaryContainer
                  else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f)
    // CircleShape (fully-rounded stadium) matches the adjacent Talk Button's
    // default Material3 shape, so the two 52dp buttons look identical. Clip BEFORE
    // combinedClickable so the press ripple stays inside the rounded corners.
    Surface(
        shape = CircleShape,
        color = container,
        modifier = modifier
            .clip(CircleShape)
            .combinedClickable(enabled = enabled, onClick = onTap, onLongClick = onLongPress),
    ) {
        Row(
            Modifier.heightIn(min = 52.dp).fillMaxWidth().padding(horizontal = 16.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("Look & Ask", style = MaterialTheme.typography.labelLarge, color = content,
                maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
    }
}

/** A rounded chat bubble; the tail corner flips for user (right) vs my.ai (left). */
@Composable
private fun ChatBubble(text: String, container: Color, content: Color, alignEnd: Boolean) {
    Surface(
        shape = RoundedCornerShape(
            topStart = 16.dp, topEnd = 16.dp,
            bottomStart = if (alignEnd) 16.dp else 5.dp,
            bottomEnd = if (alignEnd) 5.dp else 16.dp),
        color = container,
        modifier = Modifier.widthIn(max = 320.dp),
    ) {
        Text(text, style = MaterialTheme.typography.bodyLarge, color = content,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp))
    }
}

/** On-device hardware validation — the one screen that answers whether the glasses
 *  mic/speaker/camera and the media-button gesture actually work on real Ray-Bans. */
@Composable
private fun DiagnosticsScreen(vm: MainViewModel, ui: UiState, onBack: () -> Unit) {
    val clipboard = LocalClipboardManager.current
    // System Back should leave Diagnostics (return to Home), not the whole app.
    BackHandler { onBack() }
    LaunchedEffect(Unit) { vm.refreshDiagnostics() }
    val d = ui.diagnostics
    Column(
        Modifier.fillMaxSize().statusBarsPadding().verticalScroll(rememberScrollState())
            .padding(start = 20.dp, end = 20.dp, bottom = 20.dp, top = 24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            IconButton(onClick = onBack, modifier = Modifier.size(40.dp)) {
                Icon(Icons.AutoMirrored.Rounded.ArrowBack, contentDescription = "Back",
                    tint = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Text("Diagnostics", style = MaterialTheme.typography.titleLarge)
            Spacer(Modifier.weight(1f))
        }
        Text("On-device checks for the glasses audio + gesture.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant)

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(enabled = !d.running, onClick = vm::runAudioDiagnostic) {
                Text(if (d.running) "Testing…" else "Test mic + speaker")
            }
            OutlinedButton(enabled = !d.running, onClick = vm::refreshDiagnostics) { Text("Refresh") }
        }

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Report", style = MaterialTheme.typography.labelLarge)
                Text(d.report.ifBlank { "Tap 'Test mic + speaker' to run the audio check." },
                    style = MaterialTheme.typography.bodySmall, fontFamily = FontFamily.Monospace)
            }
        }

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Gesture events", style = MaterialTheme.typography.labelLarge)
                    Spacer(Modifier.weight(1f))
                    TextButton(onClick = vm::clearGestureLog) { Text("Clear") }
                }
                Text("Tap or hold the glasses button — raw media keys appear here.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (d.gestureLog.isEmpty()) {
                    Text("(none yet)", style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                } else d.gestureLog.forEach {
                    Text(it, style = MaterialTheme.typography.bodySmall,
                        fontFamily = FontFamily.Monospace)
                }
            }
        }

        OutlinedButton(onClick = {
            val text = "my.ai Glasses diagnostics\n\n${d.report}\n\nGesture events:\n" +
                d.gestureLog.joinToString("\n").ifBlank { "(none)" }
            clipboard.setText(AnnotatedString(text))
        }) { Text("Copy report") }
    }
}

@Composable
private fun DrawerRow(title: String, subtitle: String, onClick: (() -> Unit)? = null) {
    Column(
        Modifier
            .fillMaxWidth()
            .clip(MaterialTheme.shapes.small)
            .then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier)
            .padding(vertical = 7.dp, horizontal = 4.dp),
    ) {
        Text(title, style = MaterialTheme.typography.bodyLarge,
            maxLines = 1, overflow = TextOverflow.Ellipsis)
        Text(subtitle, style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 2, overflow = TextOverflow.Ellipsis)
    }
}

/** One checkable row (a note or task) in a home card. */
private data class ChecklistRow(
    val id: String, val label: String, val sub: String? = null, val done: Boolean = false,
    // Multi-item checklists (AI-created) are read-only on glasses — a whole-note
    // toggle would clobber their per-item state; manage them on the web.
    val checkable: Boolean = true,
)

/** A home card: a checklist of items — tap the box to complete a task, tap ✕ to
 *  remove any item — plus an inline quick-add. Notes and tasks both live here. */
@Composable
private fun ChecklistCard(
    title: String, items: List<ChecklistRow>, empty: String, hint: String,
    onCheck: (String) -> Unit,
    onAdd: (text: String) -> Unit,
    onDelete: (String) -> Unit,
    // Notes are reference text (no completion); tasks are checkable. Notes pass
    // false so no checkbox renders (completion for notes would collide with the
    // web app's Archive flag).
    showChecks: Boolean = true,
) {
    var draft by remember { mutableStateOf("") }
    val submit = {
        if (draft.isNotBlank()) { onAdd(draft); draft = "" }
    }

    SectionCard(spacing = 10.dp) {
        Row(verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, style = MaterialTheme.typography.titleLarge)
            if (items.isNotEmpty()) {
                Text("${items.size}", style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.clip(CircleShape)
                        .background(MaterialTheme.colorScheme.surfaceVariant)
                        .padding(horizontal = 8.dp, vertical = 2.dp))
            }
        }
        if (items.isEmpty()) {
            Text(empty, style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                items.take(8).forEach { row ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        // Tapping toggles done both ways — a completed task stays
                        // visible (greyed + struck through) and can be re-activated.
                        if (showChecks && row.checkable) {
                            Checkbox(checked = row.done, onCheckedChange = { onCheck(row.id) })
                        } else {
                            Spacer(Modifier.width(4.dp))
                        }
                        val labelColor = if (row.done)
                            MaterialTheme.colorScheme.onSurfaceVariant
                        else MaterialTheme.colorScheme.onSurface
                        val strike = if (row.done)
                            TextDecoration.LineThrough else null
                        Column(Modifier.weight(1f).padding(vertical = 6.dp)) {
                            Text(row.label, style = MaterialTheme.typography.bodyLarge,
                                color = labelColor, textDecoration = strike,
                                maxLines = 1, overflow = TextOverflow.Ellipsis)
                            row.sub?.let {
                                Text(it, style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                        // Remove this item entirely (hard delete on the host). Hidden
                        // for multi-item AI checklists (checkable=false): those are
                        // read-only on glasses, so a one-tap delete of the whole
                        // web/agent-managed note is too destructive — manage on web.
                        if (row.checkable) {
                            IconButton(onClick = { onDelete(row.id) },
                                modifier = Modifier.size(32.dp)) {
                                Icon(Icons.Rounded.Close, contentDescription = "Remove",
                                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                                    modifier = Modifier.size(18.dp))
                            }
                        }
                    }
                }
            }
        }
        OutlinedTextField(
            value = draft, onValueChange = { draft = it },
            label = { Text(hint) },
            singleLine = true,
            shape = MaterialTheme.shapes.large,
            modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
            keyboardActions = KeyboardActions(onDone = { submit() }),
            trailingIcon = {
                if (draft.isNotBlank()) {
                    IconButton(onClick = submit) {
                        Icon(Icons.Rounded.Add, contentDescription = "Add",
                            tint = MaterialTheme.colorScheme.secondary)
                    }
                }
            },
        )
    }
}

/** Reusable elevated card: one consistent shape, padding, and inner rhythm so
 *  every surface in the app reads the same. */
@Composable
private fun SectionCard(
    modifier: Modifier = Modifier,
    spacing: Dp = 12.dp,
    content: @Composable ColumnScope.() -> Unit,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.medium,
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Column(
            Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(spacing),
            content = content,
        )
    }
}

/** Small connection chip: a colored dot + state label. */
@Composable
private fun StatusPill(connected: Boolean) {
    val color = if (connected) MyAiConnected else MaterialTheme.colorScheme.onSurfaceVariant
    val bg = if (connected) MyAiConnected.copy(alpha = 0.15f)
             else MaterialTheme.colorScheme.surfaceVariant
    Row(
        Modifier.clip(CircleShape).background(bg).padding(horizontal = 11.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Box(Modifier.size(7.dp).clip(CircleShape).background(color))
        Text(if (connected) "Connected" else "Not linked",
            style = MaterialTheme.typography.labelMedium, color = color)
    }
}

/** my.ai wordmark + a live connection chip — the brand anchor on every screen. */
@Composable
private fun BrandHeader(connected: Boolean, onMenu: (() -> Unit)? = null) {
    Row(
        Modifier.fillMaxWidth().padding(bottom = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        onMenu?.let {
            IconButton(onClick = it, modifier = Modifier.size(40.dp)) {
                Icon(Icons.Rounded.Menu, contentDescription = "History",
                    tint = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Row(verticalAlignment = Alignment.Bottom) {
            Text("my.ai", style = MaterialTheme.typography.titleLarge, color = MyAiBrand)
            Spacer(Modifier.width(6.dp))
            Text("GLASSES", style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(bottom = 2.dp))
        }
        Spacer(Modifier.weight(1f))
        StatusPill(connected)
    }
}

/** A numbered step badge + title, for the setup flow. */
@Composable
private fun StepHeader(number: Int, title: String) {
    Row(verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Box(
            Modifier.size(26.dp).clip(CircleShape)
                .background(MaterialTheme.colorScheme.secondaryContainer),
            contentAlignment = Alignment.Center,
        ) {
            Text("$number", style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onSecondaryContainer)
        }
        Text(title, style = MaterialTheme.typography.titleMedium)
    }
}

/** First screen: both connection events, nothing else. */
@Composable
private fun SetupScreen(vm: MainViewModel, ui: UiState) {
    Text("Link your glasses and your my.ai host — then you're in.",
        style = MaterialTheme.typography.bodyLarge,
        color = MaterialTheme.colorScheme.onSurfaceVariant)

    SectionCard {
        StepHeader(1, "Glasses")
        StatusRow("Status", ui.glassesLabel)
        ui.glassesDetail?.let {
            Text("Glasses report: $it", style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.error)
        }
        Text("Pair the glasses in the Meta AI app (Bluetooth), then pull " +
            "down here to refresh. Voice also works with just the phone — " +
            "glasses can join later.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant)
    }

    // Host pairing: find the my.ai host on Wi-Fi and approve on the host. No
    // QR/JSON to copy. (A myai-glasses:// deep link from the host's browser
    // page still works too, routed through the confirm dialog — but there's no
    // in-app QR scan or JSON paste to fiddle with.)
    HostDiscoverySection(vm, ui)

    ui.failure?.let {
        Text(recoveryHint(it), style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.error)
    }
}

@Composable
private fun HostDiscoverySection(vm: MainViewModel, ui: UiState) {
    // While awaiting approval, show the verify code prominently.
    ui.enroll?.let { e ->
        SectionCard {
            StepHeader(2, "Approve on ${e.hostName}")
            if (e.verifyCode.isNotBlank()) {
                Text("VERIFICATION CODE",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text(e.verifyCode,
                    style = MaterialTheme.typography.displaySmall,
                    color = MyAiAccent)
            }
            Text(e.status, style = MaterialTheme.typography.bodyLarge)
            Text("On your my.ai host, open the pair-glasses page and approve this " +
                "device — confirm the code above matches.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
            OutlinedButton(onClick = vm::cancelEnroll) { Text("Cancel") }
        }
        return
    }

    SectionCard {
        StepHeader(2, "my.ai host")
        Text("Find your my.ai host on this Wi-Fi and approve this device on the " +
            "host — no code to copy.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant)
        Button(
            onClick = vm::discoverHosts,
            enabled = !ui.scanning,
            modifier = Modifier.fillMaxWidth().height(50.dp),
        ) { Text(if (ui.scanning) "Scanning…" else "Find my.ai host on Wi-Fi") }
        ui.discoveredHosts.forEach { h ->
            OutlinedButton(
                onClick = { vm.enrollWith(h) },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("${h.name} · ${h.host}:${h.port}${if (h.tls) " · TLS" else ""}") }
        }
        if (!ui.scanning && ui.discoveredHosts.isEmpty()) {
            Text("Tap to scan. Make sure the phone is on the same Wi-Fi as the host.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
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
/** A preference row: title + explanation on the left, a switch on the right. */
@Composable
private fun ToggleRow(title: String, subtitle: String,
                      checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.bodyLarge)
            Text(subtitle, style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Spacer(Modifier.width(12.dp))
        Switch(checked = checked, onCheckedChange = onChange)
    }
}

@Composable
private fun MainScreen(vm: MainViewModel, ui: UiState) {

    // ── Status + preferences ──────────────────────────────────────────────
    SectionCard(spacing = 10.dp) {
        StatusRow("Glasses", ui.glassesLabel)
        StatusRow("my.ai host", ui.hostLabel)
        StatusRow("Model", ui.modelLabel)
        StatusRow("Voice", ui.voiceLabel)
        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
        ToggleRow("Keep session context",
            if (ui.storeTranscript) "Follow-ups remembered in RAM this session"
            else "No storage — words aren't retained or logged",
            ui.storeTranscript, vm::setStoreTranscript)
        ToggleRow("Hands-free",
            if (ui.handsFree) "Auto-sends when you stop speaking"
            else "Tap Talk again to send",
            ui.handsFree, vm::setHandsFree)
        ui.failure?.let {
            Text(recoveryHint(it), style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.error)
        }
        ui.glassesDetail?.let {
            Text("Glasses report: $it", style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.error)
        }
    }

    // Glasses touchpad control needs Notification Access to drive the user's
    // music (single tap = play/pause). Prompt until granted — re-checked on
    // ON_RESUME so the card disappears the moment the user returns from Settings
    // having granted it (composition wouldn't otherwise re-read the setting).
    val mediaCtx = LocalContext.current
    if (!rememberNotificationAccess(mediaCtx)) {
        SectionCard(spacing = 10.dp) {
            Text("Enable glasses touchpad control", style = MaterialTheme.typography.titleMedium)
            Text("Grant Notification access so a single tap on the glasses plays/pauses " +
                "your music (a 3-second hold talks to my.ai).",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
            Button(onClick = {
                mediaCtx.startActivity(
                    Intent("android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS")
                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            }) { Text("Grant access") }
        }
    }

    // ── Assistant ─────────────────────────────────────────────────────────
    run {
        var draft by remember { mutableStateOf("") }
        // Text chat needs the host's chat model serving. If the host is up but
        // Ollama/the model isn't, the inputs are disabled and we show why + a
        // retry — a tap must not fail silently (UAT #2).
        val chatReady = ui.canTalk && ui.llmReady
        val send = {
            // Not while listening: starting a turn would leave the open mic
            // running (its later stopListening fires a second, overlapping turn).
            if (chatReady && draft.isNotBlank() && !ui.busy && !ui.listening) {
                vm.ask(draft); draft = ""
            }
        }
        if (ui.canTalk && !ui.llmReady) {
            SectionCard(spacing = 0.dp) {
                Row(Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically) {
                    Text("No model available on the host — is Ollama running?",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier.weight(1f))
                    OutlinedButton(enabled = !ui.refreshing, onClick = vm::refresh) {
                        Icon(Icons.Rounded.Refresh, null, Modifier.size(18.dp))
                        Spacer(Modifier.width(6.dp)); Text("Retry")
                    }
                }
            }
        }
        // Ask field with an inline Send affordance (its own button no longer
        // crowds a 3-button row).
        OutlinedTextField(
            value = draft, onValueChange = { draft = it },
            label = { Text("Ask my.ai") },
            enabled = chatReady,
            singleLine = true,
            shape = MaterialTheme.shapes.large,
            modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
            keyboardActions = KeyboardActions(onSend = { send() }),
            trailingIcon = {
                val canSend = chatReady && draft.isNotBlank() && !ui.busy && !ui.listening
                if (draft.isNotBlank()) {
                    IconButton(onClick = send, enabled = canSend) {
                        Icon(Icons.AutoMirrored.Rounded.Send, contentDescription = "Send",
                            tint = if (canSend) MaterialTheme.colorScheme.secondary
                                   else MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            },
        )
        // Primary voice actions — two equal, prominent buttons.
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            // Push-to-talk: hold to record, release to send. Needs STT AND the
            // chat model (the transcript is answered by it).
            Button(
                enabled = chatReady && ui.sttAvailable && !ui.busy,
                onClick = { if (ui.listening) vm.stopListening() else vm.startListening() },
                modifier = Modifier.weight(1f).height(52.dp),
            ) {
                Text(when {
                    ui.listening && ui.handsFree -> "Pause to send"
                    ui.listening -> "Tap to send"
                    else -> "Talk"
                }, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            LookAndAskButton(
                // Disabled while listening: a tap/long-press mid-listen would
                // start a look while the mic is still open (overlapping turns).
                enabled = ui.canTalk && ui.visionAvailable && !ui.busy && !ui.listening,
                onTap = vm::lookAndAsk,
                onLongPress = vm::lookAndAskSpoken,
                modifier = Modifier.weight(1f),
            )
        }
        if (ui.visionAvailable) {
            Text("Tap to identify · hold to ask about it",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        // Secondary actions — only when there's a turn in flight or to clear.
        if (ui.busy || ui.lastResponse.isNotBlank() || ui.lastQuestion.isNotBlank()) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (ui.busy) TextButton(onClick = vm::cancel) { Text("Stop") }
                Spacer(Modifier.weight(1f))
                TextButton(
                    enabled = !ui.busy,
                    onClick = { vm.newChat(); draft = "" },
                ) { Text("New chat") }
            }
        }

        // Response as chat bubbles (question + answer keep their context, UAT #4).
        if (ui.lastQuestion.isNotBlank() || ui.lastResponse.isNotBlank() || ui.busy) {
            Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                if (ui.lastQuestion.isNotBlank()) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                        ChatBubble(ui.lastQuestion,
                            MaterialTheme.colorScheme.secondaryContainer,
                            MaterialTheme.colorScheme.onSecondaryContainer, alignEnd = true)
                    }
                }
                Column {
                    Text("my.ai", style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.secondary,
                        modifier = Modifier.padding(start = 4.dp, bottom = 3.dp))
                    ChatBubble(ui.lastResponse.ifBlank { if (ui.busy) "…" else "—" },
                        MaterialTheme.colorScheme.surfaceVariant,
                        MaterialTheme.colorScheme.onSurface, alignEnd = false)
                }
            }
        }
    }

    // ── Productivity: live previews + quick-add against the my.ai host. ─────
    ChecklistCard(
        title = "Notes",
        items = ui.notes.map {
            ChecklistRow(it.id, it.title.ifBlank { it.snippet }.ifBlank { "(untitled)" })
        },
        empty = "No notes yet",
        hint = "Quick note",
        onCheck = {},                 // notes aren't completable
        onAdd = vm::addNote,
        onDelete = vm::deleteItem,
        showChecks = false,
    )
    ChecklistCard(
        title = "Tasks",
        items = ui.tasks.map { t ->
            // Single-item tasks are checkable; multi-item checklists show progress
            // (done/total) read-only.
            val sub = if (t.total > 1) "${t.done}/${t.total} done"
                      else t.dueDate?.take(10)?.let { "due $it" }
            ChecklistRow(t.id, t.title, sub, done = t.completed, checkable = t.total <= 1)
        },
        empty = "No tasks",
        hint = "Add a task",
        onCheck = vm::completeItem,
        onAdd = vm::addTask,
        onDelete = vm::deleteItem,
    )

    // ── Footer: subdued, destructive-adjacent actions. ─────────────────────
    Row(verticalAlignment = Alignment.CenterVertically) {
        // Disabled mid-turn: deleting the session out from under a running stream
        // left it running against a deleted session with busy stuck true (L2).
        TextButton(enabled = !ui.busy, onClick = vm::deleteConversation) {
            Text("Delete conversation",
                color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Spacer(Modifier.weight(1f))
        TextButton(onClick = vm::unpair) {
            Text("Unpair host", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun StatusRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(label, style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.width(12.dp))
        Text(value, style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface,
            textAlign = TextAlign.End, maxLines = 1, overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f))
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
