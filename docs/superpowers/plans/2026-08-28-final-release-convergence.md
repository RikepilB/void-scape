# Voidscape Final Release Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the local image and carousel release, publish accurate browser and remote-control guidance, and close the four stale `read-video` issues with current verification evidence.

**Architecture:** Keep `voidscape.py` as the guided dispatcher over the focused `image.py` and `video.py` sibling engines. Treat Chrome and phone-based remote control as harness capabilities that steer a host where Voidscape runs, not as authentication or browser code inside Voidscape. Defer the universal harness extension and generic reader interface to a separate design.

**Tech Stack:** Python 3.10+, standard library, FFmpeg and FFprobe, pytest, PowerShell, Markdown, GitHub CLI.

## Global Constraints

- Preserve `inspect -> preview -> read`.
- Never infer cloud-upload or model-download consent.
- Never read browser credentials, cookies, storage, or secrets.
- Keep `read-video` as documented backward compatibility.
- Keep local image and carousel reads non-recursive, naturally ordered, byte-preserving, and limited to 100 images.
- Do not add OCR, cloud image processing, a generic reader interface, an MCP server, or a browser extension in this release.
- Do not touch unrelated untracked artifacts.
- Do not claim website deployment before commit, push, and deployment verification.
- Do not commit, push, open a pull request, merge, or deploy without a separate explicit user request.
- Close the approved legacy issues only after their relevant checks pass.

## File Structure

- `tests/test_skill_md_wording.py`: locks the public browser, remote-control, authentication, and roadmap boundaries.
- `README.md`: gives users a short capability summary and points to the detailed harness guide.
- `docs/harness-support.md`: owns the Codex, ChatGPT, Claude, remote-control, and harness-portability matrix.
- `docs/authenticated-sources.md`: owns the browser-session versus CLI-authentication boundary.
- `docs/chrome-use-case-matrix.md`: separates personally tested behavior, vendor-documented behavior, and unverified claims.
- `docs/ROADMAP.md`: records current reader status and keeps the universal extension as separately designed future work.
- `docs/superpowers/specs/2026-07-21-image-carousel-reader-design.md`: records local implementation and verification status.
- `docs/superpowers/plans/2026-07-21-image-carousel-reader.md`: records completed implementation tasks and fresh evidence.
- `handoff.md`: records final local state, issue resolution, verification, and the remaining shipping decision.

---

### Task 1: Lock the browser and remote-control truth contract

**Files:**
- Modify: `tests/test_skill_md_wording.py:4-23`
- Modify: `tests/test_skill_md_wording.py:39-49`
- Modify: `README.md:89-122`
- Modify: `docs/harness-support.md:1-71`
- Modify: `docs/authenticated-sources.md:22-35`
- Modify: `docs/chrome-use-case-matrix.md:1-43`

**Interfaces:**
- Consumes: the existing Markdown documentation files.
- Produces: wording tests that prevent browser login, remote host, and universal-harness claims from drifting.

- [ ] **Step 1: Add failing documentation contract tests**

Add these constants beside the current documentation paths:

```python
HARNESS_SUPPORT = REPO / "docs" / "harness-support.md"
CHROME_MATRIX = REPO / "docs" / "chrome-use-case-matrix.md"
ROADMAP = REPO / "docs" / "ROADMAP.md"
IMAGE_DESIGN = REPO / "docs" / "superpowers" / "specs" / "2026-07-21-image-carousel-reader-design.md"
IMAGE_PLAN = REPO / "docs" / "superpowers" / "plans" / "2026-07-21-image-carousel-reader.md"
```

Add these tests:

```python
def test_browser_and_remote_docs_keep_host_boundary_explicit():
    readme = README.read_text(encoding="utf-8")
    harness = HARNESS_SUPPORT.read_text(encoding="utf-8")
    auth = AUTH_GUIDE.read_text(encoding="utf-8")
    matrix = CHROME_MATRIX.read_text(encoding="utf-8")

    assert "docs/harness-support.md" in readme
    for required in (
        "ChatGPT Remote",
        "Claude Code Remote Control",
        "host must remain awake",
        "local Voidscape CLI",
        "A model without tool access cannot run Voidscape directly",
    ):
        assert required in harness
    assert "Browser access does not become CLI authentication" in auth
    assert "Vendor-documented" in matrix
    assert "Richard-tested" in matrix


def test_harness_docs_do_not_claim_automatic_universal_support():
    content = HARNESS_SUPPORT.read_text(encoding="utf-8")
    assert "does not mean one extension automatically supports every model and harness" in content
    for required in (
        "transport",
        "tool discovery",
        "permissions",
        "approval",
        "host routing",
    ):
        assert required in content
```

