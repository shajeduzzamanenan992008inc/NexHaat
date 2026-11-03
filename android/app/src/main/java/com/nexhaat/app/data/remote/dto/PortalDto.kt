package com.nexhaat.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class SellerDashboardDto(
    val products: Int = 0,
    @SerialName("active_products")
    val activeProducts: Int = 0,
    @SerialName("pending_orders")
    val pendingOrders: Int = 0,
    @SerialName("completed_orders")
    val completedOrders: Int = 0,
    val sales: String = "0.00"
)
