package com.nexhaat.app.ui.components

import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Fingerprint
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.fragment.app.FragmentActivity
import com.nexhaat.app.R
import com.nexhaat.app.data.biometric.BiometricError
import com.nexhaat.app.data.biometric.BiometricPromptHelper

/**
 * Reusable BiometricPrompt composable in Kotlin that displays a fingerprint icon
 * or button to trigger the authentication flow implemented in the Android app.
 * Provides specific error handling (user cancellation, lockouts, no enrolled biometrics)
 * and fallback options.
 */
@Composable
fun BiometricPromptButton(
    biometricPromptHelper: BiometricPromptHelper,
    modifier: Modifier = Modifier,
    title: String? = null,
    subtitle: String? = null,
    buttonText: String = stringResource(R.string.biometric_sign_in),
    isCompact: Boolean = false,
    enabled: Boolean = true,
    onSuccess: () -> Unit,
    onError: (BiometricError) -> Unit = {},
    onFallbackPassword: (() -> Unit)? = null
) {
    val context = LocalContext.current
    val activity = context as? FragmentActivity
    var activeErrorDialog by remember { mutableStateOf<BiometricError?>(null) }

    fun triggerPrompt() {
        if (activity == null) {
            val error = BiometricError.Generic(-1, "Activity is not a FragmentActivity")
            onError(error)
            return
        }

        biometricPromptHelper.showBiometricPrompt(
            activity = activity,
            title = title ?: activity.getString(R.string.biometric_prompt_title),
            subtitle = subtitle ?: activity.getString(R.string.biometric_prompt_subtitle),
            description = activity.getString(R.string.biometric_prompt_description),
            negativeButtonText = activity.getString(R.string.cancel),
            onSuccess = onSuccess,
            onError = { biometricError ->
                when (biometricError) {
                    is BiometricError.UserCanceled -> {
                        // User dismissed or tapped negative button: silent, don't show intrusive dialog
                        onError(biometricError)
                    }
                    is BiometricError.TemporaryLockout,
                    is BiometricError.PermanentLockout,
                    is BiometricError.NoneEnrolled,
                    is BiometricError.HardwareUnavailable,
                    is BiometricError.EnrollmentChanged,
                    is BiometricError.SetupRequired,
                    is BiometricError.CryptoUnavailable -> {
                        // Critical error requiring fallback or settings
                        activeErrorDialog = biometricError
                        onError(biometricError)
                    }
                    is BiometricError.Generic -> {
                        activeErrorDialog = biometricError
                        onError(biometricError)
                    }
                }
            },
            onFailed = {
                val error = BiometricError.Generic(-2, context.getString(R.string.biometric_auth_failed))
                onError(error)
            }
        )
    }

    if (isCompact) {
        IconButton(
            onClick = ::triggerPrompt,
            modifier = modifier,
            enabled = enabled
        ) {
            Icon(
                imageVector = Icons.Default.Fingerprint,
                contentDescription = buttonText,
                tint = if (enabled) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    } else {
        OutlinedButton(
            onClick = ::triggerPrompt,
            modifier = modifier.fillMaxWidth(),
            enabled = enabled,
            shape = RoundedCornerShape(12.dp)
        ) {
            Icon(
                imageVector = Icons.Default.Fingerprint,
                contentDescription = null,
                modifier = Modifier.size(22.dp)
            )
            Spacer(Modifier.size(10.dp))
            Text(buttonText)
        }
    }

    // Specific error handling & fallback dialog
    activeErrorDialog?.let { error ->
        AlertDialog(
            onDismissRequest = { activeErrorDialog = null },
            icon = {
                Icon(
                    imageVector = Icons.Default.Lock,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary
                )
            },
            title = {
                Text(
                    text = when (error) {
                        is BiometricError.TemporaryLockout -> stringResource(R.string.biometric_lockout_title)
                        is BiometricError.PermanentLockout -> stringResource(R.string.biometric_permanent_lockout_title)
                        is BiometricError.NoneEnrolled -> stringResource(R.string.biometric_none_enrolled_title)
                        is BiometricError.HardwareUnavailable -> stringResource(R.string.biometric_hardware_unavailable_title)
                        else -> stringResource(R.string.biometric_error_title)
                    }
                )
            },
            text = {
                Text(
                    text = error.message,
                    style = MaterialTheme.typography.bodyMedium
                )
            },
            confirmButton = {
                when (error) {
                    is BiometricError.NoneEnrolled -> {
                        Button(
                            onClick = {
                                activeErrorDialog = null
                                biometricPromptHelper.openBiometricEnrollment(context)
                            }
                        ) {
                            Text(stringResource(R.string.open_settings))
                        }
                    }
                    else -> {
                        if (onFallbackPassword != null) {
                            Button(
                                onClick = {
                                    activeErrorDialog = null
                                    onFallbackPassword()
                                }
                            ) {
                                Text(stringResource(R.string.use_password))
                            }
                        } else {
                            Button(onClick = { activeErrorDialog = null }) {
                                Text(stringResource(android.R.string.ok))
                            }
                        }
                    }
                }
            },
            dismissButton = {
                TextButton(onClick = { activeErrorDialog = null }) {
                    Text(stringResource(R.string.cancel))
                }
            }
        )
    }
}
