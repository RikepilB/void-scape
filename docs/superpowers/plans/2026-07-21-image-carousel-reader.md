# Image and Carousel Reader Implementation Plan

**Status:** Shipped in PR #9 (merged 2026-08-28)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

Historical RED checkpoints from the original implementation are retained below without checkboxes and
explicitly labeled as intentionally unperformed. They document the intended pre-implementation sequence;
they are not pending release work and cannot be recreated after the implementation exists.

**Goal:** Add local single-image and filename-ordered carousel evidence preparation to Voidscape's existing `inspect -> preview -> read` workflow.

**Architecture:** Add a focused sibling engine, `skill/scripts/image.py`, with the same `manifest`, `probe`, `estimate`, and `run` shape as `video.py`. The guided CLI dispatches local directories and recognized image extensions to this engine while leaving all existing video/audio/URL behavior unchanged.

**Tech Stack:** Python 3.10+ standard library, existing FFprobe baseline, pytest, PowerShell and Bash installers.

## Global Constraints

- Local inputs only: one image file or one non-recursive directory treated as one carousel.
- Supported formats: static JPG/JPEG, PNG, and WebP. Every selected file must report exactly one
  FFprobe read frame; animated APNG/WebP and recognized unsupported formats receive an input error.
- Natural filename order is mandatory (`slide1`, `slide2`, `slide10`), with a hard 100-image ceiling for `estimate` and `run`.
- Do not add OCR, cloud calls, URL acquisition, recursion, deduplication, resize/recompression, or a new dependency.
- Skip symlinks and unsupported directory entries; never modify source files.
- Preserve protocol version `1.0` and exit codes `0` through `6`.
- Do not change `video.py` behavior or weaken either privacy gate.
- Do not commit, push, deploy, or modify GitHub state without fresh explicit authorization.

---

### Task 1: Image input discovery and probing

**Files:**
- Create: `skill/scripts/image.py`
- Create: `tests/test_image_reader.py`

**Interfaces:**
- Produces: `is_image_input(value: str) -> bool`, `probe(inp: str) -> dict[str, Any]`.
- `probe` returns `source`, `input`, `kind`, `item_count`, `within_limit`, `images`, and `skipped`.
- Each image record contains `index`, `source`, `source_name`, `width`, `height`, and `bytes`.

- [x] **Step 1: Write failing discovery tests**

Add a tiny valid PNG byte fixture and tests proving:

```python
def test_probe_orders_directory_naturally(tmp_path):
    carousel = tmp_path / "carousel"
    carousel.mkdir()
    for name in ("slide10.png", "slide2.png", "slide1.png"):
        (carousel / name).write_bytes(PNG_1X1)
    result = image.probe(str(carousel))
    assert [item["source_name"] for item in result["images"]] == [
        "slide1.png", "slide2.png", "slide10.png",
    ]
    assert result["kind"] == "carousel"
    assert result["within_limit"] is True

def test_probe_skips_unsupported_entries_and_symlinks(tmp_path):
    # Create one valid PNG, one text file, and a symlink when the platform permits it.
    # Assert the valid file is selected and every ignored entry appears in `skipped`.
```

- **Historical RED checkpoint — intentionally unperformed: discovery**

Run: `python -m pytest tests/test_image_reader.py -v -p no:cacheprovider`

Expected: collection fails because `skill/scripts/image.py` does not exist.

- [x] **Step 3: Implement minimal discovery and probe behavior**

Create these constants and functions:

```python
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
REJECTED_EXTENSIONS = {".gif", ".bmp", ".tif", ".tiff", ".heic", ".heif", ".avif"}
MAX_IMAGES = 100

def _natural_key(
        path: Path,
) -> tuple[tuple[tuple[int, int | str], ...], str, str]:
    natural = tuple(
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in re.split(r"(\d+)", path.name)
    )
    return natural, path.name.casefold(), path.name

def is_image_input(value: str) -> bool:
    path = Path(value).expanduser()
    return path.is_dir() or path.suffix.casefold() in SUPPORTED_EXTENSIONS | REJECTED_EXTENSIONS

def _ffprobe_image(path: Path) -> tuple[int, int]:
    result = subprocess.run([
        "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,nb_read_frames", "-of", "json",
        str(path.resolve()),
    ], capture_output=True, text=True)
    stream = json.loads(result.stdout)["streams"][0]
    frame_value = stream.get("nb_read_frames")
    try:
        frame_count = int(frame_value)
    except (TypeError, ValueError) as ex:
        raise RuntimeError(
            f"ffprobe failed for {path.name}: expected exactly one frame, "
            f"reported {frame_value or 'unknown'}"
        ) from ex
    if frame_count != 1:
        raise RuntimeError(
            f"ffprobe failed for {path.name}: expected exactly one frame, "
            f"reported {frame_count}"
        )
    # Missing ffprobe raises RuntimeError("ffprobe is not installed").
    # Missing/non-numeric frame metadata, non-zero FFprobe results, corrupt media,
    # and any count other than one raise an input-classified RuntimeError.

def probe(inp: str) -> dict[str, Any]:
    # Resolve one file or enumerate one directory without recursion.
    # Reject a missing path, unsupported single file, empty supported set, or
    # corrupt selected image. Skip directory symlinks/unsupported entries.
    # Preserve total natural order and attach 1-based indexes after validation.
    return {
        # Existing source/input/kind/item_count fields...
        "within_limit": len(images) <= MAX_IMAGES,
        "images": images,
        "skipped": skipped,
    }
```

