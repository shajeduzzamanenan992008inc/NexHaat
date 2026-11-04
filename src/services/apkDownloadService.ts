/**
 * NexHaat Android APK Download Service
 * 
 * Provides robust filesystem & network interaction for downloading the NexHaat Android APK.
 * Handles:
 * - Proper MIME type enforcement ('application/vnd.android.package-archive')
 * - Fetch streaming with progress tracking
 * - Blob URL construction & cleanup
 * - Fallback to direct anchor navigation if fetch/blob generation fails
 * - Server metadata querying
 */

export interface ApkMetadata {
  filename: string;
  displayName: string;
  version: string;
  versionCode: number;
  packageId: string;
  mimeType: string;
  sizeBytes: number;
  sizeFormatted: string;
  downloadUrl: string;
  directUrl: string;
  exists: boolean;
}

export interface ApkProgress {
  receivedBytes: number;
  totalBytes: number;
  percent: number;
  formattedReceived: string;
  formattedTotal: string;
}

export interface ApkDownloadResult {
  success: boolean;
  filename: string;
  sizeBytes?: number;
  error?: string;
  method: 'blob-stream' | 'direct-link' | 'unavailable';
}

export const APK_MIME_TYPE = 'application/vnd.android.package-archive';
export const DEFAULT_APK_FILENAME = 'NexHaat-v1.0.0.apk';
export const PRIMARY_DOWNLOAD_URL = '/api/download/apk';
export const DIRECT_DOWNLOAD_URL = '/downloads/nexhaat.apk';

function formatBytes(bytes: number): string {
  if (bytes <= 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

/**
 * Queries server for latest APK package information
 */
export async function getApkMetadata(): Promise<ApkMetadata> {
  try {
    const res = await fetch('/api/download/apk/info', {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });

    if (res.ok) {
      const data = await res.json();
      if (data.success && data.apk) {
        return data.apk;
      }
    }
  } catch {
    // Fall back to default metadata if API info is unreachable
  }

  return {
    filename: 'nexhaat.apk',
    displayName: DEFAULT_APK_FILENAME,
    version: '1.0.0',
    versionCode: 1,
    packageId: 'com.nexhaat.app',
    mimeType: APK_MIME_TYPE,
    sizeBytes: 0,
    sizeFormatted: 'Unavailable',
    downloadUrl: PRIMARY_DOWNLOAD_URL,
    directUrl: DIRECT_DOWNLOAD_URL,
    exists: false,
  };
}

/**
 * Triggers direct browser download via anchor element
 */
export function triggerDirectDownload(url = PRIMARY_DOWNLOAD_URL, filename = DEFAULT_APK_FILENAME): void {
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  link.setAttribute('type', APK_MIME_TYPE);
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  setTimeout(() => {
    if (document.body.contains(link)) {
      document.body.removeChild(link);
    }
  }, 500);
}

/**
 * Initiates APK download with explicit MIME type enforcement and optional progress tracking
 */
export async function downloadApk(
  onProgress?: (progress: ApkProgress) => void,
  options?: { targetUrl?: string; filename?: string },
): Promise<ApkDownloadResult> {
  const targetUrl = options?.targetUrl || PRIMARY_DOWNLOAD_URL;
  const targetFilename = options?.filename || DEFAULT_APK_FILENAME;

  try {
    const response = await fetch(targetUrl, {
      method: 'GET',
      headers: {
        Accept: `${APK_MIME_TYPE}, application/octet-stream, */*`,
      },
    });

    if (!response.ok) {
      throw new Error(`Server returned HTTP ${response.status} ${response.statusText}`);
    }

    const contentLength = response.headers.get('content-length');
    const totalBytes = contentLength ? parseInt(contentLength, 10) : 0;

    let blob: Blob;

    // Use streaming if body reader is available to provide fluid progress
    if (response.body && typeof response.body.getReader === 'function') {
      const reader = response.body.getReader();
      const chunks: Uint8Array[] = [];
      let receivedBytes = 0;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        if (value) {
          chunks.push(value);
          receivedBytes += value.length;

          if (onProgress) {
            const percent = totalBytes > 0 ? Math.min(100, Math.round((receivedBytes / totalBytes) * 100)) : 0;
            onProgress({
              receivedBytes,
              totalBytes: totalBytes || receivedBytes,
              percent,
              formattedReceived: formatBytes(receivedBytes),
              formattedTotal: formatBytes(totalBytes || receivedBytes),
            });
          }
        }
      }

      // CRITICAL MIME FIX: Explicitly enforce the Android Package Archive MIME type
      // Even if server or intermediate proxy rewrote the Content-Type header to text/plain or octet-stream
      const downloadedBytes = new ArrayBuffer(receivedBytes);
      const downloadedView = new Uint8Array(downloadedBytes);
      let offset = 0;
      for (const chunk of chunks) {
        downloadedView.set(chunk, offset);
        offset += chunk.byteLength;
      }
      blob = new Blob([downloadedBytes], { type: APK_MIME_TYPE });
    } else {
      const arrayBuffer = await response.arrayBuffer();
      blob = new Blob([arrayBuffer], { type: APK_MIME_TYPE });
    }

    // Generate verified Object URL
    const blobUrl = window.URL.createObjectURL(blob);
    const downloadAnchor = document.createElement('a');
    downloadAnchor.href = blobUrl;
    downloadAnchor.download = targetFilename;
    downloadAnchor.setAttribute('type', APK_MIME_TYPE);
    downloadAnchor.style.display = 'none';
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();

    setTimeout(() => {
      if (document.body.contains(downloadAnchor)) {
        document.body.removeChild(downloadAnchor);
      }
      window.URL.revokeObjectURL(blobUrl);
    }, 1000);

    return {
      success: true,
      filename: targetFilename,
      sizeBytes: blob.size,
      method: 'blob-stream',
    };
  } catch (err: any) {
    if (typeof err?.message === 'string' && err.message.startsWith('Server returned HTTP ')) {
      return {
        success: false,
        filename: targetFilename,
        error: err.message,
        method: 'unavailable',
      };
    }

    // Robust Fallback: Trigger direct anchor navigation if fetch/blob streaming encountered CORS or memory issues
    try {
      triggerDirectDownload(targetUrl, targetFilename);
      return {
        success: true,
        filename: targetFilename,
        method: 'direct-link',
      };
    } catch (fallbackErr: any) {
      return {
        success: false,
        filename: targetFilename,
        error: err?.message || fallbackErr?.message || 'Download failed',
        method: 'direct-link',
      };
    }
  }
}
