package com.nexhaat.app.ui.screens.checkout

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CreditCard
import androidx.compose.material.icons.filled.LocalAtm
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Tag
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nexhaat.app.R
import com.nexhaat.app.ui.components.ErrorState
import com.nexhaat.app.ui.components.LoadingState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CheckoutScreen(
    viewModel: CheckoutViewModel = hiltViewModel(),
    onNavigateBack: () -> Unit,
    onOrderPlaced: (String) -> Unit
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val context = LocalContext.current

    var customerName by remember { mutableStateOf("Enan Shajed") }
    var phone by remember { mutableStateOf("01712345678") }
    var address by remember { mutableStateOf("House 12, Road 4, Dhanmondi") }
    var city by remember { mutableStateOf("Dhaka") }
    var paymentMethod by remember { mutableStateOf("cod") }
    var promoCode by remember { mutableStateOf("") }

    LaunchedEffect(uiState) {
        val state = uiState
        if (state is CheckoutUiState.Completed) {
            onOrderPlaced(state.orderNumber)
        } else if (state is CheckoutUiState.Ready && state.error != null) {
            Toast.makeText(context, state.error, Toast.LENGTH_LONG).show()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.checkout), fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack, modifier = Modifier.testTag("checkout_back")) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.back))
                    }
                }
            )
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            when (val state = uiState) {
                is CheckoutUiState.Loading -> LoadingState()
                is CheckoutUiState.Error -> ErrorState(
                    message = state.message,
                    onRetry = viewModel::loadCheckoutData
                )
                is CheckoutUiState.Ready -> {
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxSize()
                            .testTag("checkout_form"),
                        contentPadding = PaddingValues(16.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        item {
                            DeliveryInfoCard(
                                name = customerName,
                                onNameChange = { customerName = it },
                                phone = phone,
                                onPhoneChange = { phone = it },
                                address = address,
                                onAddressChange = { address = it },
                                city = city,
                                onCityChange = { city = it }
                            )
                        }

                        item {
                            PaymentMethodCard(
                                selectedMethod = paymentMethod,
                                onSelectMethod = { paymentMethod = it }
                            )
                        }

                        item {
                            PromoCodeCard(
                                promoCode = promoCode,
                                onPromoCodeChange = { promoCode = it },
                                onApply = { viewModel.previewDiscount(promoCode) }
                            )
                        }

                        item {
                            val subtotal = state.preview?.total ?: state.cart.total
                            val discount = state.preview?.promotionDiscount ?: "0.00"
                            OrderSummaryCard(
                                cart = state.cart,
                                discount = discount,
                                total = subtotal
                            )
                        }

                        item {
                            Button(
                                onClick = {
                                    if (customerName.isBlank() || phone.isBlank() || address.isBlank() || city.isBlank()) {
                                        Toast.makeText(context, "Please fill in all delivery details.", Toast.LENGTH_SHORT).show()
                                    } else {
                                        viewModel.placeOrder(
                                            customerName = customerName,
                                            phone = phone,
                                            address = address,
                                            city = city,
                                            paymentMethod = paymentMethod,
                                            promoCode = promoCode.ifBlank { null }
                                        )
                                    }
                                },
                                enabled = !state.isPlacingOrder,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(52.dp)
                                    .testTag("place_order_button"),
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                if (state.isPlacingOrder) {
                                    CircularProgressIndicator(
                                        color = MaterialTheme.colorScheme.onPrimary,
                                        modifier = Modifier.size(20.dp),
                                        strokeWidth = 2.dp
                                    )
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text(stringResource(R.string.placing_order))
                                } else {
                                    Text(stringResource(R.string.place_order), fontWeight = FontWeight.Bold)
                                }
                            }
                        }
                    }
                }
                is CheckoutUiState.Completed -> {
                    LoadingState()
                }
            }
        }
    }
}