- [ ] **Step 2: Run the tests to verify RED**

Run:

```powershell
python -m pytest tests/test_skill_md_wording.py -q -p no:cacheprovider
```

Expected: the new tests fail because the detailed remote-control and portability wording does not
exist yet.

- [ ] **Step 3: Add the short README explanation**

Replace the current browser-only paragraph with a concise summary that includes this content:

```markdown
Browser and phone control belong to the agent harness, not the media engine. With the approved
Chrome connection, Codex/ChatGPT or Claude can select permitted media in signed-in tabs, then run
Voidscape on the host that can access the files. ChatGPT Remote and Claude Code Remote Control can
continue that host task from a phone while the local tools remain on the host. Browser access does
not authenticate `yt-dlp`.

See [Multi-harness, browser, and remote support](docs/harness-support.md) and
[Public and authenticated sources](docs/authenticated-sources.md).
```

Keep the existing `inspect -> preview -> read` agent instructions immediately after this summary.

- [ ] **Step 4: Rewrite the detailed harness guide**

Keep the existing installer paths and verification behavior. Add a capability matrix with these
rows and exact boundaries:

```markdown
| Environment | What the harness can do | What Voidscape does | Remote condition |
| --- | --- | --- | --- |
| Codex or Work in ChatGPT desktop with Chrome | Use approved signed-in tabs, click, type, inspect rendered state, and use developer data when enabled | Run the local CLI and read its evidence bundle | ChatGPT Remote can steer the paired host from mobile; the host must remain awake, online, and available |
| Claude Code with Claude in Chrome | Use signed-in sites, test browser flows, and inspect DOM, console, and network state | Run the local Voidscape CLI beside the coding session | Claude Code Remote Control continues the running host session from mobile or web |
| Claude Cowork in the cloud | Continue cloud work across desktop, web, and mobile | Use Voidscape only when the session can reach the media and CLI | Local files or local Chrome still require the connected desktop path |
| Other tool-capable harness | Execute the JSON CLI and read local evidence | Preserve the same gates and citations | Discovery, transport, permissions, approval, and host routing are harness-specific |
```

Add official links:

```markdown
- https://developers.openai.com/codex/chrome-extension
- https://developers.openai.com/codex/remote-connections
- https://developers.openai.com/codex/app/browser
- https://docs.anthropic.com/en/docs/claude-code/chrome
- https://docs.anthropic.com/en/docs/claude-code/remote-control
- https://support.anthropic.com/en/articles/12012173-getting-started-with-claude-for-chrome
```

End the guide with:

```markdown
The CLI is model-neutral. That does not mean one extension automatically supports every model and
harness. Each integration still needs a transport, tool discovery, permissions, approval handling,
and local or remote host routing. A model without tool access cannot run Voidscape directly.
```

- [ ] **Step 5: Strengthen the authentication guide**

Add this paragraph under `## Three separate browser pieces`:

```markdown
**Browser access does not become CLI authentication.** A browser-connected agent may inspect a tab
the user is permitted to view, but that connection does not silently transfer Chrome cookies to
`yt-dlp`. Voidscape never reads browser credentials, cookies, storage, or secrets.
```

Add a fourth item explaining that mobile remote control steers the connected execution host. It
does not move local files, browser sessions, or CLI credentials onto the phone.

- [ ] **Step 6: Add evidence labels to the Chrome matrix**

Add a `## Browser and remote-control support matrix` section with three evidence labels:

```markdown
- **Richard-tested:** observed on Richard's connected Windows setup.
- **Vendor-documented:** supported by current OpenAI or Anthropic documentation but not reproduced
  as a Voidscape product test.
- **Unverified:** do not publish as a capability claim.
```

Record the browser selection plus host CLI sequence as Richard-tested. Record mobile continuation,
host availability requirements, and DOM/console/network capabilities as vendor-documented unless a
new reproducible local test is added. Mark automatic cookie transfer and automatic support for every
model or harness as unverified and unsupported.

- [ ] **Step 7: Run the documentation tests to verify GREEN**

Run:

```powershell
python -m pytest tests/test_skill_md_wording.py -q -p no:cacheprovider
```

Expected: all wording tests pass.

---

### Task 2: Reconcile the roadmap and image-release records

