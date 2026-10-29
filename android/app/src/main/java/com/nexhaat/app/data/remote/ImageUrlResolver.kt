package com.nexhaat.app.data.remote

import java.net.URI

/** Resolves API image references while rejecting unsupported or malformed URLs. */
object ImageUrlResolver {
    fun resolve(imageReference: String?, mediaBaseUrl: String): String? {
        val reference = imageReference?.trim()?.takeIf(String::isNotEmpty) ?: return null
        if (reference.any(Char::isWhitespace) || reference.any { it.isISOControl() }) return null

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

        val baseUri = runCatching {
            val base = URI(mediaBaseUrl.trim())
            if (base.path.orEmpty().endsWith('/')) base else URI(base.toASCIIString() + "/")
        }.getOrNull() ?: return null
        if (!isSafeHttpUri(baseUri) || baseUri.rawQuery != null || baseUri.rawFragment != null) return null

        val resolved = if (imageUri.rawPath.orEmpty().startsWith('/')) {
            URI(baseUri.scheme, null, baseUri.host, baseUri.port, imageUri.path, imageUri.query, imageUri.fragment)
        } else {
            baseUri.resolve(imageUri)
        }.normalize()
        return resolved.takeIf(::isSafeHttpUri)?.toASCIIString()
    }

    private fun isSafeHttpUri(uri: URI): Boolean =
        uri.scheme?.lowercase()?.let { it == "http" || it == "https" } == true &&
            !uri.host.isNullOrBlank() &&
            uri.rawUserInfo == null
}
