package com.nexhaat.app.data.remote

import java.net.URI

/** Resolves API image references while rejecting unsupported or malformed URLs. */
object ImageUrlResolver {
    private fun isKnownMediaPlaceholderHost(host: String?): Boolean {
        if (host.isNullOrBlank()) return false
        val lower = host.lowercase()
        return lower.contains("release_base_url_replace_me") || (lower.contains("replace_me") && lower.contains("media"))
    }

    private fun isKnownMediaPlaceholderBase(mediaBaseUrl: String): Boolean {
        val trimmed = mediaBaseUrl.trim()
        if (trimmed.isBlank()) return true
        val lower = trimmed.lowercase()
        if (lower.contains("release_base_url_replace_me")) return true
        if (lower.contains("replace_me") && lower.contains("media")) return true
        return false
    }

    fun resolve(imageReference: String?, mediaBaseUrl: String): String? {
        val reference = imageReference?.trim()?.takeIf(String::isNotEmpty) ?: return null

        val imageUri = runCatching { URI(reference) }.getOrNull() ?: return null
        val scheme = imageUri.scheme
        if (scheme != null) {
            if (scheme.lowercase() !in setOf("http", "https")) return null
            return imageUri.takeIf(::isSafeHttpUri)?.toASCIIString()
        }
        if (imageUri.rawAuthority != null || reference.startsWith("//")) return null
        if (imageUri.rawPath.orEmpty().split('/').any { it == ".." || it.equals("%2e%2e", ignoreCase = true) }) {
            return null
        }

        if (isKnownMediaPlaceholderBase(mediaBaseUrl)) {
            return null
        }

        val baseUri = runCatching {
            val base = URI(mediaBaseUrl.trim())
            if (base.path.orEmpty().endsWith('/')) base else URI(base.toASCIIString() + "/")
        }.getOrNull() ?: return null
        if (!isSafeHttpUri(baseUri) || baseUri.rawQuery != null || baseUri.rawFragment != null) return null
        if (isKnownMediaPlaceholderHost(baseUri.host)) {
            return null
        }

        val resolved = if (imageUri.rawPath.orEmpty().startsWith('/')) {
            URI(baseUri.scheme, null, baseUri.host, baseUri.port, imageUri.path, imageUri.query, imageUri.fragment)
        } else {
            baseUri.resolve(imageUri)
        }.normalize()
        return resolved.takeIf(::isSafeHttpUri)?.toASCIIString()
    }

    fun resolveAbsoluteOnly(imageReference: String?, mediaBaseUrl: String): String? {
        val reference = imageReference?.trim()?.takeIf(String::isNotEmpty) ?: return null
        if (reference.any(Char::isWhitespace) || reference.any { it.isISOControl() }) return null
        val imageUri = runCatching { URI(reference) }.getOrNull() ?: return null
        val scheme = imageUri.scheme
        if (scheme == null || scheme.lowercase() !in setOf("http", "https")) return null
        return imageUri.takeIf(::isSafeHttpUri)?.toASCIIString()
    }

    fun resolveFromBackendAbsolute(imageReference: String?): String? {
        if (imageReference != null) {
            val trimmed = imageReference.trim()
            if (trimmed.isNotEmpty()) {
                val candidate = runCatching { URI(trimmed) }.getOrNull()
                    ?.takeIf { it.scheme?.lowercase() in setOf("http", "https") && isSafeHttpUri(it) }
                    ?.toASCIIString()
                if (candidate != null) return candidate
            }
        }
        return null
    }

