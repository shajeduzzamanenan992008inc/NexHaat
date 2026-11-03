package com.nexhaat.app.ui.screens.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nexhaat.app.R
import com.nexhaat.app.data.biometric.BiometricAuthStatus
import com.nexhaat.app.data.biometric.BiometricPromptHelper
import com.nexhaat.app.ui.components.BiometricPromptButton
import com.nexhaat.app.ui.components.MarketplaceBottomBar
import com.nexhaat.app.ui.components.MarketplaceTopBar

@Composable
fun SettingsScreen(
    viewModel: SettingsViewModel = hiltViewModel(),
    biometricPromptHelper: BiometricPromptHelper = viewModel.biometricHelper,
    isLoggingOut: Boolean = false,
    onLogout: () -> Unit = {},
    onNavigateBack: () -> Unit,

    onNavigateToHome: () -> Unit,
    onNavigateToCategories: () -> Unit,
    onNavigateToSearch: () -> Unit,
    onNavigateToCart: () -> Unit,
    onNavigateToSecurityCenter: () -> Unit = {}
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(Unit) {
        viewModel.refreshState()
    }

    LaunchedEffect(uiState.userNotice) {
        uiState.userNotice?.let { notice ->
            snackbarHostState.showSnackbar(notice)
            viewModel.dismissNotice()
        }
    }

    Scaffold(
        topBar = {
            MarketplaceTopBar(
                onNavigateBack = onNavigateBack,
                onSearch = onNavigateToSearch,
                onCart = onNavigateToCart
            )
        },
        bottomBar = {
            MarketplaceBottomBar(
                selectedTab = null,
                onHome = onNavigateToHome,
                onCategories = onNavigateToCategories,
                onSearch = onNavigateToSearch,
                onCart = onNavigateToCart
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
        containerColor = MaterialTheme.colorScheme.background
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Header
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Security,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(28.dp)
                )
                Text(
                    text = stringResource(R.string.security_settings),
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold
                )
            }

            // 2FA Security Center Entry Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f)),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = stringResource(R.string.security_center),
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                        Spacer(Modifier.height(4.dp))
                        Text(
                            text = "Set up 2FA Authenticator, backup codes, and session defenses",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Button(
                        onClick = onNavigateToSecurityCenter,
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Text("Open")
                    }
                }
            }

            // Card 1: Device Sensor Status
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = stringResource(R.string.device_biometric_status),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(Modifier.height(6.dp))
                    Text(
                        text = when (uiState.biometricStatus) {
                            is BiometricAuthStatus.Ready -> stringResource(R.string.status_ready)
                            is BiometricAuthStatus.NoneEnrolled -> stringResource(R.string.status_none_enrolled)
                            is BiometricAuthStatus.HardwareUnavailable -> stringResource(R.string.status_hardware_unavailable)
                            is BiometricAuthStatus.NotAvailable -> stringResource(R.string.status_not_available)
                        },
                        style = MaterialTheme.typography.bodyMedium,
                        color = if (uiState.biometricStatus is BiometricAuthStatus.Ready) {
                            MaterialTheme.colorScheme.primary
                        } else {
                            MaterialTheme.colorScheme.error
                        }
                    )

                    if (uiState.biometricStatus is BiometricAuthStatus.NoneEnrolled) {
                        Spacer(Modifier.height(12.dp))
                        OutlinedButton(
                            onClick = { viewModel.openSystemBiometricSettings(context) },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Icon(Icons.Default.Settings, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(Modifier.size(8.dp))
                            Text(stringResource(R.string.setup_biometrics_in_settings))
                        }
                    }
                }
            }

            // Card 2: Biometric Sign-In Switch & Test
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f).padding(end = 12.dp)) {
                            Text(
                                text = stringResource(R.string.biometric_auth_title),
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.SemiBold
                            )
                            Text(
                                text = stringResource(R.string.biometric_auth_desc),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        Switch(
                            checked = uiState.isBiometricEnabled,
                            onCheckedChange = viewModel::setBiometricEnabled,
                            enabled = uiState.isAuthenticated &&
                                uiState.biometricStatus is BiometricAuthStatus.Ready
                        )
                    }

                    if (uiState.isBiometricEnabled && uiState.biometricStatus is BiometricAuthStatus.Ready) {
                        Spacer(Modifier.height(16.dp))
                        HorizontalDivider()
                        Spacer(Modifier.height(16.dp))
                        BiometricPromptButton(
                            biometricPromptHelper = biometricPromptHelper,
                            buttonText = stringResource(R.string.verify_active_session),
                            onSuccess = {
                                viewModel.revalidateBiometricSession()
                            },
                            onError = viewModel::onBiometricError
                        )
                    }
                }
            }

            if (uiState.isBiometricEnabled) {
                OutlinedButton(
                    onClick = viewModel::clearStoredBiometricData,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(Icons.Default.Delete, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.size(8.dp))
                    Text(stringResource(R.string.disable_biometric_unlock))
                }
            }
            if (uiState.isAuthenticated) {
                OutlinedButton(
                    onClick = onLogout,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    enabled = !isLoggingOut
                ) {
                    if (isLoggingOut) {
                        androidx.compose.material3.CircularProgressIndicator(
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(Modifier.size(8.dp))
                    }
                    Text(stringResource(R.string.sign_out))
                }
            }
        }
    }
}
