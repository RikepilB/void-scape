"""Create local synthetic original/crop evidence for screenshot scope QA."""
import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path


def png(width, rows):
    def chunk(kind, payload):
        return (struct.pack(">I", len(payload)) + kind + payload
                + struct.pack(">I", zlib.crc32(kind + payload)))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, len(rows), 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(b"\x00" + row for row in rows)))
            + chunk(b"IEND", b""))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    rows = [bytes((20, 170, 70)) * 320] * 120 + [bytes((220, 30, 40)) * 320] * 120
    original = png(320, rows)
    crop = png(320, rows[:120])
    original_hash = hashlib.sha256(original).hexdigest()
    for name, payload, height, mode, parent in (
        ("01-original.png", original, 240, "viewport", None),
        ("02-crop.png", crop, 120, "crop",
         {"sha256": original_hash, "pixels": {"width": 320, "height": 240}}),
    ):
        (args.out / name).write_bytes(payload)
        data = {
            "version": 1, "image_sha256": hashlib.sha256(payload).hexdigest(),
            "producer": {"name": "synthetic-fixture", "version": "1"},
            "observed_at": None, "source_url": None, "final_url": None,
            "viewport": {"width": 320, "height": 240},
            "pixels": {"width": 320, "height": height}, "scale": 1,
            "mode": mode,
            "region": {"x": 0, "y": 0, "width": 320, "height": 120} if parent else None,
            "readiness_warnings": ["unknown"], "content_trust": "untrusted",
            "derived_from": parent,
        }
        (args.out / (name + ".capture.json")).write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("Created synthetic green/red original and green-only crop; no website was captured.")


if __name__ == "__main__":
    main()
