package com.nexhaat.app.ui.screens.orders

import android.widget.Toast
import androidx.compose.foundation.background
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
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.LocalShipping
import androidx.compose.material.icons.filled.Replay
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nexhaat.app.R
import com.nexhaat.app.data.remote.dto.OrderDto
import com.nexhaat.app.ui.components.EmptyState
import com.nexhaat.app.ui.components.ErrorState
import com.nexhaat.app.ui.components.LoadingState
import com.nexhaat.app.ui.components.MarketplaceBottomBar
import com.nexhaat.app.ui.components.MarketplaceTopBar

@Composable
fun OrdersScreen(
    viewModel: OrdersViewModel = hiltViewModel(),
    onNavigateToHome: () -> Unit,
    onNavigateToCategories: () -> Unit,
    onNavigateToSearch: () -> Unit,
    onNavigateToCart: () -> Unit,
    onNavigateToSignIn: () -> Unit = {}
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val actionMessage by viewModel.actionMessage.collectAsStateWithLifecycle()
    val context = LocalContext.current

    var selectedOrderForReturn by remember { mutableStateOf<OrderDto?>(null) }
    var returnReason by remember { mutableStateOf("") }

    LaunchedEffect(actionMessage) {
        actionMessage?.let {
            Toast.makeText(context, it, Toast.LENGTH_SHORT).show()
            viewModel.dismissActionMessage()
        }
    }

    Scaffold(
        topBar = {
            MarketplaceTopBar(
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
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            when (val state = uiState) {
                is OrdersUiState.Loading -> LoadingState()
                is OrdersUiState.Error -> {
                    if (state.message.contains("Sign in", ignoreCase = true)) {
                        EmptyState(
                            title = stringResource(R.string.my_orders),
                            message = state.message,
                            buttonText = stringResource(R.string.sign_in),
                            onButtonClick = onNavigateToSignIn
                        )
                    } else {
                        ErrorState(
                            message = state.message,
                            onRetry = viewModel::loadOrders
                        )
                    }
                }
                is OrdersUiState.Success -> {
                    if (state.orders.isEmpty()) {
                        EmptyState(
                            title = stringResource(R.string.no_orders),
                            message = stringResource(R.string.no_orders_sub),
                            buttonText = stringResource(R.string.explore_marketplace),
                            onButtonClick = onNavigateToHome
                        )
                    } else {
                        LazyColumn(
                            modifier = Modifier
                                .fillMaxSize()
                                .testTag("orders_list"),
                            contentPadding = PaddingValues(16.dp),
                            verticalArrangement = Arrangement.spacedBy(16.dp)
                        ) {
                            items(state.orders, key = { it.id }) { order ->
                                OrderCard(
                                    order = order,
                                    onCancelOrder = { viewModel.cancelOrder(order.orderNumber) },
                                    onRequestReturn = {
                                        selectedOrderForReturn = order
                                        returnReason = ""
                                    }
                                )
                            }
                        }
                    }
                }
            }
        }
    }

    selectedOrderForReturn?.let { order ->
        AlertDialog(
            onDismissRequest = { selectedOrderForReturn = null },
            title = { Text(stringResource(R.string.request_return), fontWeight = FontWeight.Bold) },
            text = {
                Column {
                    Text("Order #${order.orderNumber}", style = MaterialTheme.typography.bodyMedium)
                    Spacer(modifier = Modifier.height(12.dp))
                    OutlinedTextField(
                        value = returnReason,
                        onValueChange = { returnReason = it },
                        label = { Text(stringResource(R.string.return_reason_prompt)) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("return_reason_input"),
                        minLines = 3
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (returnReason.isNotBlank()) {
                            viewModel.requestReturn(order.orderNumber, returnReason.trim())
                            selectedOrderForReturn = null
                        }
                    },
                    modifier = Modifier.testTag("submit_return_button")
                ) {
                    Text(stringResource(R.string.submit_return))
                }
            },
            dismissButton = {
                TextButton(onClick = { selectedOrderForReturn = null }) {
                    Text(stringResource(R.string.cancel))
                }
            }
        )
    }
}

@Composable
private fun OrderCard(
    order: OrderDto,
    onCancelOrder: () -> Unit,
    onRequestReturn: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .testTag("order_card_${order.orderNumber}"),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "Order #${order.orderNumber}",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    order.createdAt?.let {
                        Text(
                            text = it.take(10),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                OrderStatusBadge(status = order.status)
            }

            Spacer(modifier = Modifier.height(12.dp))
            HorizontalDivider()
            Spacer(modifier = Modifier.height(12.dp))

            // Items list
            order.items.forEach { item ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 4.dp),
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

            Spacer(modifier = Modifier.height(12.dp))
            HorizontalDivider()
            Spacer(modifier = Modifier.height(12.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "Payment: ${order.paymentMethod.uppercase()} (${order.paymentStatus ?: "unpaid"})",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = "Total: ৳ ${order.total}",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )
                }

                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (order.status == "pending" || order.status == "confirmed") {
                        OutlinedButton(
                            onClick = onCancelOrder,
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
                            modifier = Modifier.testTag("cancel_order_${order.orderNumber}")
                        ) {
                            Text(stringResource(R.string.cancel_order))
                        }
                    } else if (order.status == "delivered" && order.returnEligible == true) {
                        Button(
                            onClick = onRequestReturn,
                            modifier = Modifier.testTag("request_return_${order.orderNumber}")
                        ) {
                            Text(stringResource(R.string.request_return))
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun OrderStatusBadge(status: String) {
    val (bgColor, textColor, label) = when (status.lowercase()) {
        "delivered" -> Triple(MaterialTheme.colorScheme.primaryContainer, MaterialTheme.colorScheme.primary, "Delivered")
        "shipped" -> Triple(MaterialTheme.colorScheme.secondaryContainer, MaterialTheme.colorScheme.secondary, "Shipped")
        "processing" -> Triple(MaterialTheme.colorScheme.tertiaryContainer, MaterialTheme.colorScheme.tertiary, "Processing")
        "confirmed" -> Triple(MaterialTheme.colorScheme.surfaceVariant, MaterialTheme.colorScheme.onSurfaceVariant, "Confirmed")
        "cancelled" -> Triple(MaterialTheme.colorScheme.errorContainer, MaterialTheme.colorScheme.error, "Cancelled")
        else -> Triple(MaterialTheme.colorScheme.surfaceVariant, MaterialTheme.colorScheme.onSurfaceVariant, status.replaceFirstChar { it.uppercase() })
    }

    Surface(
        shape = RoundedCornerShape(8.dp),
        color = bgColor
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Bold,
            color = textColor,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
        )
    }
}
