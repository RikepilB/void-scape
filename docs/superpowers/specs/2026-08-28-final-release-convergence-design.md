# Voidscape final release convergence design

**Voidscape will ship its current local-first reader improvements without pulling a future universal extension into the release.**

**Date:** 2026-08-28  
**Status:** Approved in conversation  
**Branch:** `feat/image-carousel-reader`

## Goal

Finish the current Voidscape release, reconcile the remaining `read-video` issues, and document
the browser and remote-control workflows that Richard has tested. Keep every current privacy and
cost gate intact.

The release must make a clear distinction between three layers:

1. A browser-connected agent discovers or selects permitted media.
2. The Voidscape CLI prepares local, ordered evidence through `inspect -> preview -> read`.
3. The agent reads that evidence and answers with `[image N]` or `[MM:SS]` citations.

## Release boundary

Keep Voidscape as the canonical product. Keep `read-video` as the stable compatibility engine and
legacy name.

Ship the existing sibling-reader architecture:

- `skill/scripts/voidscape.py` selects the reader.
- `skill/scripts/image.py` handles one local image or one local carousel folder.
- `skill/scripts/video.py` handles video, audio, and supported video URLs.

Do not extract a generic media-reader interface before this release. Two implementations provide
useful comparison evidence, but article intake and a second capture adapter do not exist yet. A
shared interface designed now would still guess at major requirements.

Finish the image and carousel work already present in the working tree. Preserve these constraints:

- local input only
- non-recursive natural filename order
- 100-image ceiling
- byte-preserving copies
- no OCR claim
- no cloud processing or model download
- `manifest.json` written only after successful evidence preparation

No commit, push, pull request, merge, website deployment, or release publication is part of this
design unless Richard requests it separately.

## Browser and remote workflows

### Codex and ChatGPT

The ChatGPT desktop Chrome integration can work in existing signed-in Chrome tabs after the user
installs the plugin and grants site access. In Work mode or Codex, it can navigate, click, type,
inspect rendered state, and use developer data such as the DOM, console, and network traffic when
that access is enabled.

ChatGPT Remote can continue a ChatGPT or Codex task from a phone connected to a Mac or Windows
host. The host owns the files, credentials, permissions, plugins, Computer Use configuration,
Chrome extension, and local tools. The host must remain awake, online, and available.

For Voidscape, a remote phone session can steer or approve work on the connected host. The CLI
still runs on the host or remote environment that can access the selected media and evidence
files.

Official references:

- [Chrome extension](https://developers.openai.com/codex/chrome-extension)
- [Remote connections](https://developers.openai.com/codex/remote-connections)
- [Browser](https://developers.openai.com/codex/app/browser)

### Claude

Claude Code can connect to Claude in Chrome from the CLI or editor. It can use signed-in web apps,
test browser flows, inspect DOM, console, and network state, extract page data, and combine browser
actions with local coding commands.

Claude Code Remote Control can continue a running local session from `claude.ai/code` or the Claude
mobile app. The local Claude Code process and its machine remain the execution host.

Claude Cowork can also run cloud sessions that continue across desktop, web, and mobile. A cloud
session can keep working without the laptop. Work that needs local media, the local Voidscape CLI,
or the user's local Chrome session still needs the connected desktop path.

Official references:

- [Use Claude Code with Chrome](https://docs.anthropic.com/en/docs/claude-code/chrome)
- [Continue local sessions with Remote Control](https://docs.anthropic.com/en/docs/claude-code/remote-control)
- [Get started with Claude in Chrome](https://support.anthropic.com/en/articles/12012173-getting-started-with-claude-for-chrome)

### Authentication boundary

Browser access and CLI authentication remain separate.

The browser connection may let the agent inspect a page the user is already permitted to view.
It does not silently give `yt-dlp` the browser session. When a supported source requires account
access, the user may provide a site-scoped Netscape `cookies.txt` through
`READ_VIDEO_YTDLP_COOKIES`. Voidscape never discovers, reads, or exports browser credentials,
cookies, storage, or secrets.

## Harness-neutral core and future extension

The Voidscape CLI is model-neutral. Any harness that can execute a command, read files, and honour
the approval gates can drive its JSON interface.

This does not mean one browser extension automatically works with every model and harness. A usable
integration also needs:

- a transport between the browser and the harness
- tool discovery and schemas
- site and action permissions
- approval handling
- local or remote host routing
- secret and session isolation

A future harness extension should reuse the existing command manifest and
`{ok,data,error,meta}` envelope. MCP or a similarly explicit tool protocol is a reasonable
candidate. Native messaging may connect the browser to a local host. That extension requires its
own design and security review and is not part of this release.

A model without tool access cannot run Voidscape directly.

## Legacy issue resolution

Resolve the four open issues in `RikepilB/read-video` after verification:

### Issue #2

Close as fixed by commit `6c3b469`.

Verify:

- `run()` uses the resolved `info["input"]`
- the bare inbox filename regression test passes
- `.gitignore` allows `.env.example`
- `.env.example` is tracked

### Issue #3

Close as fixed by commit `6c3b469`.

Verify:

- `auto` selects the thorough profile above the configured duration threshold
- the thorough profile selects the intended model and VAD arguments
- model downloads still require explicit approval
- profile and estimate tests pass

### Issue #4

Close as a private Instagram-vault quality task rather than a Voidscape product issue. Do not copy,
inspect, publish, or migrate private notes as part of this release.

### Issue #5

Close as superseded by the Voidscape roadmap and this release decision. The current release keeps
two focused readers. Capture-adapter and general reader extraction remain future architecture work
after more concrete implementations exist.

Do not create replacement GitHub issues in this release.

## Documentation changes

Update:

- `README.md` with a short browser and remote-work summary
- `docs/harness-support.md` with the full Codex, ChatGPT, Claude, and portability matrix
- `docs/authenticated-sources.md` with the browser versus CLI authentication boundary
- `docs/chrome-use-case-matrix.md` with tested, official, and unverified claim labels
- `docs/ROADMAP.md` with current image-reader status and the separately scoped extension direction
- the existing image and carousel design and implementation plan with completion status and fresh
  verification evidence

Keep public copy direct. Describe what works, what requires a connected host, and what remains
planned. Do not imply that browser login state transfers to the CLI or that every model and harness
is automatically supported.

## Error handling and stop conditions

Do not close an issue if its verification fails.

Do not claim that the website contains local image and carousel support until the relevant changes
are committed, pushed, and deployed.

Do not touch unrelated untracked artifacts. Do not weaken the cloud or model-download approval
gates. Do not add browser credential discovery.

## Verification

Run the following Voidscape checks:

1. `python -m compileall -q skill/scripts`
2. `git diff --check`
3. `python -m pytest -q -p no:cacheprovider`
4. installer verification for both supported skill roots
5. key-free video demo fixture from creation through `inspect -> preview -> read`
6. a real local image and carousel `inspect -> preview -> read`
7. protocol manifest checks for both `video.py` and `image.py`

Run the following `read-video` checks before closing issues #2 and #3:

1. bare inbox filename regression test
2. transcription profile and estimate tests
3. full test suite when local dependencies permit
4. `git check-ignore` and `git ls-files` checks for `.env.example`

The release is ready for a separate shipping decision only when the relevant checks pass and the
remaining changes are limited to the approved scope.
