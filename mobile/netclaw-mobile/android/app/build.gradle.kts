import java.util.Properties

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// FCM push notifications. The Google Services plugin ABORTS the build outright
// when google-services.json is absent, and that file is per-operator config
// that must never be committed (it carries the project's own sender ID and API
// key) — so apply the plugin only when the operator has actually dropped it in.
// Same conditional shape as the release-signing block below, and the same
// intent: a fresh clone with no credentials still builds.
val googleServicesJson = file("google-services.json")
if (googleServicesJson.exists()) {
    apply(plugin = "com.google.gms.google-services")
} else {
    logger.lifecycle(
        "NetClaw: android/app/google-services.json not found — building WITHOUT " +
            "FCM. Push registration will fail at runtime and the app will run " +
            "normally without notifications. See README.md \"Push notifications\"."
    )
}

// Release signing material lives outside git (android/.gitignore covers
// key.properties, *.jks and *.keystore). When it is absent — CI, a fresh
// clone, or anyone who only needs a debug build — the release build type
// falls back to the debug key so `flutter run --release` still works, but
// the resulting artifact is one Play will reject. See PLAY-STORE-ROADMAP.md
// phase 2.
val keystoreProperties = Properties().apply {
    val f = rootProject.file("key.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}
val hasReleaseKeystore = keystoreProperties.getProperty("storeFile") != null

android {
    namespace = "ca.automateyournetwork.netclaw.mobile"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
        // Required by flutter_local_notifications (spec 073): it uses
        // java.time APIs that do not exist below API 26, so the build fails
        // outright without desugaring —
        // "Dependency ':flutter_local_notifications' requires core library
        // desugaring to be enabled for :app". Not optional and not a warning:
        // every Android build, debug and release, fails until this is set.
        isCoreLibraryDesugaringEnabled = true
    }

    defaultConfig {
        // Permanent once published to Play — do not change. See PLAY-STORE-ROADMAP.md.
        applicationId = "ca.automateyournetwork.netclaw.mobile"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    signingConfigs {
        if (hasReleaseKeystore) {
            create("release") {
                keyAlias = keystoreProperties.getProperty("keyAlias")
                keyPassword = keystoreProperties.getProperty("keyPassword")
                storeFile = rootProject.file(keystoreProperties.getProperty("storeFile"))
                storePassword = keystoreProperties.getProperty("storePassword")
            }
        }
    }

    buildTypes {
        release {
            signingConfig = if (hasReleaseKeystore) {
                signingConfigs.getByName("release")
            } else {
                logger.warn(
                    "NetClaw: android/key.properties not found — signing the release " +
                        "build with the DEBUG key. This artifact cannot be uploaded to Play."
                )
                signingConfigs.getByName("debug")
            }
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}

dependencies {
    // Pairs with isCoreLibraryDesugaringEnabled above. Version pinned to the
    // one flutter_local_notifications' own setup documentation specifies for
    // the 19+ line, rather than tracking latest — the desugaring library is
    // coupled to AGP, and a mismatch fails the build in a much less obvious
    // place than the flag being absent does.
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")
}
