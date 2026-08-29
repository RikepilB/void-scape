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

## Guided use

```powershell
python skill/scripts/voidscape.py inspect "slides"
python skill/scripts/voidscape.py preview "slides"
python skill/scripts/voidscape.py read "slides" --workdir image-evidence
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
