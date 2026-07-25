# NetClaw Mobile — R8 keep rules for the release build.
#
# Flutter's own engine rules come from the plugin; these cover the parts of
# this app that R8 cannot see are reachable, because they are entered from
# native code, reflection, or a Dart MethodChannel rather than from Java/Kotlin
# call sites.

# --- Flutter embedding -------------------------------------------------------
# FlutterFragmentActivity and the embedding are referenced from the manifest
# and from native, not from Kotlin.
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.** { *; }
-keep class io.flutter.embedding.** { *; }
-dontwarn io.flutter.embedding.**

# --- NCFED edge identity (feature 066) --------------------------------------
# MainActivity is named in AndroidManifest.xml and its MethodChannel handler is
# invoked from Dart; nothing in Kotlin calls it, so R8 would otherwise strip it.
-keep class ca.automateyournetwork.netclaw.mobile.MainActivity { *; }

# AndroidKeyStore keygen/signing goes through JCA provider lookup by string
# name ("AndroidKeyStore", "SHA256withECDSA"), which is reflection R8 can't
# trace. Keeping the spec classes avoids a release-only NoSuchAlgorithm/
# InvalidKeySpec failure that never reproduces in debug.
-keep class android.security.keystore.** { *; }
-dontwarn android.security.keystore.**

# --- Firebase / FCM ---------------------------------------------------------
# Push is dependency-present but config-incomplete (see PLAY-STORE-ROADMAP.md).
# These rules keep a release build from failing on missing Firebase internals
# whether or not push is finished before launch.
-keep class com.google.firebase.** { *; }
-dontwarn com.google.firebase.**
-dontwarn com.google.android.gms.**

# --- Kotlin metadata --------------------------------------------------------
-keepattributes *Annotation*
-keepattributes Signature
-keepattributes InnerClasses
-keepattributes EnclosingMethod