    val CATEGORY_FALLBACKS = mapOf(
        "burgers" to "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=900&q=80",
        "pizza" to "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=900&q=80",
        "drinks" to "https://images.unsplash.com/photo-1544145945-f90425340c7e?auto=format&fit=crop&w=900&q=80",
        "beverages" to "https://images.unsplash.com/photo-1544145945-f90425340c7e?auto=format&fit=crop&w=900&q=80",
        "chicken" to "https://images.unsplash.com/photo-1598103442097-8b74394b95c6?auto=format&fit=crop&w=900&q=80",
        "fruits" to "https://images.unsplash.com/photo-1619566636858-adf3ef46400b?auto=format&fit=crop&w=900&q=80",
        "vegetables" to "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=900&q=80",
        "grocery" to "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=900&q=80",
        "groceries" to "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=900&q=80",
        "dairy" to "https://images.unsplash.com/photo-1550583724-b2692b85b150?auto=format&fit=crop&w=900&q=80",
        "bakery" to "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=900&q=80",
        "meat" to "https://images.unsplash.com/photo-1607623814075-e51df1bdc82f?auto=format&fit=crop&w=900&q=80",
        "fish" to "https://images.unsplash.com/photo-1534043464124-3be32fe000c9?auto=format&fit=crop&w=900&q=80",
        "seafood" to "https://images.unsplash.com/photo-1534043464124-3be32fe000c9?auto=format&fit=crop&w=900&q=80",
        "snacks" to "https://images.unsplash.com/photo-1621996346565-e3d5d6281775?auto=format&fit=crop&w=900&q=80",
        "sweets" to "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=900&q=80",
        "dessert" to "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=900&q=80",
        "spices" to "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?auto=format&fit=crop&w=900&q=80",
        "rice" to "https://images.unsplash.com/photo-1586201375761-83865001e31c?auto=format&fit=crop&w=900&q=80",
        "electronics" to "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=900&q=80",
        "gadgets" to "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=900&q=80",
        "mobile" to "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=900&q=80",
        "computers" to "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=900&q=80",
        "laptops" to "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=900&q=80",
        "fashion" to "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?auto=format&fit=crop&w=900&q=80",
        "clothing" to "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?auto=format&fit=crop&w=900&q=80",
        "men" to "https://images.unsplash.com/photo-1516257984-b1b4d707412e?auto=format&fit=crop&w=900&q=80",
        "women" to "https://images.unsplash.com/photo-1525507119028-ed4c629a60a3?auto=format&fit=crop&w=900&q=80",
        "kids" to "https://images.unsplash.com/photo-1622290291468-a28f7a7dc6a8?auto=format&fit=crop&w=900&q=80",
        "footwear" to "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80",
        "shoes" to "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80",
        "beauty" to "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=900&q=80",
        "skincare" to "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=900&q=80",
        "health" to "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=900&q=80",
        "medicine" to "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=900&q=80",
        "pharmacy" to "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=900&q=80",
        "home-kitchen" to "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=900&q=80",
        "kitchen" to "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=900&q=80",
        "sports" to "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?auto=format&fit=crop&w=900&q=80",
        "books" to "https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=900&q=80",
        "stationery" to "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?auto=format&fit=crop&w=900&q=80"
    )

    fun getCategoryFallback(slugOrName: String?): String {
        val key = (slugOrName ?: "").lowercase().trim()
        if (key.isNotEmpty()) {
            CATEGORY_FALLBACKS[key]?.let { return it }
            for ((catKey, url) in CATEGORY_FALLBACKS) {
                if (key.contains(catKey) || catKey.contains(key)) return url
            }
        }
        return CATEGORY_FALLBACKS["grocery"] ?: "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=900&q=80"
    }

    private fun isSafeHttpUri(uri: URI): Boolean =
        uri.scheme?.lowercase()?.let { it == "http" || it == "https" } == true &&
            !uri.host.isNullOrBlank() &&
            uri.rawUserInfo == null
}

/** Selects the media base URL when the build-time one was explicitly configured. */
object MediaBaseUrlResolver {
    /**
     * Returns the media base URL a release build may trust.
     *
     * [runtimeFallback] intentionally keeps the placeholder value, so an unconfigured
     * release build resolves relative references to null instead of inventing a host.
     */
    fun resolvedOrFallbackString(
        resolvedFlag: String?,
        buildTimeValue: String,
        runtimeFallback: String
    ): String = resolvedOrFallback(resolvedFlag, buildTimeValue, runtimeFallback)

    fun resolvedOrFallback(
        resolvedFlag: String?,
        buildTimeValue: String,
        runtimeFallback: String
    ): String {
        val resolved = resolvedFlag == "true" || resolvedFlag == "1"
        val configured = if (resolved) buildTimeValue else runtimeFallback
        return if (configured.isBlank()) "" else configured.trim()
    }

    fun resolvedOrFallbackStrict(
        resolvedFlag: String,
        buildTimeValue: String,
        runtimeFallback: String
    ): String {
        return resolvedOrFallback(resolvedFlag, buildTimeValue, runtimeFallback)
    }

    fun isMediaBaseResolvedFlagTrue(resolvedFlag: String): Boolean {
        return resolvedFlag == "true" || resolvedFlag == "1"
    }
}
