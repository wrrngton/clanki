# import base64, io
# from PIL import Image
#
# def validate_base64_image(b64: str, claimed_mime: str):
#     if b64.startswith("data:"):
#         b64 = b64.split(",", 1)[1]
#
#     try:
#         raw = base64.b64decode(b64, validate=True)
#     except Exception as e:
#         raise ValueError(f"Invalid base64: {e}")
#
#     try:
#         im = Image.open(io.BytesIO(raw))
#         im.verify()
#         fmt = (im.format or "").lower()
#     except Exception as e:
#         raise ValueError(f"Corrupt/unreadable image bytes: {e}")
#
#     expected = {"jpeg":"image/jpeg","jpg":"image/jpeg","png":"image/png","gif":"image/gif","webp":"image/webp"}.get(fmt, None)
#     if expected and expected != claimed_mime.lower():
#         raise ValueError(f"MIME mismatch: claimed {claimed_mime}, detected {expected}")
#
#     return b64
#
import base64
import io

import filetype
from PIL import Image, UnidentifiedImageError


def detected_mime_from_b64(b64: str) -> str | None:
    kind = filetype.guess(base64.b64decode(b64, validate=True))
    return kind.mime if kind else None


def is_valid_base64_image(b64: str, mime_type: str) -> bool:

    sniffed_mime_type = detected_mime_from_b64(b64)

    if sniffed_mime_type is None or sniffed_mime_type != mime_type:
        return False

    if b64.startswith("data:"):
        b64 = b64.split(",", 1)[1]
    try:
        raw = base64.b64decode(b64, validate=True)
        with Image.open(io.BytesIO(raw)) as im:
            im.verify()
        return True
    except (ValueError, UnidentifiedImageError, OSError):
        return False
