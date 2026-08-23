# ProGuard / R8 configuration for JARVIS Android Companion Client
-keepattributes *Annotation*
-keepattributes Signature
-keepattributes InnerClasses

# Kotlinx Serialization
-keepclassmembers class * {
    *** Companion;
}
-keepclasseswithmembers class * {
    kotlinx.serialization.KSerializer serializer(...);
}

# AndroidX Biometric
-keep class androidx.biometric.** { *; }
-keep class androidx.security.crypto.** { *; }
