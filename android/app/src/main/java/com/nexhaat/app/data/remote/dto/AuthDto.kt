package com.nexhaat.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

@Serializable
data class CsrfTokenDto(
    @SerialName("csrf_token")
    val csrfToken: String
)

@Serializable
data class LoginRequestDto(
    val email: String,
    val password: String
)

@Serializable
data class RegisterRequestDto(
    val role: String = "customer",
    val email: String,
    @SerialName("full_name")
    val fullName: String,
    val phone: String,
    val password: String,
    @SerialName("store_name")
    val storeName: String? = null,
    @SerialName("business_address")
    val businessAddress: String? = null
)

@Serializable
data class RegistrationChallengeDto(
    val email: String,
    @SerialName("expires_at")
    val expiresAt: String? = null
)

@Serializable
data class VerifyRegistrationRequestDto(
    val code: String
)

@Serializable
data class ForgotPasswordRequestDto(
    val email: String
)

@Serializable
data class ResetPasswordRequestDto(
    val email: String,
    val code: String,
    @SerialName("new_password")
    val newPassword: String
)

@Serializable
data class SocialLoginRequestDto(
    val provider: String,
    val token: String,
    val email: String? = null,
    val name: String? = null
)

@Serializable
data class TotpSetupDto(
    val secret: String,
    @SerialName("provisioning_uri")
    val provisioningUri: String,
    @SerialName("backup_codes")
    val backupCodes: List<String> = emptyList()
)

@Serializable
data class TotpVerifyRequestDto(
    val code: String
)

@Serializable
data class UserDto(
    val id: Int,
    val email: String,
    val role: String,
    @SerialName("is_active")
    val isActive: Boolean = true,
    @SerialName("preferred_locale")
    val preferredLocale: String? = null,
    @SerialName("is_totp_enabled")
    val isTotpEnabled: Boolean = false
)

@Serializable
data class ApiMessageDto(
    val message: String? = null,
    val data: JsonElement? = null
)
