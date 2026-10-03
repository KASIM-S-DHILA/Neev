"""Isolated low-resolution change analysis, never a speech or OCR model."""
import json
import sys
from pathlib import Path


def main():
    import cv2
    import numpy as np
    import scenedetect
    from scenedetect import ContentDetector, FrameTimecode
    from .resource_guard import private_bytes
    cv2.setNumThreads(1)
    folder = Path(sys.argv[1])
    request = json.loads((folder / "selection.json").read_text("utf-8"))
    config = request["config"]
    if scenedetect.__version__ != config["scenedetect"]:
        raise ValueError("Scene detector version changed; install pinned dependencies")
    detector = ContentDetector(threshold=config["scene_threshold"], min_scene_len=.5)
    def thumbnail(path):
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError("Frame preview cannot be decoded")
        return cv2.resize(image, (320, 180), interpolation=cv2.INTER_AREA)
    previous = request["previous"]
    last = thumbnail(previous["path"]) if previous else None
    last_time = previous["seconds"] if previous else None
    if previous:
        detector.process_frame(FrameTimecode(float(last_time), 1000.0), last)
    useful = []
    for item in request["frames"]:
        image = thumbnail(folder / item["file"])
        cut = bool(detector.process_frame(FrameTimecode(float(item["seconds"]), 1000.0), image))
        changed = float(np.mean(np.max(np.abs(image.astype(np.int16) - last.astype(np.int16)), axis=2) > config["pixel_delta"])) if last is not None else 1.0
        reasons = []
        if last is None:
            reasons.append("first_frame")
        elif changed >= config["changed_pixel_fraction"]:
            reasons.append("visual_change")
            if cut:
                reasons.append("sampled_scene_change")
        elif item["seconds"] - last_time >= config["max_duplicate_seconds"]:
            reasons.append("periodic_reference")
        if reasons:
            useful.append(item | {"reasons": reasons, "changed_fraction": round(changed, 6)})
            last, last_time = image, item["seconds"]
    # Uniformly spread retained candidates within the window when its share of
    # the budget is exceeded. Keep both ends when at least two slots remain.
    quota = request["quota"]
    selected = useful
    if len(useful) > quota:
        indices = np.linspace(0, len(useful) - 1, num=quota, dtype=int)
        selected = [useful[int(i)] for i in indices]
    print(json.dumps({"selected": selected, "omitted": len(useful) - len(selected), "private_bytes_after": private_bytes()}))


if __name__ == "__main__":
    main()
