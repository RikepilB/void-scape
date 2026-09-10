# YouTube queue capture

Capture videos from a **user-owned private queue playlist** into `urls.md` using the official
YouTube Data API v3. This is the capture half of the pipeline; `video.py` / `voidscape.py` already
read captured YouTube URLs on the read side.

Watch Later is **not** used: current API docs report it as inaccessible to `playlistItems.list`.
Use a dedicated playlist instead (default title: `Read Video Queue`).

## Design pass (API, OAuth, quota, terms)

| Topic | Decision |
|---|---|
| API | YouTube Data API v3 (`playlists.list`, `playlistItems.list`, `playlistItems.delete`) |
| Auth | Explicit OAuth 2.0 consent; **never** browser cookies, storage, or credential scraping |
| Read scope | `https://www.googleapis.com/auth/youtube.readonly` |
| Delete scope | `https://www.googleapis.com/auth/youtube.force-ssl` (`youtube.readonly` cannot delete) |
| Quota | `playlists.list` / `playlistItems.list` = 1 unit; `playlistItems.delete` = 50 units per item |
| Rate limits | Project daily quota (default 10,000 units/day); helper aborts on `quotaExceeded` |
| Terms | Comply with [YouTube API Services Terms](https://developers.google.com/youtube/terms/api-services-terms-of-service) and Google API Services User Data Policy; personal/self-hosted use only in this repo's scope |

Flow mirrors Instagram capture: **inspect → preview → process**. Playlist mutation happens only in
`process`, and only after a durable append to `urls.md` (or a confirmed duplicate already in the vault).

Playlist enumeration validates page item lists, nested object fields and string page
tokens. Repeated tokens stop with a structured API-shape error rather than requesting
the same pages indefinitely. Enumeration completes before queue writes or playlist
deletion, so a malformed later page does not publish a partial queue. Missing video
identities remain skipped as unavailable items; nonempty identities selected for
capture must be strings.
These checks follow the response types in the official
[playlist-items](https://developers.google.com/youtube/v3/docs/playlistItems/list)
and [playlists](https://developers.google.com/youtube/v3/docs/playlists/list) references.
They detect token cycles, not every possible unbounded stream of unique tokens.

## One-time OAuth setup

1. Create a Google Cloud project and enable **YouTube Data API v3**.
2. Configure the OAuth consent screen (External or Internal per your account type).
3. Create OAuth client credentials (Desktop app is simplest for local CLI use).
4. Request scopes:
   - `https://www.googleapis.com/auth/youtube.readonly` (inspect/preview)
   - `https://www.googleapis.com/auth/youtube.force-ssl` (process — required for delete)
5. Run an out-of-band OAuth flow (e.g. `google-auth-oauthlib` sample, or Google's OAuth Playground)
   and obtain a short-lived **access token**. Export it for the helper:

   ```powershell
   $env:YOUTUBE_ACCESS_TOKEN = "<access-token-from-consent-flow>"
   ```

   Or pass `--access-token` per invocation. Refresh/re-auth when the token expires.

6. In YouTube, create a **private** playlist titled `Read Video Queue` (or note your playlist ID).
   Add videos you want captured to that playlist.

The helper does **not** implement the OAuth browser flow itself — consent must be explicit and
separate from any browser automation.

## Commands

All commands print one JSON object to stdout.

### inspect — list queue, no mutations

```powershell
python scripts/youtube_capture_helper.py inspect --playlist-id PLxxxxxxxx
# or discover by title:
python scripts/youtube_capture_helper.py inspect --playlist-title "Read Video Queue"
```

Returns playlist metadata, queued items (`video_id`, canonical URL, title), and embedded design
metadata (scopes, quota units, terms note).

### preview — planned actions, no mutations

```powershell
python scripts/youtube_capture_helper.py preview --playlist-id PLxxxxxxxx path\to\urls.md
```

Shows per-item `action` (`append` or `skip_duplicate`), `safe_to_remove`, and a summary count.
Does not write `urls.md` or touch the playlist.

### process — capture then remove from queue

```powershell
python scripts/youtube_capture_helper.py process --playlist-id PLxxxxxxxx path\to\urls.md
```

For each queued item, in order:

1. Canonicalize to `https://www.youtube.com/watch?v=<id>`
2. Skip append if URL already in `urls.md` (content-keyed dedup)
3. Otherwise append and verify the line persisted
4. **Only then** call `playlistItems.delete` for that item

Aborts with `error_type` on:

- `authorization` — missing/invalid token or insufficient scope
- `quota` — quota or rate-limit errors
- `api_shape` — unexpected API response
- `partial_write` — append succeeded but delete failed (queue item left in place for manual recovery)

On `partial_write`, earlier items in the same run may already have been captured and removed;
check stdout `details.processed` and your playlist.

## Manual verification recipe

Prerequisites: OAuth token with `youtube.force-ssl`, private queue playlist with 1–2 test videos,
empty or known `urls.md` path.

1. **Inspect** — confirm items appear and design metadata looks right:

   ```powershell
   python scripts/youtube_capture_helper.py inspect --playlist-title "Read Video Queue"
   ```

2. **Preview** — confirm append/skip plan without side effects:

   ```powershell
   python scripts/youtube_capture_helper.py preview --playlist-title "Read Video Queue" .\urls.md
   ```

3. **Process** — run capture:

   ```powershell
   python scripts/youtube_capture_helper.py process --playlist-title "Read Video Queue" .\urls.md
   ```

4. Verify `urls.md` contains canonical YouTube URLs.
5. Verify processed videos disappeared from the queue playlist in YouTube Studio.
6. Re-run **preview** — queue should be empty (or only show new additions).
7. Re-run **process** on an empty queue — should return `summary.total: 0` with no errors.
8. Optional read step: `voidscape.py inspect "<youtube-url>"` then `preview` / `read` per existing cost gates.

## Privacy and cost gates

- This adapter only talks to Google's API with a token you supply; it does not bypass `voidscape`
  inspect/preview/read cost or cloud consent gates for the actual media read.
- Do not commit access tokens or client secrets to the repository.

## Related decisions

- `docs/decisions.md` — 2026-07-09 and 2026-07-17 YouTube adapter entries
- `docs/ROADMAP.md` — Phase 2.5
