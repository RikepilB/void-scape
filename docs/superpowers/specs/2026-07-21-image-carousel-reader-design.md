# Local image and carousel reader design

**Date:** 2026-07-21  
**Status:** Shipped in PR #9 (merged 2026-08-28)
**Branch:** merged to `main` via PR #9

## Goal

Extend Voidscape's local-first evidence workflow from video/audio to one local image or one local
folder treated as a filename-ordered carousel. Preserve `inspect -> preview -> read`, agent-readable
artifacts, cost visibility, and the existing JSON envelope.

## Scope

Version 1 accepts:

- one local `.jpg`, `.jpeg`, `.png`, or `.webp` file; or
- one local directory whose supported regular files form one carousel.

Directory enumeration is non-recursive and naturally sorted by filename, case-insensitively with
numeric runs compared as integers. Example: `slide1.png`, `slide2.png`, `slide10.png`.

Version 1 excludes public URL downloads, platform carousel capture, OCR, captions, generated
summaries, cloud processing, model downloads, recursive folders, visual deduplication, animated
images, HEIC/TIFF/BMP support, and a generic media-reader or source-adapter interface.

## Architecture

Add one concrete engine at `skill/scripts/image.py`. It exposes Python functions and a raw CLI with
the same command vocabulary as the video engine:

```text
image.py manifest
image.py probe <input>
image.py estimate <input>
image.py run <input> [--workdir PATH]
```

Raw commands support the existing `--human`, `--envelope`, and `--compact` output modes and protocol
version `1.0`. `image.py` directly reuses `video.load_pricing`, `video.per_frame_tokens`, and the
existing internal envelope/error helpers. This deliberate sibling dependency is smaller than a new
shared layer and can be revisited after a second reader exists.

`skill/scripts/voidscape.py` detects a local directory or known image extension and dispatches its
existing `inspect`, `preview`, and `read` commands to `image.py`. Supported extensions are `.jpg`,
`.jpeg`, `.png`, and `.webp`. Known-but-rejected extensions `.gif`, `.bmp`, `.tif`, `.tiff`, `.heic`,
`.heif`, and `.avif` also route to `image.py` so users get a clear unsupported-format error. All
other inputs continue through `video.py`. `video.py` behavior and public contract remain unchanged.

## Source discovery and ordering

`probe(input)` resolves the path without network access. A directory scan:

1. examines direct children only;
2. skips directories and symlinks;
3. records unsupported regular files in `skipped`;
4. sorts supported files using natural filename order;
5. validates each supported file and reads width, height, and available frame-count metadata through
   existing `ffprobe` tooling;
6. reports whether the 100-image processing limit is satisfied.

A supported extension with invalid image bytes is an input error naming that file. A file reported
as multi-frame is rejected as animated input. An unsupported single file is an input error rather
than a video fallback in the raw image CLI. Guided dispatch uses the explicit extension sets above.

Probe data shape:

```json
{
  "input": "C:/carousel",
  "source": "local",
  "kind": "carousel",
  "item_count": 3,
  "within_limit": true,
  "images": [
    {"index": 1, "source": "C:/carousel/slide1.png", "source_name": "slide1.png", "width": 1080, "height": 1350, "bytes": 12345}
  ],
  "skipped": [
    {"name": "notes.txt", "reason": "unsupported"}
  ]
}
```

For one file, `kind` is `image`, `item_count` is `1`, and `skipped` is empty.

## Preview and cost gate

`estimate(input, out_words=600, agent_model=None)` calls `probe`, then reuses Voidscape's active
vision estimator and pricing file. Image tokens are the sum of per-image estimates because carousel
items may have different aspect ratios. The gate adds the existing 2,000-token prompt overhead and
estimated output tokens.

The result keeps familiar fields:

- `tokens.images`, `tokens.output`, `tokens.overhead`, and `tokens.read_total`;
- `cost_usd.transcription = 0`, plus agent and total estimates;
- `free = true`, meaning no out-of-pocket transcription or processing charge;
- `requires_cloud_approval = false`;
- `needs_model_download = false`;
- `needs_install = false` when the existing FFmpeg/FFprobe baseline is available;
- `agent_model`, `vision_estimator`, and `cost_basis`.

