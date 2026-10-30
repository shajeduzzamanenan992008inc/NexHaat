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
