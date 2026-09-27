from __future__ import annotations

import logging
import re
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.exceptions import ParamInvalidError, UnauthorizedError
from app.repositories import UserRepository

logger = logging.getLogger(__name__)

MAX_AVATAR_BYTES = 2 * 1024 * 1024
MAX_AVATAR_PIXELS = 16_000_000
AVATAR_FILENAME = re.compile(r"[1-9][0-9]*_[0-9a-f]{32}\.png")


def get_avatar_path(filename: str) -> Path | None:
    if not AVATAR_FILENAME.fullmatch(filename):
        return None
    return settings.AVATAR_UPLOAD_DIR / filename


def _encode_avatar(content: bytes) -> bytes:
    if not content or len(content) > MAX_AVATAR_BYTES:
        raise ParamInvalidError(message="头像不能为空，且不能超过 2MB")
    try:
        with Image.open(BytesIO(content), formats=("JPEG", "PNG", "WEBP")) as image:
            if image.width * image.height > MAX_AVATAR_PIXELS:
                raise ParamInvalidError(message="头像分辨率过大，请选择较小的图片")
            image.verify()
        with Image.open(BytesIO(content), formats=("JPEG", "PNG", "WEBP")) as image:
            image = ImageOps.exif_transpose(image).convert("RGBA")
            image.thumbnail((512, 512), Image.Resampling.LANCZOS)
            # Re-encode pixels only, stripping EXIF and other uploaded metadata.
            clean_image = Image.new("RGBA", image.size)
            clean_image.paste(image)
            output = BytesIO()
            clean_image.save(output, format="PNG")
            return output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ParamInvalidError(message="请选择有效的 JPG、PNG 或 WebP 图片") from exc


def _write_avatar(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _remove_avatar(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove avatar file %s", path.name, exc_info=True)


async def save_avatar(user_id: int, content: bytes) -> str:
    user = await UserRepository.get_by_id(user_id)
    if not user:
        raise UnauthorizedError(message="用户不存在，请重新登录")
    encoded = await run_in_threadpool(_encode_avatar, content)
    filename = f"{user_id}_{uuid4().hex}.png"
    path = settings.AVATAR_UPLOAD_DIR / filename
    url_prefix = f"{settings.API_V1_PREFIX}/user/avatars/"
    avatar_url = f"{url_prefix}{filename}"
    try:
        await run_in_threadpool(_write_avatar, path, encoded)
        await UserRepository.update_profile(user_id, nickname=None, avatar_url=avatar_url)
    except Exception:
        await run_in_threadpool(_remove_avatar, path)
        raise

    old_url = user.get("avatar_url") or ""
    if old_url.startswith(url_prefix):
        old_filename = old_url[len(url_prefix):]
        old_path = get_avatar_path(old_filename)
        # Never delete external images or files belonging to another user.
        if old_path and old_filename.startswith(f"{user_id}_"):
            await run_in_threadpool(_remove_avatar, old_path)
    return avatar_url
