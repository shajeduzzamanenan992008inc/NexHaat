package com.nexhaat.app.ui.screens.auth

import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Business
import androidx.compose.material.icons.filled.DirectionsBike
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
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
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nexhaat.app.R
import com.nexhaat.app.ui.components.MarketplaceTopBar

@Composable
fun SignUpScreen(
    viewModel: SignUpViewModel = hiltViewModel(),
    onNavigateBack: () -> Unit,
    onNavigateToSignIn: () -> Unit,
    onRegistrationSuccess: (email: String, challengeId: String?) -> Unit,
    onSignedIn: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    LaunchedEffect(uiState.challenge) {
        uiState.challenge?.let { challenge ->
            onRegistrationSuccess(uiState.email, challenge.challengeId)
        }
    }

    LaunchedEffect(uiState.signedInUser) {
        if (uiState.signedInUser != null) {
            onSignedIn()
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
                    .padding(horizontal = 24.dp, vertical = 16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Text(
                    text = stringResource(R.string.create_account),
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    text = stringResource(R.string.create_account_sub),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(Modifier.height(20.dp))

                // Role selection chips
                Text(
                    text = stringResource(R.string.role_label),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.align(Alignment.Start)
                )
                Spacer(Modifier.height(6.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    FilterChip(
                        selected = uiState.role == "customer",
                        onClick = { viewModel.setRole("customer") },
                        label = { Text(stringResource(R.string.role_customer)) },
                        leadingIcon = { Icon(Icons.Default.Person, contentDescription = null, modifier = Modifier.size(16.dp)) },
                        modifier = Modifier.weight(1f)
                    )
                    FilterChip(
                        selected = uiState.role == "seller",
                        onClick = { viewModel.setRole("seller") },
                        label = { Text(stringResource(R.string.role_seller)) },
                        leadingIcon = { Icon(Icons.Default.Business, contentDescription = null, modifier = Modifier.size(16.dp)) },
                        modifier = Modifier.weight(1f)
                    )
                }

                Spacer(Modifier.height(14.dp))

                OutlinedTextField(
                    value = uiState.fullName,
                    onValueChange = viewModel::setFullName,
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("signup_fullname"),
                    label = { Text(stringResource(R.string.full_name)) },
                    singleLine = true,
                    enabled = !uiState.isLoading,
                    shape = RoundedCornerShape(12.dp)
                )

                Spacer(Modifier.height(12.dp))

                OutlinedTextField(
                    value = uiState.email,
                    onValueChange = viewModel::setEmail,
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("signup_email"),
                    label = { Text(stringResource(R.string.email)) },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                    singleLine = true,
                    enabled = !uiState.isLoading,
                    shape = RoundedCornerShape(12.dp)
                )

                Spacer(Modifier.height(12.dp))

                OutlinedTextField(
                    value = uiState.phone,
                    onValueChange = viewModel::setPhone,
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("signup_phone"),
                    label = { Text(stringResource(R.string.phone_number)) },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                    singleLine = true,
                    enabled = !uiState.isLoading,
                    shape = RoundedCornerShape(12.dp)
                )

                Spacer(Modifier.height(12.dp))

                OutlinedTextField(
                    value = uiState.password,
                    onValueChange = viewModel::setPassword,
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("signup_password"),
                    label = { Text(stringResource(R.string.password)) },
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
                        .testTag("signup_confirm_password"),
                    label = { Text(stringResource(R.string.confirm_password)) },
                    visualTransformation = PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                    singleLine = true,
                    enabled = !uiState.isLoading,
                    shape = RoundedCornerShape(12.dp)
                )

                uiState.error?.let { error ->
                    Spacer(Modifier.height(12.dp))
                    Text(
                        text = error,
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodyMedium
                    )
                }

                Spacer(Modifier.height(20.dp))

                Button(
                    onClick = viewModel::register,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(50.dp)
                        .testTag("signup_submit_button"),
                    enabled = !uiState.isLoading,
                    shape = RoundedCornerShape(12.dp)
                ) {
                    if (uiState.isLoading) {
                        CircularProgressIndicator(modifier = Modifier.size(22.dp), strokeWidth = 2.dp)
                    } else {
                        Text(stringResource(R.string.sign_up), style = MaterialTheme.typography.titleMedium)
                    }
                }

                Spacer(Modifier.height(16.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    HorizontalDivider(modifier = Modifier.weight(1f))
                    Text(
                        text = " " + stringResource(R.string.or_continue_with) + " ",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    HorizontalDivider(modifier = Modifier.weight(1f))
                }

                Spacer(Modifier.height(14.dp))

                // Social sign-in buttons
                OutlinedButton(
                    onClick = {
                        viewModel.socialLogin(
                            provider = "google",
                            token = "google_auth_token_mock",
                            email = uiState.email.ifBlank { "google_user@nexhaat.com" },
                            name = uiState.fullName.ifBlank { "Google User" }
                        )
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(46.dp)
                        .testTag("google_login_button"),
                    shape = RoundedCornerShape(12.dp),
                    enabled = !uiState.isLoading
                ) {
                    Text(stringResource(R.string.continue_with_google))
                }

                Spacer(Modifier.height(8.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedButton(
                        onClick = {
                            viewModel.socialLogin(
                                provider = "microsoft",
                                token = "ms_auth_token_mock",
                                email = uiState.email.ifBlank { "ms_user@nexhaat.com" },
                                name = uiState.fullName.ifBlank { "Microsoft User" }
                            )
                        },
                        modifier = Modifier
                            .weight(1f)
                            .height(46.dp)
                            .testTag("microsoft_login_button"),
                        shape = RoundedCornerShape(12.dp),
                        enabled = !uiState.isLoading
                    ) {
                        Text("Microsoft")
                    }

                    OutlinedButton(
                        onClick = {
                            viewModel.socialLogin(
                                provider = "github",
                                token = "github_auth_token_mock",
                                email = uiState.email.ifBlank { "github_user@nexhaat.com" },
                                name = uiState.fullName.ifBlank { "GitHub User" }
                            )
                        },
                        modifier = Modifier
                            .weight(1f)
                            .height(46.dp)
                            .testTag("github_login_button"),
                        shape = RoundedCornerShape(12.dp),
                        enabled = !uiState.isLoading
                    ) {
                        Text("GitHub")
                    }
                }

                Spacer(Modifier.height(18.dp))

                TextButton(
                    onClick = onNavigateToSignIn,
                    modifier = Modifier.testTag("signup_login_link")
                ) {
                    Text(
                        text = stringResource(R.string.already_have_account),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }
        }
    }
}
