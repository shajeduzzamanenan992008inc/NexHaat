import { describe, it } from 'node:test';
import assert from 'node:assert';
import {
  APK_MIME_TYPE,
  DEFAULT_APK_FILENAME,
  PRIMARY_DOWNLOAD_URL,
  DIRECT_DOWNLOAD_URL,
} from './apkDownloadService.ts';

describe('apkDownloadService constants and MIME definitions', () => {
  it('enforces Android package archive MIME type', () => {
    assert.strictEqual(APK_MIME_TYPE, 'application/vnd.android.package-archive');
  });

  it('provides default APK filename matching version standard', () => {
    assert.strictEqual(DEFAULT_APK_FILENAME, 'NexHaat-v1.0.0.apk');
    assert.ok(DEFAULT_APK_FILENAME.endsWith('.apk'));
  });

  it('defines valid download endpoints', () => {
    assert.strictEqual(PRIMARY_DOWNLOAD_URL, '/api/download/apk');
    assert.strictEqual(DIRECT_DOWNLOAD_URL, '/downloads/nexhaat.apk');
  });

  it('creates Blob with explicit APK MIME type', () => {
    const dummyData = new Uint8Array([0x50, 0x4b, 0x03, 0x04]);
    const blob = new Blob([dummyData], { type: APK_MIME_TYPE });
    assert.strictEqual(blob.type, 'application/vnd.android.package-archive');
    assert.strictEqual(blob.size, 4);
  });
});
