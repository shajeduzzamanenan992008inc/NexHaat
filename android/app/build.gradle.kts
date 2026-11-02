import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("com.google.dagger.hilt.android")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("kotlin-kapt")
}

android {
    namespace = "com.nexhaat.app"
    compileSdk = 36

    val localPropertiesFile = rootProject.layout.projectDirectory.file("local.properties").asFile
    val localProperties = Properties()
    if (localPropertiesFile.exists()) {
        localPropertiesFile.inputStream().use { localProperties.load(it) }
    }

    fun envOrLocalProperty(name: String, default: String = ""): String {
        return System.getenv(name)
            ?: localProperties.getProperty(name)
            ?: default
    }

    fun isPropertyExplicitlySet(name: String): Boolean {
        if (System.getenv(name) != null) return true
        if (localProperties.containsKey(name)) return true
        return false
    }

    fun readPropertyRaw(name: String): String? {
        val env = System.getenv(name)
        if (env != null) return env
        if (localProperties.containsKey(name)) {
            return localProperties.getProperty(name)
        }
        return null
    }

    fun isKnownMediaPlaceholder(value: String?): Boolean {
        if (value.isNullOrBlank()) return false
        val trimmed = value.trim()
        val lower = trimmed.lowercase()
        return lower.contains("release_base_url_replace_me") ||
            lower.contains("replace_me") && lower.contains("media")
    }

    fun effectiveDebugMediaRaw(): String? {
        val explicit = readPropertyRaw("NEXHAAT_MEDIA_BASE_URL")
        if (explicit != null && explicit.isNotBlank() && !isKnownMediaPlaceholder(explicit)) {
            return explicit
        }
        return null
    }

    fun effectiveReleaseMediaRaw(): String? {
        val explicit = readPropertyRaw("NEXHAAT_MEDIA_BASE_URL")
        if (explicit == null || explicit.isNotBlank().not()) return null
        return if (!isKnownMediaPlaceholder(explicit)) explicit else null
    }

    fun kotlinStringLiteral(value: String): String =
        "\"${value.replace("\\", "\\\\").replace("\"", "\\\"")}\""

    fun normalizedBaseUrl(value: String): String = value.trim().trim('"').trim()

    val releaseBaseUrlValue = normalizedBaseUrl(
        envOrLocalProperty("NEXHAAT_RELEASE_BASE_URL", "https://RELEASE_BASE_URL_REPLACE_ME/")
    )
    val debugBaseUrlValue = normalizedBaseUrl(
        envOrLocalProperty("NEXHAAT_DEBUG_BASE_URL", "http://10.0.2.2:5000/")
    )

    // Media configuration. A debug build may serve media from the local API host;
    // a release build must never trust a placeholder media base.
    val debugMediaExplicitRaw = effectiveDebugMediaRaw()
    val debugMediaBaseUrl = normalizedBaseUrl(debugMediaExplicitRaw ?: debugBaseUrlValue)
    val debugMediaResolved = debugMediaBaseUrl.isNotBlank() && !isKnownMediaPlaceholder(debugMediaBaseUrl)
    val debugMediaBaseUrlLiteral = if (debugMediaResolved) kotlinStringLiteral(debugMediaBaseUrl) else "\"\""

    val releaseMediaExplicitRaw = effectiveReleaseMediaRaw()
    val releaseMediaExplicitlyValid = releaseMediaExplicitRaw != null
    val releaseMediaBaseUrl = releaseMediaExplicitRaw ?: ""
    val releaseMediaResolved = releaseMediaExplicitlyValid
    val releaseMediaBaseUrlLiteral = if (releaseMediaExplicitlyValid) kotlinStringLiteral(releaseMediaBaseUrl.trim()) else "\"\""

    val releaseMediaBuildBlocked = !releaseMediaExplicitlyValid

    defaultConfig {
        applicationId = "com.nexhaat.app"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables {
            useSupportLibrary = true
        }
    }

    buildTypes {
        debug {
            buildConfigField("String", "BASE_URL", kotlinStringLiteral(debugBaseUrlValue))
            buildConfigField("String", "MEDIA_BASE_URL", debugMediaBaseUrlLiteral)
            buildConfigField("String", "RELEASE_BASE_URL", kotlinStringLiteral(releaseBaseUrlValue))
            buildConfigField("String", "MEDIA_BASE_URL_RESOLVED", kotlinStringLiteral(debugMediaResolved.toString()))
            buildConfigField("String", "MEDIA_BASE_URL_RUNTIME_FALLBACK", "\"https://RELEASE_BASE_URL_REPLACE_ME/media/\"")
        }

        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            buildConfigField("String", "BASE_URL", kotlinStringLiteral(releaseBaseUrlValue))
            buildConfigField("String", "MEDIA_BASE_URL", releaseMediaBaseUrlLiteral)
            buildConfigField("String", "MEDIA_BASE_URL_RESOLVED", kotlinStringLiteral(releaseMediaResolved.toString()))
            buildConfigField("String", "MEDIA_BASE_URL_RUNTIME_FALLBACK", "\"https://RELEASE_BASE_URL_REPLACE_ME/media/\"")

            val keystorePathValue = envOrLocalProperty("NEXHAAT_KEYSTORE_PATH")
            val storePasswordValue = envOrLocalProperty("NEXHAAT_KEYSTORE_STORE_PASSWORD")
            val keyAliasValue = envOrLocalProperty("NEXHAAT_KEYSTORE_KEY_ALIAS")
            val keyPasswordValue = envOrLocalProperty("NEXHAAT_KEYSTORE_KEY_PASSWORD")

            if (keystorePathValue.isNotBlank() &&
                storePasswordValue.isNotBlank() &&
                keyAliasValue.isNotBlank() &&
                keyPasswordValue.isNotBlank()
            ) {
                signingConfigs {
                    create("release") {
                        storeFile = file(keystorePathValue)
                        storePassword = storePasswordValue
                        keyAlias = keyAliasValue
                        keyPassword = keyPasswordValue
                    }
                }
                signingConfig = signingConfigs.getByName("release")
            } else {
                logger.lifecycle(
                    "Release signing credentials not configured. Release build will be unsigned. " +
                    "Set NEXHAAT_KEYSTORE_PATH, NEXHAAT_KEYSTORE_STORE_PASSWORD, " +
                    "NEXHAAT_KEYSTORE_KEY_ALIAS, and NEXHAAT_KEYSTORE_KEY_PASSWORD, or add them to android/local.properties."
                )
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.09.02")
    implementation(composeBom)
    androidTestImplementation(composeBom)

    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.6")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")

    // Navigation
    implementation("androidx.navigation:navigation-compose:2.8.2")

    // Hilt
    implementation("com.google.dagger:hilt-android:2.57.2")
    kapt("com.google.dagger:hilt-android-compiler:2.57.2")
    implementation("androidx.hilt:hilt-navigation-compose:1.2.0")

    // Networking
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-kotlinx-serialization:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")

    // Image loading
    implementation("io.coil-kt:coil-compose:2.7.0")

    // Paging
    implementation("androidx.paging:paging-runtime-ktx:3.3.2")
    implementation("androidx.paging:paging-compose:3.3.2")

    // DataStore
    implementation("androidx.datastore:datastore-preferences:1.1.1")

    // Biometric Authentication
    implementation("androidx.biometric:biometric:1.2.0-alpha05")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")


    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")

    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
}
