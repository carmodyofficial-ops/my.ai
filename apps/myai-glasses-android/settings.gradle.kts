pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        // Meta Wearables Device Access Toolkit (needs a GitHub token with
        // read:packages in ~/.gradle/gradle.properties: gpr.user / gpr.token).
        // Only consulted when -PmetaSdk=true (see app/build.gradle.kts).
        maven {
            url = uri("https://maven.pkg.github.com/facebook/meta-wearables-dat-android")
            credentials {
                username = providers.gradleProperty("gpr.user").orNull ?: ""
                password = providers.gradleProperty("gpr.token").orNull ?: ""
            }
        }
    }
}

rootProject.name = "myai-glasses"
include(":core")
// :app needs the Android SDK; skip it when none is configured so the pure-JVM
// :core module (and its tests) still work on hosts without Android tooling.
val hasAndroidSdk = System.getenv("ANDROID_HOME") != null ||
    File(rootDir, "local.properties").let { it.exists() && it.readText().contains("sdk.dir") }
if (hasAndroidSdk) include(":app")