**Files:**
- Modify: `tests/test_skill_md_wording.py`
- Modify: `docs/ROADMAP.md:43-73`
- Modify: `docs/ROADMAP.md:181-203`
- Modify: `docs/superpowers/specs/2026-07-21-image-carousel-reader-design.md:1-25`
- Modify: `docs/superpowers/plans/2026-07-21-image-carousel-reader.md:1-20`

**Interfaces:**
- Consumes: the implemented `image.py` behavior and its existing tests.
- Produces: current roadmap language and auditable completion status without claiming a deployment.

- [ ] **Step 1: Add failing roadmap and status tests**

Add:

```python
def test_roadmap_and_image_plan_match_local_release_state():
    roadmap = ROADMAP.read_text(encoding="utf-8")
    design = IMAGE_DESIGN.read_text(encoding="utf-8")
    plan = IMAGE_PLAN.read_text(encoding="utf-8")

    assert "Local images and carousels" in roadmap
    assert "implemented on `feat/image-carousel-reader`" in roadmap
    assert "separate design and security review" in roadmap
    assert "**Status:** Implemented and verified locally; not yet shipped" in design
    assert "**Status:** Completed locally; awaiting a separate shipping decision" in plan
```

- [ ] **Step 2: Run the tests to verify RED**

Run:

```powershell
python -m pytest tests/test_skill_md_wording.py::test_roadmap_and_image_plan_match_local_release_state -q -p no:cacheprovider
```

Expected: FAIL because the current roadmap still calls images future work and the old design and
plan statuses are stale.

- [ ] **Step 3: Correct the roadmap's current-state language**

Replace the statement that the read axis is video-only with:

```markdown
- **Read axis** - media to ordered evidence. `video.py` handles video and audio.
  `image.py`, implemented on `feat/image-carousel-reader`, handles local images and carousels.
  The guided CLI dispatches between these focused readers. A generic reader interface remains
  deferred until article intake supplies a third concrete shape.
```

Update Phase 1.1:

```markdown
- **1.1 Local images and carousels** - implemented on `feat/image-carousel-reader`; local
  verification is complete, but commit, merge, and deployment remain a separate shipping decision.
```

Keep article and RSS intake planned.

- [ ] **Step 4: Narrow the universal-extension roadmap entry**

Retitle it as a next-project candidate, not a current release promise. State:

```markdown
The existing CLI manifest and `{ok,data,error,meta}` envelope are the portable core. A universal
browser bridge still needs a transport, tool schemas, permission and approval handling, host
routing, and a per-platform policy review. It requires a separate design and security review.
```

Do not name a specific model fleet or promise support for every model and harness.

- [ ] **Step 5: Update the image design and plan status**

Change the image design header to:

```markdown
**Status:** Implemented and verified locally; not yet shipped
```

Change the image implementation plan header to:

```markdown
**Status:** Completed locally; awaiting a separate shipping decision
```

Mark an implementation checkbox complete only when its corresponding file or test exists. Leave no
checkbox checked solely because the plan expected it.

- [ ] **Step 6: Run the status tests to verify GREEN**

Run:

```powershell
python -m pytest tests/test_skill_md_wording.py -q -p no:cacheprovider
```

Expected: all wording tests pass.

---

### Task 3: Verify the current Voidscape release candidate

**Files:**
- Verify: `skill/scripts/image.py`
- Verify: `skill/scripts/voidscape.py`
- Verify: `skill/scripts/video.py`
- Verify: `tests/test_image_reader.py`
- Verify: `tests/test_voidscape.py`
- Verify: `tests/test_install_skill.py`
- Verify: `tests/test_privacy_gate.py`
- Verify: `tests/test_build_week_hardening.py`

**Interfaces:**
- Consumes: `image.probe`, `image.estimate`, `image.run`, guided dispatch, installer scripts, and the existing privacy gates.
- Produces: fresh local evidence that the release candidate works without changing its architecture.

- [ ] **Step 1: Run the focused reader and safety suite**

Run:

```powershell
python -m pytest tests/test_image_reader.py tests/test_voidscape.py tests/test_install_skill.py tests/test_privacy_gate.py tests/test_build_week_hardening.py -q -p no:cacheprovider
```

Expected: all selected tests pass. Stop and diagnose before documentation or issue closure if any
test fails.

- [ ] **Step 2: Verify static integrity**

Run:

```powershell
python -m compileall -q skill/scripts
git diff --check
python skill/scripts/video.py manifest --compact
python skill/scripts/image.py manifest --compact
```

Expected: both static commands exit `0`; each manifest is valid compact JSON with protocol version
`1.0` and commands `manifest`, `probe`, `estimate`, and `run`.