`probe` may report more than 100 images so `inspect` remains informative. `estimate` and `run` reject
more than 100 items with an input error instructing the user to choose a narrower folder.

## Read and evidence bundle

`run(input, workdir=None)` performs no network action and never modifies originals.

1. Probe and validate the complete selected set.
2. Reject a requested workdir that already contains any entry.
3. Create `workdir/images/`.
4. Copy original bytes with `shutil.copy2`, prefixing natural order:
   `001-slide1.png`, `002-slide2.png`, `003-slide10.png`.
5. Write `manifest.json` only after every copy succeeds.

Manifest data shape:

```json
{
  "workdir": "C:/output",
  "kind": "carousel",
  "source": "C:/carousel",
  "item_count": 3,
  "images": [
    {"index": 1, "file": "C:/output/images/001-slide1.png", "source_name": "slide1.png", "width": 1080, "height": 1350, "bytes": 12345}
  ],
  "skipped": []
}
```

Copied images preserve file format and resolution. No resize, recompression, OCR, or semantic output
occurs. If copying or manifest writing fails, command exits as an operation failure and never claims
success; partial files may remain for diagnosis, but no successful manifest exists.

Agent answers refer to carousel evidence as `[image 1]`, `[image 2]`, and so on. Image evidence never
uses fabricated video timestamps. The CLI creates evidence only; an agent authors any Markdown note.

## Error contract

Raw CLI failures use the existing envelope shape:

```json
{"ok":false,"data":null,"error":{"code":"input_error","message":"...","retryable":false,"exit_code":3},"meta":{"command":"probe","protocol_version":"1.0"}}
```

- Exit `3`: missing input, unsupported single file, no supported images, corrupt/unreadable image,
  more than 100 images, or non-empty workdir.
- Exit `5`: FFprobe dependency unavailable when dimensions cannot be inspected.
- Exit `6`: copy, directory creation, or manifest write failure.
- Exit `1`: uncategorized unexpected failure.

Unsupported files and symlinks inside a valid folder are reported in `skipped` and do not fail the
carousel. Originals are never renamed, deleted, rewritten, or traversed recursively.

## Tests

Add focused tests using tiny repository-generated image bytes and temporary directories:

1. natural order is `slide1`, `slide2`, `slide10`;
2. supported single files and mixed folders probe correctly;
3. unsupported files and symlinks are skipped and reported;
4. missing, empty, unsupported, corrupt, and over-100 inputs return exit `3`;
5. estimate sums per-image tokens and reports zero cloud/model approval requirements;
6. run copies ordered original bytes, writes the documented manifest, and leaves sources unchanged;
7. non-empty workdir fails before evidence copy;
8. raw `manifest`, envelope, compact JSON, and exit-code behavior match protocol `1.0`;
9. guided `inspect`, `preview`, and `read` dispatch images without changing video behavior;
10. full `python -m pytest -q -p no:cacheprovider` passes;
11. installer tests confirm the image engine is copied into both supported skill roots;
12. existing video demo fixture still passes `inspect -> preview -> read`.

## Demo

After implementation passes, update `docs/demo-shot-list.md` with a 45-60 second OpenScreen CLI
sequence:

1. show naturally named carousel files;
2. run `inspect` and show deterministic order;
3. run `preview` and show local/free gates plus token estimate;
4. run `read` and open the ordered manifest/images;
5. show an agent answer citing `[image 1]` and `[image 2]`.

Recording and editing remain manual. Review recorded footage against the shot list through
Voidscape/read-video's visual tier.

## Delivery order after this milestone

1. Private YouTube queue capture through a user-owned playlist.
2. Local/article URL and RSS intake as a separate text reader, not through `video.py`.
3. A reusable adapter interface extracted only after concrete implementations reveal shared
   behavior.
