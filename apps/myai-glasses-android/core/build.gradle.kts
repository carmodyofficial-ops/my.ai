// Pure-JVM core: connection state machine, gateway client, SSE parser,
// pairing payload, wearables adapter interface + mock. No Android types —
// this module compiles and its tests run on any JVM (including the ARM
// Ubuntu host, where the Android SDK's x86_64-only aapt2 blocks :app).
plugins {
    id("org.jetbrains.kotlin.jvm")
}

kotlin { jvmToolchain(17) }

dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    // On Android the platform provides org.json; on the JVM we use the
    // standalone artifact. :app excludes it to avoid a duplicate-class clash.
    implementation("org.json:json:20240303")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.9.0")
}