- [ ] **Step 3: Exercise a generated carousel**

Run:

```powershell
$carousel = Join-Path $env:TEMP ("voidscape-carousel-" + [guid]::NewGuid())
$evidence = Join-Path $env:TEMP ("voidscape-evidence-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $carousel | Out-Null
$png = [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
[IO.File]::WriteAllBytes((Join-Path $carousel "slide10.png"), $png)
[IO.File]::WriteAllBytes((Join-Path $carousel "slide2.png"), $png)
[IO.File]::WriteAllBytes((Join-Path $carousel "slide1.png"), $png)
python skill/scripts/voidscape.py inspect $carousel
python skill/scripts/voidscape.py preview $carousel
python skill/scripts/voidscape.py read $carousel --workdir $evidence
Get-Content (Join-Path $evidence "manifest.json")
```

Expected: inspect reports `slide1.png`, `slide2.png`, `slide10.png`; preview reports no cloud or
model-download requirement; read writes three ordered copies plus `manifest.json`.

- [ ] **Step 4: Exercise the key-free video fixture**

Run:

```powershell
$videoEvidence = Join-Path $env:TEMP ("voidscape-video-" + [guid]::NewGuid())
python scripts/create-demo-fixture.py
python skill/scripts/voidscape.py inspect samples/build-week-demo.mp4
python skill/scripts/voidscape.py preview samples/build-week-demo.mp4 --tier both --backend captions
python skill/scripts/voidscape.py read samples/build-week-demo.mp4 --tier both --backend captions --workdir $videoEvidence
Get-Content (Join-Path $videoEvidence "manifest.json")
```

Expected: all commands exit `0`; the evidence contains frames, `transcript.txt`, and
`manifest.json`; no API key, cloud approval, or model download is required.

- [ ] **Step 5: Run the complete Voidscape suite**

Run:

```powershell
python -m pytest -q -p no:cacheprovider
```

Expected: the entire suite passes with no skips caused by a regression.

---

### Task 4: Verify and close the stale read-video issues

**Files:**
- Verify in sibling repo: `../read-video/skill/scripts/video.py`
- Verify in sibling repo: `../read-video/.gitignore`
- Verify in sibling repo: `../read-video/.env.example`
- Verify in sibling repo: `../read-video/tests/test_frames.py`
- Verify in sibling repo: `../read-video/tests/test_transcribe_profiles.py`
- Verify in sibling repo: `../read-video/tests/test_estimate.py`
- GitHub: `RikepilB/read-video` issues `#2`, `#3`, `#4`, and `#5`

**Interfaces:**
- Consumes: fixes in read-video commit `6c3b469` and their regression tests.
- Produces: an empty, accurately resolved legacy issue tracker with public explanations.

- [ ] **Step 1: Verify issue #2 in the read-video repository**

From `C:\Users\a2021\OneDrive\Escritorio\Vibe projects workspace\PROYECTOS\read-video`, run:

```powershell
python -m pytest tests/test_frames.py::test_run_resolves_workspace_bare_filename_for_frames -q -p no:cacheprovider
git ls-files --error-unmatch .env.example
git check-ignore -q .env.example
if ($LASTEXITCODE -eq 0) { throw ".env.example is still ignored" }
git log -1 --oneline -S "source_input = info"
git log -1 --oneline -S "!.env.example"
```

Expected: the pytest passes; `.env.example` is tracked and not ignored; both searches identify
`6c3b469`.

- [ ] **Step 2: Verify issue #3 in the read-video repository**

Run:

```powershell
python -m pytest tests/test_transcribe_profiles.py tests/test_estimate.py::test_estimate_surfaces_required_thorough_model_download -q -p no:cacheprovider
git log -1 --oneline -S "_TRANSCRIBE_THOROUGH_THRESHOLD_S"
```

Expected: all selected tests pass and the history search identifies `6c3b469`.

- [ ] **Step 3: Run the full read-video suite**

Run:

```powershell
python -m pytest -q -p no:cacheprovider
```

Expected: the suite passes. If an optional local dependency causes a documented skip, record the
skip. Do not close #2 or #3 after a related failure.

- [ ] **Step 4: Close issue #2 as completed**

Run:

```powershell
gh issue close 2 --repo RikepilB/read-video --reason completed --comment "Verified on 2026-08-28. Both reported defects were fixed in commit 6c3b469: run() now uses probe's resolved input, the bare-inbox-filename regression passes, .gitignore contains the .env.example exception, and .env.example is tracked. Closing as completed."
```