- [x] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_image_reader.py -v -p no:cacheprovider`

Expected: natural-order and skip-reporting tests pass.

### Task 2: Cost estimate, evidence copy, and raw agent CLI

**Files:**
- Modify: `skill/scripts/image.py`
- Modify: `tests/test_image_reader.py`

**Interfaces:**
- Produces: `estimate(inp: str, out_words: int = 600, agent_model: str | None = None) -> dict[str, Any]`.
- Produces: `run(inp: str, workdir: str | None = None) -> dict[str, Any]`.
- Produces: `main(argv: list[str] | None = None) -> int` with `manifest`, `probe`, `estimate`, and `run`.

- [x] **Step 1: Write failing estimate and run tests**

Add tests asserting:

```python
def test_estimate_sums_image_tokens_and_needs_no_approval(carousel):
    result = image.estimate(str(carousel), agent_model="gpt-5.6-terra")
    assert result["item_count"] == 3
    assert result["tokens"]["images"] == sum(
        item["tokens"] for item in result["images"]
    )
    assert result["requires_cloud_approval"] is False
    assert result["needs_model_download"] is False
    assert result["needs_install"] is False
    assert result["free"] is True

def test_estimate_rejects_negative_output_words(carousel):
    with pytest.raises(ValueError, match="out_words cannot be negative"):
        image.estimate(str(carousel), out_words=-1)

def test_estimate_uses_usd_contributions_for_dominant_cost(carousel):
    result = image.estimate(str(carousel), out_words=1000)
    assert result["tokens"]["overhead"] > result["tokens"]["output"]
    assert result["dominant_cost"] == "output"

def test_run_copies_ordered_original_bytes_and_writes_manifest(carousel, tmp_path):
    result = image.run(str(carousel), str(tmp_path / "out"))
    assert [Path(item["file"]).name for item in result["images"]] == [
        "001-slide1.png", "002-slide2.png", "003-slide10.png",
    ]
    assert json.loads((tmp_path / "out" / "manifest.json").read_text()) == result

def test_run_rejects_nonempty_workdir_before_copy(carousel, tmp_path):
    workdir = tmp_path / "out"
    workdir.mkdir()
    (workdir / "stale.txt").write_text("stale")
    with pytest.raises(ValueError, match="workdir already exists and is not empty"):
        image.run(str(carousel), str(workdir))
```

Also cover missing/empty/unsupported/corrupt/101-image inputs, unchanged originals, and absence of `manifest.json` when copying fails.

- **Historical RED checkpoint — intentionally unperformed: estimate and run**

Run: `python -m pytest tests/test_image_reader.py -v -p no:cacheprovider`

Expected: failures because `estimate`, `run`, and the raw CLI are absent.

- [x] **Step 3: Implement estimate and run**

Use the existing pricing helpers from sibling `video.py`:

```python
def estimate(inp: str, out_words: int = 600,
             agent_model: str | None = None) -> dict[str, Any]:
    if out_words < 0:
        raise ValueError("out_words cannot be negative")
    info = probe(inp)
    if info["item_count"] > MAX_IMAGES:
        raise ValueError("image input has more than 100 items; choose a narrower folder")
    pricing = video.load_pricing()
    selected_model, model_rate, estimator = video._agent_rate(pricing, agent_model)
    target_width = int(pricing.get("frame", {}).get("target_width", 512))
    # After computing image_tokens, overhead_tokens, and output_tokens:
    drivers_usd = {
        "images": image_tokens / 1e6 * model_rate["input"],
        "overhead": overhead_tokens / 1e6 * model_rate["input"],
        "output": output_tokens / 1e6 * model_rate["output"],
    }
    dominant_cost = max(drivers_usd, key=drivers_usd.get)
    # Return API-equivalent agent cost and explicit false approval/install gates.

