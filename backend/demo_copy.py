from __future__ import annotations

from pathlib import Path

import cv2


def create_controlled_copy(source_path: str | Path, output_path: str | Path) -> Path:
    """Create a visible, lossy test copy for an owned-content demo."""
    source = Path(source_path)
    target = Path(output_path)
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise ValueError("Could not open the original video to create a test copy.")

    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(capture.get(cv2.CAP_PROP_FPS)) or 24.0
    if width < 32 or height < 32:
        capture.release()
        raise ValueError("Video dimensions are too small to create a transformed test copy.")

    target.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(target), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        capture.release()
        raise ValueError("Could not create the transformed MP4 test copy.")

    crop_x = max(2, int(width * 0.045))
    crop_y = max(2, int(height * 0.045))
    overlay_height = max(24, int(height * 0.07))
    text_scale = max(0.38, min(0.85, width / 1200))
    frame_count = 0

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            cropped = frame[crop_y : height - crop_y, crop_x : width - crop_x]
            transformed = cv2.resize(cropped, (width, height), interpolation=cv2.INTER_LINEAR)
            watermark = transformed.copy()
            cv2.rectangle(watermark, (0, height - overlay_height), (width, height), (12, 24, 20), -1)
            cv2.putText(
                watermark,
                "CONTROLLED TEST COPY",
                (max(12, int(width * 0.025)), height - max(8, int(overlay_height * 0.28))),
                cv2.FONT_HERSHEY_SIMPLEX,
                text_scale,
                (220, 238, 228),
                max(1, int(text_scale * 2)),
                cv2.LINE_AA,
            )
            writer.write(cv2.addWeighted(watermark, 0.24, transformed, 0.76, 0))
            frame_count += 1
    finally:
        capture.release()
        writer.release()

    if not frame_count or not target.exists() or target.stat().st_size == 0:
        target.unlink(missing_ok=True)
        raise ValueError("No usable frames were found in the original video.")

    return target