@Composable
private fun DeliveryInfoCard(
    name: String,
    onNameChange: (String) -> Unit,
    phone: String,
    onPhoneChange: (String) -> Unit,
    address: String,
    onAddressChange: (String) -> Unit,
    city: String,
    onCityChange: (String) -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.LocationOn, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = stringResource(R.string.delivery_details),
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
            }
            Spacer(modifier = Modifier.height(12.dp))
            OutlinedTextField(
                value = name,
                onValueChange = onNameChange,
                label = { Text(stringResource(R.string.recipient_name)) },
                leadingIcon = { Icon(Icons.Default.Person, contentDescription = null) },
                modifier = Modifier
                    .fillMaxWidth()
                    .testTag("input_customer_name"),
                singleLine = true
            )
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedTextField(
                value = phone,
                onValueChange = onPhoneChange,
                label = { Text(stringResource(R.string.phone_number)) },
                leadingIcon = { Icon(Icons.Default.Phone, contentDescription = null) },
                modifier = Modifier
                    .fillMaxWidth()
                    .testTag("input_phone"),
                singleLine = true
            )
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedTextField(
                value = address,
                onValueChange = onAddressChange,
                label = { Text(stringResource(R.string.delivery_address)) },
                modifier = Modifier
                    .fillMaxWidth()
                    .testTag("input_address"),
                minLines = 2
            )
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedTextField(
                value = city,
                onValueChange = onCityChange,
                label = { Text(stringResource(R.string.delivery_city)) },
                modifier = Modifier
                    .fillMaxWidth()
                    .testTag("input_city"),
                singleLine = true
            )
        }
    }
}

@Composable
private fun PaymentMethodCard(
    selectedMethod: String,
    onSelectMethod: (String) -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = stringResource(R.string.payment_method),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(10.dp))

            // COD Option
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .selectable(
                        selected = selectedMethod == "cod",
                        onClick = { onSelectMethod("cod") }
                    )
                    .padding(vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                RadioButton(
                    selected = selectedMethod == "cod",
                    onClick = { onSelectMethod("cod") }
                )
                Spacer(modifier = Modifier.width(8.dp))
                Icon(Icons.Default.LocalAtm, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                Spacer(modifier = Modifier.width(8.dp))
                Column {
                    Text(text = stringResource(R.string.cod_label), fontWeight = FontWeight.SemiBold)
                    Text(text = "Pay with cash upon delivery", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }

            // SSLCOMMERZ Option
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .selectable(
                        selected = selectedMethod == "sslcommerz",
                        onClick = { onSelectMethod("sslcommerz") }
                    )
                    .padding(vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                RadioButton(
                    selected = selectedMethod == "sslcommerz",
                    onClick = { onSelectMethod("sslcommerz") }
                )
                Spacer(modifier = Modifier.width(8.dp))
                Icon(Icons.Default.CreditCard, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                Spacer(modifier = Modifier.width(8.dp))
                Column {
                    Text(text = stringResource(R.string.sslcommerz_label), fontWeight = FontWeight.SemiBold)
                    Text(text = "Cards, bKash, Nagad online gateway", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

@Composable
private fun PromoCodeCard(
    promoCode: String,
    onPromoCodeChange: (String) -> Unit,
    onApply: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = stringResource(R.string.promo_code),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                OutlinedTextField(
                    value = promoCode,
                    onValueChange = onPromoCodeChange,
                    placeholder = { Text("e.g. NEXFIRST10") },
                    leadingIcon = { Icon(Icons.Default.Tag, contentDescription = null) },
                    modifier = Modifier
                        .weight(1f)
                        .testTag("promo_code_input"),
                    singleLine = true
                )
                Spacer(modifier = Modifier.width(8.dp))
                Button(
                    onClick = onApply,
                    modifier = Modifier.height(56.dp).testTag("apply_promo_button")
                ) {
                    Text(stringResource(R.string.apply_promo))
                }
            }
        }
    }
}

@Composable
private fun OrderSummaryCard(
    cart: com.nexhaat.app.data.remote.dto.CartDto,
    discount: String,
    total: String
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = stringResource(R.string.order_summary),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(10.dp))

            cart.items.forEach { item ->
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 3.dp),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = "${item.quantity}x ${item.name}",
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.weight(1f)
                    )
                    Text(
                        text = "৳ ${item.subtotal}",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))
            HorizontalDivider()
            Spacer(modifier = Modifier.height(8.dp))

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(stringResource(R.string.subtotal), style = MaterialTheme.typography.bodyMedium)
                Text("৳ ${cart.subtotal}", style = MaterialTheme.typography.bodyMedium)
            }
            Spacer(modifier = Modifier.height(4.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(stringResource(R.string.delivery_fee), style = MaterialTheme.typography.bodyMedium)
                Text("৳ ${cart.deliveryFee}", style = MaterialTheme.typography.bodyMedium)
            }
            if (discount != "0.00" && discount != "0") {
                Spacer(modifier = Modifier.height(4.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(stringResource(R.string.discount), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary)
                    Text("-৳ $discount", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary)
                }
            }
            Spacer(modifier = Modifier.height(8.dp))
            HorizontalDivider()
            Spacer(modifier = Modifier.height(8.dp))

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(stringResource(R.string.total), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text("৳ $total", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
            }
        }
    }
}