def run(inp: str, workdir: str | None = None) -> dict[str, Any]:
    info = probe(inp)
    if info["item_count"] > MAX_IMAGES:
        raise ValueError("image input has more than 100 items; choose a narrower folder")
    # Validate an existing workdir is empty before mkdir/copy.
    # Copy with shutil.copy2 into images/ using 3-digit order prefixes.
    # Construct the final result only after all copies succeed, then write
    # manifest.json with UTF-8, indent=2, and a trailing newline.
```

If no workdir is supplied, use `tempfile.mkdtemp(prefix="voidscape-images-")`. Wrap copy/directory/manifest filesystem failures in `RuntimeError` so they map to exit `6`.

- [x] **Step 4: Add raw CLI and envelope behavior**

Reuse `video._AgentArgumentParser`, `video._emit`, `video._classify_error`, and protocol `1.0`. The manifest must declare only image-relevant flags:

```python
{
    "protocol_version": "1.0",
    "interactive": False,
    "commands": {
        "manifest": {"flags": ["--human", "--envelope", "--compact"]},
        "probe": {"flags": ["--human", "--envelope", "--compact"]},
        "estimate": {"flags": ["--out-words", "--agent-model", "--human", "--envelope", "--compact"]},
        "run": {"flags": ["--workdir", "--human", "--envelope", "--compact"]},
    },
}
```

Add subprocess tests for compact success, usage exit `2`, input exit `3`, dependency exit `5`, operation exit `6`, and envelope meta `{command, protocol_version}`.

- [x] **Step 5: Verify GREEN**

Run: `python -m pytest tests/test_image_reader.py -v -p no:cacheprovider`

Expected: all image engine tests pass.

### Task 3: Guided CLI dispatch

**Files:**
- Modify: `skill/scripts/voidscape.py`
- Modify: `tests/test_voidscape.py`

**Interfaces:**
- Consumes: `image.is_image_input`, `image.probe`, `image.estimate`, `image.run`.
- Existing commands and flags remain accepted; image inputs ignore video-only tier/backend/window flags and report image-specific output.

- [x] **Step 1: Write failing guided-flow tests**

Add tests for `inspect`, `preview`, and `read` on a directory plus regression tests proving an MP4 still calls `video.probe`, `video.estimate`, and `video.run`.

```python
def test_guided_image_read_dispatches_to_image_engine(carousel, tmp_path, capsys):
    workdir = tmp_path / "evidence"
    assert voidscape.main(["read", str(carousel), "--workdir", str(workdir)]) == 0
    output = capsys.readouterr().out
    assert "Images: 3" in output
    assert "[image 1]" in output
    assert (workdir / "manifest.json").exists()
```

- **Historical RED checkpoint — intentionally unperformed: guided dispatch**

Run: `python -m pytest tests/test_voidscape.py -v -p no:cacheprovider`

Expected: image directory is currently sent to `video.py` and fails.

- [x] **Step 3: Implement minimal dispatch**

Import `image as image_engine` and select it per input:

```python
def _is_image_source(value: str) -> bool:
    resolved = video.resolve_input(value)
    return image_engine.is_image_input(resolved)
