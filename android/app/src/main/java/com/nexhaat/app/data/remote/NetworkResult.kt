package com.nexhaat.app.data.remote

sealed class NetworkResult<out T> {
    data class Success<T>(val data: T) : NetworkResult<T>()
    data class Error(val message: String, val code: String? = null) : NetworkResult<Nothing>()
    data object Loading : NetworkResult<Nothing>()
}
