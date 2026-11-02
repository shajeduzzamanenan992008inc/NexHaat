const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

function crc32(buf) {
  let table = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let k = 0; k < 8; k++) {
      c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
    }
    table[i] = c;
  }
  let crc = -1;
  for (let i = 0; i < buf.length; i++) {
    crc = (crc >>> 8) ^ table[(crc ^ buf[i]) & 0xFF];
  }
  return (crc ^ -1) >>> 0;
}

function createChunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length, 0);
  const typeBuf = Buffer.from(type, 'ascii');
  const body = Buffer.concat([typeBuf, data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body), 0);
  return Buffer.concat([len, body, crc]);
}

function generatePng(size, isMaskable = false) {
  // Generate RGBA buffer
  const width = size;
  const height = size;
  const rawData = Buffer.alloc(height * (1 + width * 4));

  // Colors: NexHaat Blue #0A66C2 (10, 102, 194), Deep Blue #074F96 (7, 79, 150), Accent Orange #E8890C (232, 137, 12), White #FFFFFF
  const cx = width / 2;
  const cy = height / 2;
  const margin = isMaskable ? width * 0.15 : width * 0.05;
  const boxRadius = (width - margin * 2) / 2;

  let offset = 0;
  for (let y = 0; y < height; y++) {
    rawData[offset++] = 0; // Filter type 0 (None)
    for (let x = 0; x < width; x++) {
      const dx = x - cx;
      const dy = y - cy;
      const dist = Math.sqrt(dx * dx + dy * dy);

      let r = 244, g = 246, b = 248, a = 255; // Background canvas

      if (isMaskable) {
        // Full bleed background for maskable
        const grad = y / height;
        r = Math.round(10 * (1 - grad) + 7 * grad);
        g = Math.round(102 * (1 - grad) + 79 * grad);
        b = Math.round(194 * (1 - grad) + 150 * grad);
        a = 255;
      }

      // Rounded tile inside
      const nx = Math.abs(dx);
      const ny = Math.abs(dy);
      const cornerR = boxRadius * 0.35;
      const innerW = boxRadius - cornerR;
      const inBox = (nx <= innerW && ny <= boxRadius) ||
                    (ny <= innerW && nx <= boxRadius) ||
                    (nx > innerW && ny > innerW && Math.sqrt((nx - innerW) ** 2 + (ny - innerW) ** 2) <= cornerR);

      if (inBox) {
        const grad = (y - (cy - boxRadius)) / (boxRadius * 2);
        // Gradient tile: #0ea5e9 to #074f96
        r = Math.round(14 * (1 - grad) + 7 * grad);
        g = Math.round(165 * (1 - grad) + 79 * grad);
        b = Math.round(233 * (1 - grad) + 150 * grad);
        a = 255;

        // Draw "N" logo letter in white inside center
        const lx = dx / (boxRadius * 0.65);
        const ly = dy / (boxRadius * 0.65);
        const stemW = 0.22;
        const inLeftStem = (lx >= -0.7 && lx <= -0.7 + stemW && ly >= -0.7 && ly <= 0.7);
        const inRightStem = (lx >= 0.7 - stemW && lx <= 0.7 && ly >= -0.7 && ly <= 0.7);
        // Diagonal: from (-0.7, -0.7) to (0.7, 0.7)
        const diagDist = Math.abs(ly - lx) / Math.SQRT2;
        const inDiag = (diagDist <= stemW * 0.75 && lx >= -0.7 && lx <= 0.7 && ly >= -0.7 && ly <= 0.7);

        if (inLeftStem || inRightStem || inDiag) {
          r = 255; g = 255; b = 255;
        }

        // Orange accent dot (representing hyper-local haat sun/orbit)
        const dotDx = dx - boxRadius * 0.55;
        const dotDy = dy - (-boxRadius * 0.55);
        if (Math.sqrt(dotDx * dotDx + dotDy * dotDy) <= boxRadius * 0.16) {
          r = 232; g = 137; b = 12; // Orange
        }
      }

      rawData[offset++] = r;
      rawData[offset++] = g;
      rawData[offset++] = b;
      rawData[offset++] = a;
    }
  }

  // PNG Header
  const header = Buffer.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]);

  // IHDR
  const ihdrData = Buffer.alloc(13);
  ihdrData.writeUInt32BE(width, 0);
  ihdrData.writeUInt32BE(height, 4);
  ihdrData[8] = 8; // 8 bits per channel
  ihdrData[9] = 6; // RGBA
  ihdrData[10] = 0; // Deflate
  ihdrData[11] = 0; // Filter
  ihdrData[12] = 0; // No interlace
  const ihdrChunk = createChunk('IHDR', ihdrData);

  // IDAT
  const compressed = zlib.deflateSync(rawData);
  const idatChunk = createChunk('IDAT', compressed);

  // IEND
  const iendChunk = createChunk('IEND', Buffer.alloc(0));

  return Buffer.concat([header, ihdrChunk, idatChunk, iendChunk]);
}

const pubDir = path.resolve(__dirname, '../public');
fs.writeFileSync(path.join(pubDir, 'pwa-192x192.png'), generatePng(192, false));
fs.writeFileSync(path.join(pubDir, 'pwa-512x512.png'), generatePng(512, false));
fs.writeFileSync(path.join(pubDir, 'pwa-maskable-512x512.png'), generatePng(512, true));
fs.writeFileSync(path.join(pubDir, 'apple-touch-icon.png'), generatePng(180, false));

// Also write copy of icon.svg in public
const logoSvgPath = path.join(pubDir, 'logo.svg');
const iconSvgPath = path.join(pubDir, 'icon.svg');
if (fs.existsSync(logoSvgPath) && !fs.existsSync(iconSvgPath)) {
  fs.copyFileSync(logoSvgPath, iconSvgPath);
}

console.log('Generated all PWA compliant PNG icons in public/ successfully!');