Expected: GitHub reports issue #2 closed.

- [ ] **Step 5: Close issue #3 as completed**

Run:

```powershell
gh issue close 3 --repo RikepilB/read-video --reason completed --comment "Verified on 2026-08-28. Commit 6c3b469 implemented duration-routed fast/thorough transcription, tuned thorough-profile VAD arguments, the medium-model path, and the separate model-download approval gate. The focused profile and estimate regressions and the full suite pass. Closing as completed."
```

Expected: GitHub reports issue #3 closed.

- [ ] **Step 6: Close issue #4 as not planned product work**

Run:

```powershell
gh issue close 4 --repo RikepilB/read-video --reason "not planned" --comment "Closing because this tracks quality review of Richard's private Instagram vault notes, not a read-video or Voidscape product defect. The final-release work did not inspect, copy, publish, or migrate those private notes. Any future vault QA should remain a private local task."
```

Expected: GitHub reports issue #4 closed without importing private content.

- [ ] **Step 7: Close issue #5 as superseded**

Run:

```powershell
gh issue close 5 --repo RikepilB/read-video --reason "not planned" --comment "Superseded by Voidscape's roadmap and final-release design. Voidscape now has focused video/audio and local image/carousel readers. The release deliberately defers a generic reader or capture-adapter interface until more concrete source types and adapters exist, avoiding a premature abstraction. No replacement issue is being created in this release."
```

Expected: GitHub reports issue #5 closed.

- [ ] **Step 8: Confirm both trackers**

Run:

```powershell
gh issue list --repo RikepilB/read-video --state open --limit 100
gh issue list --repo RikepilB/void-scape --state open --limit 100
```

Expected: both commands return no open issues.

---

### Task 5: Record the verified release state and stop before shipping

**Files:**
- Modify: `docs/superpowers/plans/2026-07-21-image-carousel-reader.md`
- Modify: `handoff.md`
- Verify: the complete approved working-tree diff

**Interfaces:**
- Consumes: exact outputs from Tasks 1 through 4.
- Produces: a local release-candidate handoff and a clean decision point for a later commit or PR request.

- [ ] **Step 1: Record exact verification evidence**

Add a dated verification section to the image plan:

```markdown
## Final verification

Verified on 2026-08-28 on Windows:

- `python -m compileall -q skill/scripts` passed.
- `git diff --check` passed.
- The focused reader, installer, privacy, and hardening suite passed.
- The complete Voidscape pytest suite passed.
- The generated image carousel completed `inspect -> preview -> read` in natural order.
- The key-free video fixture completed `inspect -> preview -> read`.
- Both raw manifests reported protocol `1.0`.

This evidence is local. Commit, merge, deployment, and website verification remain separate.
```

Replace each generic “passed” sentence with its exact test count or relevant command result from
Task 3 before saving.

- [ ] **Step 2: Refresh the root handoff**

Update `handoff.md` with:

- branch and base commit
- exact test counts
- completed image and carousel state
- documentation files changed
- read-video issue closure results
- confirmation that both trackers are empty
- untouched unrelated untracked files
- explicit statement that nothing was committed, pushed, merged, or deployed
- next action: review the diff and choose whether to commit and open a pull request

- [ ] **Step 3: Review the final diff**

Run:

```powershell
git status --short --branch
git diff --check
git diff --stat
git diff -- README.md docs/harness-support.md docs/authenticated-sources.md docs/chrome-use-case-matrix.md docs/ROADMAP.md docs/superpowers/specs/2026-07-21-image-carousel-reader-design.md docs/superpowers/plans/2026-07-21-image-carousel-reader.md docs/superpowers/specs/2026-08-28-final-release-convergence-design.md docs/superpowers/plans/2026-08-28-final-release-convergence.md tests/test_skill_md_wording.py handoff.md
```

Expected: only approved feature, documentation, test, plan, and handoff changes appear in the
reviewed diff. Unrelated untracked artifacts remain unmodified.

- [ ] **Step 4: Stop before outward shipping actions**

Report:

- exact verification results
- issues closed with links
- files changed
- any remaining risk or skipped check
- that commit, push, PR, merge, and deployment were not performed

If the user later authorizes a commit, use focused commit boundaries:

1. image and carousel engine, guided dispatch, tests, installer assertions, and capability docs
2. browser and remote-control documentation, wording tests, roadmap, plans, and handoff

Do not create either commit from this plan without fresh explicit authorization.
