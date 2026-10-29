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

    fun kotlinStringLiteral(value: String): String =
        "\"${value.replace("\\", "\\\\").replace("\"", "\\\"")}\""

    val releaseBaseUrl = envOrLocalProperty("NEXHAAT_RELEASE_BASE_URL", "\"https://RELEASE_BASE_URL_REPLACE_ME/\"")
    val debugBaseUrl = envOrLocalProperty("NEXHAAT_DEBUG_BASE_URL", "http://10.0.2.2:5000/")
    val debugMediaBaseUrl = envOrLocalProperty("NEXHAAT_MEDIA_BASE_URL", debugBaseUrl)
    val releaseMediaBaseUrl = envOrLocalProperty("NEXHAAT_MEDIA_BASE_URL", "https://RELEASE_BASE_URL_REPLACE_ME/")

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
            buildConfigField("String", "BASE_URL", kotlinStringLiteral(debugBaseUrl))
            buildConfigField("String", "MEDIA_BASE_URL", kotlinStringLiteral(debugMediaBaseUrl))
            buildConfigField("String", "RELEASE_BASE_URL", releaseBaseUrl)
        }
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            buildConfigField("String", "BASE_URL", releaseBaseUrl)
            buildConfigField("String", "MEDIA_BASE_URL", kotlinStringLiteral(releaseMediaBaseUrl))

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

    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")

    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
}
