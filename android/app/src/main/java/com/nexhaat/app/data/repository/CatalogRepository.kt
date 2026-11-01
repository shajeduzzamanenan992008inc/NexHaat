package com.nexhaat.app.data.repository

import com.nexhaat.app.data.remote.ApiService
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.BannerDto
import com.nexhaat.app.data.remote.dto.CategoryDto
import com.nexhaat.app.data.remote.dto.ProductDto
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class CatalogRepository @Inject constructor(
    private val apiService: ApiService
) {
    suspend fun getCategories(): NetworkResult<List<CategoryDto>> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.getCategories()
            if (response.success && response.data != null) {
                NetworkResult.Success(response.data)
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Failed to fetch categories")
            }
        } catch (e: Exception) {
            NetworkResult.Error(e.localizedMessage ?: "Unknown error")
        }
    }

    suspend fun getBanners(): NetworkResult<List<BannerDto>> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.getBanners()
            if (response.success && response.data != null) {
                NetworkResult.Success(response.data)
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Failed to fetch banners")
            }
        } catch (e: Exception) {
            NetworkResult.Error(e.localizedMessage ?: "Unknown error")
        }
    }

    suspend fun getProducts(
        page: Int = 1,
        limit: Int = 20,
        query: String? = null,
        categoryId: Int? = null,
        sort: String? = null
    ): NetworkResult<Pair<List<ProductDto>, com.nexhaat.app.data.remote.dto.Pagination?>> = withContext(Dispatchers.IO) {
        try {
            val response = if (categoryId != null) {
                apiService.getCategoryProducts(page, limit, categoryId, sort)
            } else {
                apiService.getProducts(page, limit, query)
            }
            if (response.success && response.data != null) {
                NetworkResult.Success(Pair(response.data, response.pagination))
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Failed to fetch products")
            }
        } catch (e: Exception) {
            NetworkResult.Error(e.localizedMessage ?: "Unknown error")
        }
    }

    suspend fun searchProducts(query: String, page: Int = 1): NetworkResult<Pair<List<ProductDto>, com.nexhaat.app.data.remote.dto.Pagination?>> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.searchProducts(query, page)
            if (response.success && response.data != null) {
                NetworkResult.Success(Pair(response.data, response.pagination))
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Failed to search products")
            }
        } catch (e: Exception) {
            NetworkResult.Error(e.localizedMessage ?: "Unknown error")
        }
    }

    suspend fun getProductDetail(productId: Int): NetworkResult<ProductDto> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.getProductDetail(productId)
            if (response.success && response.data != null) {
                NetworkResult.Success(response.data)
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Failed to fetch product")
            }
        } catch (e: Exception) {
            NetworkResult.Error(e.localizedMessage ?: "Unknown error")
        }
    }

    suspend fun getBanners(page: Int = 1, limit: Int = 10): NetworkResult<List<BannerDto>> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.getBanners(page, limit)
            if (response.success && response.data != null) {
                NetworkResult.Success(response.data)
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Failed to fetch banners")
            }
        } catch (e: Exception) {
            NetworkResult.Error(e.localizedMessage ?: "Unknown error")
        }
    }
}
