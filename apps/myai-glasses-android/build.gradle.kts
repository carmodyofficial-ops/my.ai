// Toolchain pinned to what the Meta DAT SDK requires: its artifacts carry
// Kotlin 2.2 metadata (an older compiler refuses to read them) and pull in
// AndroidX/Compose versions that demand a recent AGP. These are the versions
// Meta's own CameraAccess sample uses. Needs Gradle 8.14+.
plugins {
    id("com.android.application") version "8.11.1" apply false
    id("org.jetbrains.kotlin.android") version "2.2.21" apply false
    id("org.jetbrains.kotlin.jvm") version "2.2.21" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.2.21" apply false
}
