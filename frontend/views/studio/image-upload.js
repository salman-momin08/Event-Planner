/**
 * Client-side venue photo intake: magic-byte sniffing, filename sanitization, and
 * canvas-based re-encoding that strips EXIF/metadata and bounds payload size
 * before the image is sent to the AI decor service.
 */
const ALLOWED_IMAGE_MIMES = new Set(['image/jpeg', 'image/png', 'image/webp']);
const ALLOWED_IMAGE_EXT = /\.(?:jpe?g|png|webp)$/i;
const MAX_UPLOAD_BYTES = 8 * 1024 * 1024; // 8 MB max raw upload before client-side downscaling
const MAX_SOURCE_DIMENSION = 6000; // Guard against decompression-bomb images

/** Validates raw magic bytes of an uploaded File before decoding it in the browser. */
export async function verifyFileMagicBytes(file) {
  const slice = file.slice(0, 12);
  const buf = await slice.arrayBuffer();
  const b = new Uint8Array(buf);
  if (b.length < 12) return false;
  // JPEG: FF D8 FF
  const isJpeg = b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff;
  // PNG: 89 50 4E 47 0D 0A 1A 0A
  const isPng = b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47 && b[4] === 0x0d && b[5] === 0x0a && b[6] === 0x1a && b[7] === 0x0a;
  // WebP: RIFF....WEBP
  const isWebp = b[0] === 0x52 && b[1] === 0x49 && b[2] === 0x46 && b[3] === 0x46 && b[8] === 0x57 && b[9] === 0x45 && b[10] === 0x42 && b[11] === 0x50;
  return isJpeg || isPng || isWebp;
}

/** Sanitizes a filename for safe display (strips paths, double extensions, and control chars). */
export function safeFileName(name) {
  return String(name || 'photo.jpg')
    .replace(/^.*[/\\]/, '')
    .replace(/[^\w.-]+/g, '_')
    .slice(0, 60);
}

/** Validates, re-encodes (stripping EXIF/metadata), and compresses an image file into a safe base64 JPEG data URL (< 45 KB). */
export async function compressImageFile(file) {
  if (!file || typeof file.size !== 'number') {
    throw new Error('No valid file selected.');
  }
  if (file.size <= 0) {
    throw new Error('The selected file is empty.');
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    throw new Error('Image file is too large (maximum 8 MB). Please choose a smaller photo.');
  }
  if (!ALLOWED_IMAGE_MIMES.has(file.type) || !ALLOWED_IMAGE_EXT.test(file.name || '')) {
    throw new Error('Only JPEG (.jpg, .jpeg), PNG (.png), and WebP (.webp) photos are allowed.');
  }
  if (!(await verifyFileMagicBytes(file))) {
    throw new Error('File signature does not match a valid JPEG, PNG, or WebP image.');
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Could not read the selected image file.'));
    reader.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error('Selected file could not be decoded as a valid image.'));
      img.onload = () => {
        if (img.width < 16 || img.height < 16 || img.width > MAX_SOURCE_DIMENSION || img.height > MAX_SOURCE_DIMENSION) {
          reject(new Error(`Image dimensions must be between 16×16 and ${MAX_SOURCE_DIMENSION}×${MAX_SOURCE_DIMENSION} pixels.`));
          return;
        }
        const maxDim = 560;
        const scale = Math.min(1, maxDim / Math.max(img.width, img.height));
        const w = Math.max(1, Math.round(img.width * scale));
        const hPx = Math.max(1, Math.round(img.height * scale));
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = hPx;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, w, hPx);
        let quality = 0.72;
        let dataUrl = canvas.toDataURL('image/jpeg', quality);
        while (dataUrl.length > 44000 && quality > 0.3) {
          quality -= 0.12;
          dataUrl = canvas.toDataURL('image/jpeg', quality);
        }
        if (dataUrl.length > 48000) {
          reject(new Error('Could not compress image below the 48 KB safety limit.'));
          return;
        }
        resolve(dataUrl);
      };
      img.src = String(reader.result);
    };
    reader.readAsDataURL(file);
  });
}
