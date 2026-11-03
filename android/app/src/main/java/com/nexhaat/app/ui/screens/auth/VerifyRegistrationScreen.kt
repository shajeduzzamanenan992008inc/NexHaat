package com.nexhaat.app.ui.screens.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
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
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nexhaat.app.R
import com.nexhaat.app.ui.components.MarketplaceTopBar

@Composable
fun VerifyRegistrationScreen(
    email: String,
    challengeId: String? = null,
    viewModel: VerifyRegistrationViewModel = hiltViewModel(),
    onNavigateBack: () -> Unit,
    onVerified: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    LaunchedEffect(email, challengeId) {
        viewModel.initData(email, challengeId)
    }

    LaunchedEffect(uiState.isVerified) {
        if (uiState.isVerified) {
            onVerified()
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
                    text = stringResource(R.string.verify_account),
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    text = stringResource(R.string.verify_account_sub, email),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center
                )

                Spacer(Modifier.height(32.dp))

                OutlinedTextField(
                    value = uiState.code,
                    onValueChange = viewModel::setCode,
                    modifier = Modifier
                        .fillMaxWidth(0.85f)
                        .testTag("otp_input_field"),
                    label = { Text(stringResource(R.string.enter_verification_code)) },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                    singleLine = true,
                    enabled = !uiState.isLoading,
                    shape = RoundedCornerShape(14.dp),
                    textStyle = MaterialTheme.typography.headlineMedium.copy(
                        textAlign = TextAlign.Center,
                        letterSpacing = 8.sp,
                        fontWeight = FontWeight.Bold
                    )
                )

                uiState.error?.let { error ->
                    Spacer(Modifier.height(14.dp))
                    Text(
                        text = error,
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodyMedium,
                        textAlign = TextAlign.Center
                    )
                }

                Spacer(Modifier.height(28.dp))

                Button(
                    onClick = { viewModel.verifyCode() },
                    modifier = Modifier
                        .fillMaxWidth(0.85f)
                        .height(50.dp)
                        .testTag("verify_otp_button"),
                    enabled = !uiState.isLoading && uiState.code.length == 6,
                    shape = RoundedCornerShape(12.dp)
                ) {
                    if (uiState.isLoading) {
                        CircularProgressIndicator(modifier = Modifier.size(22.dp), strokeWidth = 2.dp)
                    } else {
                        Text(stringResource(R.string.verify_code), style = MaterialTheme.typography.titleMedium)
                    }
                }

                Spacer(Modifier.height(20.dp))

                if (uiState.resendCountdown > 0) {
                    Text(
                        text = stringResource(R.string.resend_code_in, uiState.resendCountdown),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else {
                    TextButton(
                        onClick = viewModel::resendCode,
                        modifier = Modifier.testTag("resend_otp_button")
                    ) {
                        Text(
                            text = stringResource(R.string.resend_code),
                            style = MaterialTheme.typography.labelLarge,
                            color = MaterialTheme.colorScheme.primary,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                }
            }
        }
    }
}
