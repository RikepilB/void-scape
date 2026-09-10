# Images and carousels

The image reader prepares deterministic local evidence without OCR or cloud processing.

**Status:** `shipped`

[Back to agent docs](../index.md) · Entry points:
[`voidscape.py`](../../../skill/scripts/voidscape.py), [`image.py`](../../../skill/scripts/image.py)

## Inputs and limits

- One local `.jpg`, `.jpeg`, `.png`, or `.webp` file.
- One local folder treated as a non-recursive carousel.
- Natural filename order with deterministic tie breaking.
- Maximum 100 accepted images.
- Symlinks, nested directories, unsupported files, and animated images are rejected or reported
  according to the probe result.

The reader copies accepted bytes; it does not resize, transcode, OCR, caption, or modify originals.

## Optional screenshot provenance (version 1)

Place `shot.png.capture.json` beside a selected `shot.png` (same rule for JPEG/WebP).
Plain images need no sidecar. Inspect and preview report missing provenance explicitly; read
retains sanitized claims in each manifest image's `provenance`. This extension is implemented
here; release status still requires merge through a supported entry point.

```json
{
  "version": 1,
  "image_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
  "producer": {"name": "example-capture", "version": "1.0"},
  "observed_at": null,
  "source_url": "https://example.com",
  "final_url": null,
  "viewport": {"width": 800, "height": 600},
  "pixels": {"width": 800, "height": 600},
  "scale": 1,
  "mode": "viewport",
  "region": null,
  "readiness_warnings": ["unknown"],
  "content_trust": "untrusted",
  "derived_from": null
}
```

Replace the placeholder hash with the actual image SHA-256. All keys shown are required; unknown
keys/versions, duplicate keys, invalid UTF-8/JSON, symlink sidecars, mismatched hashes/dimensions,
invalid geometry and metadata over 16 KiB are rejected. No metadata path fields are supported.
Producer identifiers are limited to 64 ASCII letters/digits/dots/underscores/hyphens. Time is a
timezone-aware ISO timestamp or `null` (unknown). Dimensions are positive integers up to one
million; scale is finite and greater than zero, at most 16. Viewport dimensions are CSS pixels;
image dimensions and region coordinates are device pixels. A viewport capture must match
viewport × scale, allowing one pixel of rounding.

Modes: `viewport`, `full_page`, `region`, `crop`, `unknown`. Region/crop require an `x`, `y`,
`width`, `height` object with nonnegative integer coordinates and dimensions matching the image.
Only crop accepts/requires `derived_from`, containing `sha256` and `pixels` of the claimed
original; the crop must fit inside those dimensions. This identifies a derivative without
opening an arbitrary parent path. To retain the actual original as evidence, select it alongside
the crop; a parent hash alone does not mean the original was supplied or verified. No crop is
created by this reader, and every selected original is preserved byte-for-byte.

Readiness warnings are bounded codes: `unknown`, `fonts_pending`, `images_pending`,
`animation_active`, `timeout`, `partial_capture`, `occluded`. Free-form instructions are rejected.
Source/final URLs are HTTP(S) or `null`; only their origins survive import. Userinfo, paths,
queries and fragments are removed because all can contain secrets. Keep secrets out of producer
identifiers and hostnames too: this is not a general secret detector. Raw sidecars are neither
copied into the bundle nor modified. URLs are never fetched and metadata is never executed.

`importer_verified` contains only the image hash and measured pixel dimensions. Everything in
`producer_claims` remains untrusted, including time, viewport, readiness and parent identity.
Hash agreement proves byte association, not producer authentication, semantic correctness,
page completeness or hidden content. `coverage` stays `unknown`, even for `full_page` claims.
Failed copy/hash/dimension checks never produce a completed manifest; partial files may remain
in the failed workdir for diagnosis. No capture tool installation or browser access is involved.

## Guided use

```powershell
voidscape inspect "slides"
voidscape preview "slides"
voidscape read "slides" --workdir image-evidence
```

Image preview estimates agent vision/output-token cost. It requires no cloud or model-download
approval because evidence preparation is a local byte copy.

## Raw protocol

```powershell
python skill/scripts/image.py manifest --compact
python skill/scripts/image.py probe "slides" --envelope --compact
python skill/scripts/image.py estimate "slides" --envelope --compact
python skill/scripts/image.py run "slides" --workdir image-evidence --envelope --compact
```

`run` writes `manifest.json` and ordered files under `images/`. Use a new empty workdir.

## Citation contract

Cite exactly `[image 1]`, `[image 2]`, and so on, using manifest order. Do not invent timestamps,
OCR text, hidden frames, or motion. If two images are near-identical, say so.

Canonical details: [image/carousel design](../../superpowers/specs/2026-07-21-image-carousel-reader-design.md)
and [`tests/test_image_reader.py`](../../../tests/test_image_reader.py).
