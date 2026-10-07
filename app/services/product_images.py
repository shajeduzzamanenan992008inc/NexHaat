"""Bounded, in-memory normalization for customer product-image search."""

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError


MAX_PRODUCT_IMAGE_BYTES = 5 * 1024 * 1024


class ProductImageError(ValueError):
    pass


def normalize_product_image(raw):
    if not raw or len(raw) > MAX_PRODUCT_IMAGE_BYTES:
        raise ProductImageError("The image is empty or larger than 5 MB.")
    try:
        image = Image.open(BytesIO(raw))
        image.verify()
        image = Image.open(BytesIO(raw))
        image_format = image.format
        if (image_format not in {"JPEG", "PNG", "WEBP"} or image.width > 8000
                or image.height > 8000 or image.width * image.height > 40_000_000):
            raise ProductImageError(
                "Use a JPEG, PNG, or WebP image under 8,000 × 8,000 pixels."
            )
        image = ImageOps.exif_transpose(image)
        image.thumbnail((1024, 1024))
        output = BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=78, optimize=True)
        return output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError) as error:
        if isinstance(error, ProductImageError):
            raise
        raise ProductImageError("The uploaded file is not a valid product image.") from None