```

In `inspect_source`, call the chosen engine and print image kind/count/order for image input. In
`preview`, apply the same workspace model fallback as video before estimating:

```python
configured_agent_model = (
    args.agent_model or _defaults(workspace)["agent_model"]
)
estimate = image_engine.estimate(
    args.input, args.out_words, configured_agent_model,
)
```

Print local/free token information. In `read`, call `image_engine.run(args.input, args.workdir)`
without evaluating cloud/model gates and print evidence guidance using `[image 1]` citations. Keep
the current video branches byte-for-byte behaviorally equivalent.

- [x] **Step 4: Verify GREEN and video regression**

Run: `python -m pytest tests/test_voidscape.py tests/test_privacy_gate.py tests/test_build_week_hardening.py -v -p no:cacheprovider`

Expected: all guided image and existing video/privacy tests pass.

### Task 4: Packaging and user/agent documentation

**Files:**
- Modify: `tests/test_install_skill.py`
- Modify: `skill/SKILL.md`
- Modify: `README.md`
- Modify: `docs/cli-reference.md`
- Modify: `docs/voidscape-guide.md`
- Modify: `docs/demo-shot-list.md`
- Modify: `docs/index.html`
- Modify: `tests/test_skill_md_wording.py`

**Interfaces:**
- Installer already copies the whole `skill/` tree; tests must prove `scripts/image.py` exists in both canonical install roots.
- Public copy must move local images/carousels from planned to available while leaving URL/social adapters planned.

- [x] **Step 1: Write failing installer and wording tests**

Extend the installer loop assertion:

```python
assert (install_root / "voidscape" / "scripts" / "image.py").exists()
```

Add wording checks requiring `image.py manifest --compact`, `[image 1]`, local/non-recursive scope, and explicit shipped-versus-planned labels.

- **Historical RED checkpoint — intentionally unperformed: packaging and wording**

Run: `python -m pytest tests/test_install_skill.py tests/test_skill_md_wording.py -v -p no:cacheprovider`

Expected: installer/image documentation assertions fail.

- [x] **Step 3: Update docs and demo instructions**

Document:

```text
python skill/scripts/voidscape.py inspect path/to/carousel
python skill/scripts/voidscape.py preview path/to/carousel
python skill/scripts/voidscape.py read path/to/carousel --workdir carousel-evidence
python skill/scripts/image.py manifest --compact
```

State that folder reads are local, non-recursive, naturally ordered, capped at 100 images, preserve originals, and produce `images/` plus `manifest.json`. Agents cite `[image N]`; they must not invent timestamps or claim OCR. Update the OpenScreen shot list to the approved 45–60 second carousel story. On the website, label local images/carousels “Available now” and retain private YouTube queue, article/RSS intake, and remote adapters as “Coming soon — planned, not shipped.”

- [x] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_install_skill.py tests/test_skill_md_wording.py -v -p no:cacheprovider`

Expected: packaging and wording checks pass.

### Task 5: Full verification and handoff

**Files:**
- Modify by append only: `docs/handoff/2026-07-21-image-carousel-design/HANDOFF.md`
- Modify current state/index only: `docs/handoff/HANDOFF.md`
- Modify: `handoff.md`

**Interfaces:**
- Produces a verified local feature branch ready for a separate ship authorization.

- [x] **Step 1: Run static verification**

Run:

```powershell
python -m compileall -q skill/scripts
git diff --check
```

Expected: both commands exit `0` with no errors.

- [x] **Step 2: Run the full test suite**

Run: `python -m pytest -q -p no:cacheprovider`

Expected: all tests pass.

- [x] **Step 3: Exercise the real CLI**

Create a temporary three-image folder in natural-order filenames, then run:

```powershell
python skill/scripts/voidscape.py inspect <carousel>
python skill/scripts/voidscape.py preview <carousel>
python skill/scripts/voidscape.py read <carousel> --workdir <empty-output>
python skill/scripts/image.py manifest --compact
```

Expected: deterministic `1, 2, 10` order; local/free preview; copied evidence plus final manifest; protocol `1.0` manifest.

- [x] **Step 4: Refresh handoffs without rewriting immutable history**

Append concrete completed tasks, changed files, failures, and next steps to the active session handoff. Replace only the father `## Current state`, preserve exactly one session-index line, and refresh root `handoff.md`.

- [x] **Step 5: Stop before outward-facing actions**

Report verification evidence and changed files. Do not commit, push, merge, deploy, or claim `voidscape.club` is updated until Richard explicitly authorizes those actions for this feature.

## Final verification

Verified on 2026-08-28 on Windows:

- `python -m compileall -q skill/scripts` passed with exit `0`.
- `git diff --check` passed with exit `0`; it emitted six non-failing LF-to-CRLF warnings.
- The focused image/guided/privacy/wording/installer/hardening suite passed: `89 passed`.
- The complete Voidscape pytest suite passed: `194 passed`.
- Embedded locally generated static JPG/JPEG/WebP fixtures passed the exact-one-frame probe rule;
  embedded animated APNG/WebP fixtures were rejected without requiring an image encoder at test
  runtime.
- Image dominant-cost selection was verified against per-component USD contributions, including
  the active-pricing case where output costs more despite fewer tokens than overhead.
- The generated image carousel completed `inspect -> preview -> read` in natural filename order (`slide1`, `slide2`, `slide10`).
- The key-free video fixture completed `inspect -> preview -> read`.
- Both raw manifests reported protocol `1.0`.
- The read-video focused checks passed: `1 passed` and `12 passed`; the complete read-video suite passed: `133 passed`.
- Four read-video issues were closed, and both the read-video and Voidscape trackers reported zero open issues.

Post-merge verification on `main` at `a0fd4e8` (2026-08-28): the full Voidscape suite passed
(`194 passed`), installer and demo-fixture checks passed, and the image/carousel and key-free video
`inspect -> preview -> read` workflows completed. Vercel checks for PR #9 passed at merge time.
