package com.nexhaat.app.ui.screens.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nexhaat.app.R
import com.nexhaat.app.ui.components.MarketplaceTopBar

@Composable
fun ForgotPasswordScreen(
    viewModel: ForgotPasswordViewModel = hiltViewModel(),
    onNavigateBack: () -> Unit,
    onPasswordResetSuccess: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    LaunchedEffect(uiState.isResetSuccessful) {
        if (uiState.isResetSuccessful) {
            onPasswordResetSuccess()
        }
    }

    Scaffold(
        topBar = { MarketplaceTopBar(onNavigateBack = onNavigateBack) },
        containerColor = MaterialTheme.colorScheme.background
    ) { padding ->
        BoxWithConstraints(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .imePadding()
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = maxHeight)
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Text(
                    text = stringResource(R.string.forgot_password_title),
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    text = stringResource(R.string.forgot_password_sub),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center
                )

                Spacer(Modifier.height(24.dp))

                OutlinedTextField(
                    value = uiState.email,
                    onValueChange = viewModel::setEmail,
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("forgot_password_email"),
                    label = { Text(stringResource(R.string.email)) },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                    singleLine = true,
                    enabled = !uiState.isLoading && !uiState.codeSent,
                    shape = RoundedCornerShape(12.dp)
                )

                if (!uiState.codeSent) {
                    Spacer(Modifier.height(20.dp))
                    Button(
                        onClick = viewModel::requestResetCode,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(50.dp)
                            .testTag("send_reset_code_button"),
                        enabled = !uiState.isLoading && uiState.email.isNotBlank(),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        if (uiState.isLoading) {
                            CircularProgressIndicator(modifier = Modifier.size(22.dp), strokeWidth = 2.dp)
                        } else {
                            Text(stringResource(R.string.send_reset_code))
                        }
                    }
                } else {
                    Spacer(Modifier.height(14.dp))

                    OutlinedTextField(
                        value = uiState.code,
                        onValueChange = viewModel::setCode,
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("reset_password_code"),
                        label = { Text(stringResource(R.string.verification_code)) },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                        singleLine = true,
                        enabled = !uiState.isLoading,
                        shape = RoundedCornerShape(12.dp)
                    )

                    Spacer(Modifier.height(12.dp))

                    OutlinedTextField(
                        value = uiState.newPassword,
                        onValueChange = viewModel::setNewPassword,
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("reset_password_new"),
                        label = { Text(stringResource(R.string.new_password)) },
                        visualTransformation = PasswordVisualTransformation(),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                        singleLine = true,
                        enabled = !uiState.isLoading,
                        shape = RoundedCornerShape(12.dp)
                    )

                    Spacer(Modifier.height(12.dp))

                    OutlinedTextField(
                        value = uiState.confirmPassword,
                        onValueChange = viewModel::setConfirmPassword,
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("reset_password_confirm"),
                        label = { Text(stringResource(R.string.confirm_password)) },
                        visualTransformation = PasswordVisualTransformation(),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                        singleLine = true,
                        enabled = !uiState.isLoading,
                        shape = RoundedCornerShape(12.dp)
                    )

                    Spacer(Modifier.height(20.dp))

                    Button(
                        onClick = viewModel::resetPassword,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(50.dp)
                            .testTag("submit_new_password_button"),
                        enabled = !uiState.isLoading && uiState.code.length == 6,
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        if (uiState.isLoading) {
                            CircularProgressIndicator(modifier = Modifier.size(22.dp), strokeWidth = 2.dp)
                        } else {
                            Text(stringResource(R.string.set_new_password))
                        }
                    }
                }

                uiState.error?.let { error ->
                    Spacer(Modifier.height(14.dp))
                    Text(
                        text = error,
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodyMedium,
                        textAlign = TextAlign.Center
                    )
                }

                uiState.successMessage?.let { msg ->
                    Spacer(Modifier.height(14.dp))
                    Text(
                        text = msg,
                        color = MaterialTheme.colorScheme.primary,
                        style = MaterialTheme.typography.bodyMedium,
                        textAlign = TextAlign.Center
                    )
                }

                Spacer(Modifier.height(20.dp))

                TextButton(onClick = onNavigateBack) {
                    Text(stringResource(R.string.already_have_account))
                }
            }
        }
    }
}
