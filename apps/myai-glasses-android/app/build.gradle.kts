plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

// Build without the Meta SDK by default (mock adapter only) so the project
// compiles with no GitHub Packages credentials. Real-glasses builds:
//   ./gradlew assembleDebug -PmetaSdk=true
// which adds the `metadat` source set containing MetaDatAdapter.
val metaSdkEnabled = (findProperty("metaSdk") as String?)?.toBoolean() ?: false

// Meta app identity comes from git-ignored local.properties (metaAppId=…,
// metaClientToken=…) so credentials never enter source control. Empty values
// keep mock builds working; the real-glasses build fails fast if unset.
val localProps: Map<String, String> = rootProject.file("local.properties")
    .takeIf { it.exists() }?.readLines()
    ?.filterNot { it.trimStart().startsWith("#") }
    ?.mapNotNull { line -> line.split("=", limit = 2).takeIf { it.size == 2 } }
    ?.associate { it[0].trim() to it[1].trim() }
    ?: emptyMap()
val metaAppId = localProps["metaAppId"] ?: ""
val metaClientToken = localProps["metaClientToken"] ?: ""
if (metaSdkEnabled && (metaAppId.isBlank() || metaClientToken.isBlank())) {
    throw GradleException(
        "metaSdk build needs metaAppId + metaClientToken in local.properties " +
        "(from the Meta Wearables Developer Center)")
}

android {
    namespace = "ai.my.glasses"
    compileSdk = 36

    defaultConfig {
        applicationId = "ai.my.glasses"
        minSdk = 31 // AudioManager.setCommunicationDevice (BT HFP mic routing)
        targetSdk = 36
        versionCode = 43
        versionName = "0.9.6"
        buildConfigField("boolean", "META_SDK", metaSdkEnabled.toString())
        manifestPlaceholders["metaAppId"] = metaAppId
        manifestPlaceholders["metaClientToken"] = metaClientToken
        // Ship only the arm64 native libs. The Meta SDK bundles x86/x86_64/armv7
        // too (~24MB dead weight); every real Ray-Ban-companion phone is arm64,
        // and dropping the rest keeps the sideload small enough to survive a
        // flaky Wi-Fi transfer. (Mock builds carry no native libs regardless.)
        ndk { abiFilters += "arm64-v8a" }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    sourceSets {
        if (metaSdkEnabled) {
            getByName("main").java.srcDir("src/metadat/java")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                // Keeps the reflectively-loaded Meta SDK classes; without it a
                // minified metaSdk build silently falls back to the mock adapter.
                "proguard-rules.pro",
            )
        }
    }
}

dependencies {
    implementation(project(":core")) {
        // Android provides org.json natively; the JVM artifact would clash.
        exclude(group = "org.json", module = "json")
    }
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation(platform("androidx.compose:compose-bom:2025.09.00"))
    implementation("androidx.compose.material3:material3")
    // Curated core icon set only (~40 common icons) — NOT material-icons-extended,
    // which bundles thousands and bloats the APK ~30 MB (breaks flaky-Wi-Fi installs).
    implementation("androidx.compose.material:material-icons-core")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.6")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.6")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")

    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
    // Pairing-QR scanner (offline, no Play Services dependency).
    implementation("com.journeyapps:zxing-android-embedded:4.3.0")

    if (metaSdkEnabled) {
        val datVersion = "0.8.0"
        implementation("com.meta.wearable:mwdat-core:$datVersion")
        implementation("com.meta.wearable:mwdat-camera:$datVersion")
        debugImplementation("com.meta.wearable:mwdat-mockdevice:$datVersion")
    }

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.9.0")
}
