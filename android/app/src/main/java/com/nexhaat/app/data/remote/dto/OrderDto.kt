package com.nexhaat.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class OrderDto(
    val id: Int,
    @SerialName("order_number")
    val orderNumber: String,
    @SerialName("checkout_group")
    val checkoutGroup: String? = null,
    val status: String,
    @SerialName("delivery_status")
    val deliveryStatus: String? = null,
    @SerialName("payment_method")
    val paymentMethod: String,
    @SerialName("payment_status")
    val paymentStatus: String? = null,
    @SerialName("customer_name")
    val customerName: String? = null,
    val phone: String? = null,
    val email: String? = null,
    val address: String? = null,
    val total: String,
    @SerialName("delivery_fee")
    val deliveryFee: String? = null,
    @SerialName("discount_amount")
    val discountAmount: String? = null,
    @SerialName("promotion_code")
    val promotionCode: String? = null,
    @SerialName("items_subtotal")
    val itemsSubtotal: String? = null,
    @SerialName("return_deadline")
    val returnDeadline: String? = null,
    @SerialName("return_eligible")
    val returnEligible: Boolean? = null,
    @SerialName("return_request")
    val returnRequest: ReturnRequestDto? = null,
    @SerialName("seller_id")
    val sellerId: Int? = null,
    @SerialName("rider_id")
    val riderId: Int? = null,
    @SerialName("created_at")
    val createdAt: String? = null,
    val items: List<OrderItemDto> = emptyList()
)

@Serializable
data class OrderItemDto(
    val id: Int? = null,
    @SerialName("product_id")
    val productId: Int,
    @SerialName("variant_id")
    val variantId: Int? = null,
    val name: String,
    @SerialName("variant_label")
    val variantLabel: String? = null,
    val sku: String? = null,
    val price: String,
    val quantity: Int,
    val subtotal: String
)

@Serializable
data class ReturnRequestDto(
    val id: Int? = null,
    val status: String,
    val reason: String? = null,
    @SerialName("refund_amount")
    val refundAmount: String? = null,
    @SerialName("refund_status")
    val refundStatus: String? = null,
    @SerialName("review_note")
    val reviewNote: String? = null,
    @SerialName("created_at")
    val createdAt: String? = null,
    @SerialName("reviewed_at")
    val reviewedAt: String? = null,
    @SerialName("resolved_at")
    val resolvedAt: String? = null
)

@Serializable
data class CheckoutPreviewRequest(
    @SerialName("promotion_code")
    val promotionCode: String? = null
)

@Serializable
data class CheckoutPreviewResponse(
    val orders: List<CheckoutPreviewOrderDto> = emptyList(),
    @SerialName("promotion_code")
    val promotionCode: String? = null,
    @SerialName("promotion_discount")
    val promotionDiscount: String = "0.00",
    val total: String = "0.00"
)

@Serializable
data class CheckoutPreviewOrderDto(
    @SerialName("seller_id")
    val sellerId: Int? = null,
    val items: List<CheckoutPreviewItemDto> = emptyList(),
    val subtotal: String,
    @SerialName("delivery_fee")
    val deliveryFee: String,
    @SerialName("promotion_code")
    val promotionCode: String? = null,
    @SerialName("discount_amount")
    val discountAmount: String = "0.00",
    val total: String
)

@Serializable
data class CheckoutPreviewItemDto(
    @SerialName("product_id")
    val productId: Int,
    @SerialName("variant_id")
    val variantId: Int? = null,
    val name: String,
    @SerialName("variant_label")
    val variantLabel: String? = null,
    val quantity: Int,
    @SerialName("unit_price")
    val unitPrice: String,
    val subtotal: String
)

@Serializable
data class CheckoutRequest(
    @SerialName("customer_name")
    val customerName: String,
    val phone: String,
    val address: String,
    val city: String,
    @SerialName("payment_method")
    val paymentMethod: String = "cod",
    @SerialName("promotion_code")
    val promotionCode: String? = null
)

@Serializable
data class CheckoutResponse(
    val orders: List<OrderDto> = emptyList(),
    @SerialName("checkout_group")
    val checkoutGroup: String? = null,
    @SerialName("payment_status")
    val paymentStatus: String? = null,
    @SerialName("checkout_url")
    val checkoutUrl: String? = null,
    @SerialName("payment_status_url")
    val paymentStatusUrl: String? = null
)

@Serializable
data class ReturnOrderRequest(
    val reason: String
)
