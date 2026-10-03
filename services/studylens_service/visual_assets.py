"""Small immutable derived previews. The API never exposes filesystem paths."""
import base64
import hashlib
import io
import os

ASSET_MAX_BYTES = 512 * 1024


def save_preview(root, image, caption):
    from PIL import Image
    converted = image.convert("RGB")
    converted.thumbnail((1400, 1400))
    try:
        while True:
            buffer = io.BytesIO()
            converted.save(buffer, format="PNG")
            data = buffer.getvalue()
            if len(data) <= ASSET_MAX_BYTES:
                break
            converted.thumbnail((max(1, int(converted.width * .75)), max(1, int(converted.height * .75))))
        digest = hashlib.sha256(data).hexdigest()
        relative = f"derived/{digest[:2]}/{digest}.png"
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        existing = b""
        if target.exists():
            with target.open("rb") as stream:
                existing = stream.read(ASSET_MAX_BYTES + 1)
        if hashlib.sha256(existing).hexdigest() != digest:
            # One heavy worker owns writes. A crash before replace leaves no referenced preview.
            temporary = target.with_suffix(".part")
            with temporary.open("wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        return {"path": relative, "sha256": digest, "caption": caption,
            "width": converted.width, "height": converted.height}
    finally:
        converted.close()


def public_assets(root, metadata):
    result = dict(metadata)
    if metadata.get("audio"):
        from .audio import public_audio
        result["audio"] = public_audio(root, metadata["audio"])
    result["assets"] = []
    for asset in metadata.get("assets", [])[:4]:
        public = {key: asset[key] for key in ("sha256", "caption", "width", "height") if key in asset}
        target = (root / asset.get("path", "")).resolve()
        try:
            if not target.is_relative_to((root / "derived").resolve()) or target.stat().st_size > ASSET_MAX_BYTES:
                raise ValueError("Invalid preview")
            with target.open("rb") as stream:
                data = stream.read(ASSET_MAX_BYTES + 1)
            if hashlib.sha256(data).hexdigest() != asset.get("sha256"):
                raise ValueError("Damaged preview")
            public["data_url"] = "data:image/png;base64," + base64.b64encode(data).decode("ascii")
        except (OSError, ValueError):
            public["error"] = "Preview missing or damaged. The original is retained; process visuals again to regenerate it."
        result["assets"].append(public)
    return result
