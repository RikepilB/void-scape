# Public and authenticated sources

Voidscape started as a personal workflow for media Richard had already saved or could access while
signed in. That setup is useful evidence, but it is not the product's source of truth. The baseline
experience must work with a local file or a public media URL. Account-only sources are an optional
mode that uses access the user already has.

## Pick the smallest access path

| Source | Start here | Authentication needed? | Current status |
| --- | --- | --- | --- |
| Local video or audio | Pass the file path to `inspect` | No | Shipped |
| Public YouTube video | Pass the video URL to `inspect` | Usually no | Shipped through `yt-dlp`; platform behavior can change |
| Public Reel or TikTok URL | Try `inspect` with the direct media URL | Sometimes, even when the page looks public | Best effort through `yt-dlp`, not a guaranteed platform adapter |
| Instagram saved collection | Sign in manually in Chrome and use the repository capture workflow | Yes | User-observed development workflow; not an installed command |
| Private, age-gated, or subscriber-only media | Export cookies for the target site, then pass their path locally | Yes | Optional CLI bridge; the user owns and controls the cookie file |
| Public or subscriber Substack article | Read it in the browser | Sometimes | Not a media-CLI input; Substack/RSS ingestion is planned |

Always test the public path first. Do not require a personal account, a private saved collection, or
Richard's folders to demonstrate Voidscape's core CLI.

## Three separate browser pieces

These solve different problems and should not be described as one feature:

1. The [ChatGPT Chrome extension](https://chromewebstore.google.com/detail/chatgpt/hehggadaopoacecdllhhajmbjkdcmajg)
   connects ChatGPT/Codex to tabs after the user approves site access. It is useful for navigating a
   saved collection or inspecting an authenticated page.
2. The agent harness must expose a Chrome-control skill or browser tool. Voidscape's installer does
   not install that capability.
3. A Netscape-format `cookies.txt` lets `yt-dlp`, and therefore the Voidscape CLI, make a request
   using the user's existing site session. The ChatGPT extension does not automatically give the CLI
   those cookies.

None of these is required for local files or normally accessible public URLs.

## Use your own login with the CLI

Use this only for content your account is allowed to access.

1. Open the target site in Chrome and sign in yourself.
2. Export cookies for only that site in Netscape format. During project testing,
   [Get cookies.txt LOCALLY 0.7.2](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   solved this setup problem. It is an optional third-party tool, not a Voidscape dependency. Review
   its source, publisher, permissions, and current version before installing it.
3. Save the file outside the repository. A cookie file is effectively a temporary account key: do
   not share it, upload it, paste it into an agent prompt, or commit it.
4. Point Voidscape to the file for the current terminal session.

PowerShell:

```powershell
$env:READ_VIDEO_YTDLP_COOKIES = "C:\private\instagram-cookies.txt"
python skill/scripts/voidscape.py inspect "https://www.instagram.com/reel/REEL_ID/"
python skill/scripts/voidscape.py preview "https://www.instagram.com/reel/REEL_ID/"
```

macOS/Linux/Git Bash:

```bash
export READ_VIDEO_YTDLP_COOKIES="/private/instagram-cookies.txt"
python skill/scripts/voidscape.py inspect "https://www.instagram.com/reel/REEL_ID/"
python skill/scripts/voidscape.py preview "https://www.instagram.com/reel/REEL_ID/"
```

5. Inspect and preview before `read`. Authentication changes access, not the cost/privacy approval
   rules.
6. Remove the environment variable when finished, and delete or securely store the export.

```powershell
Remove-Item Env:READ_VIDEO_YTDLP_COOKIES
```

```bash
unset READ_VIDEO_YTDLP_COOKIES
```

Voidscape never discovers browser cookies itself. If the environment variable is absent or the file
does not exist, the CLI continues anonymously.

## Saved-content use case

A useful personal workflow is:

1. sign in to Instagram, TikTok, YouTube, or another service in Chrome;
2. open a saved category, playlist, or collection;
3. ask the browser-connected agent to inspect the visible items after granting site access;
4. choose a direct media URL you are permitted to process;
5. run `inspect -> preview -> read` on that URL;
6. have the agent answer from the resulting frames and transcript with timestamps.

The browser step discovers or selects the item. The CLI step prepares media evidence. Support for
automatically processing every saved item is not shipped.

## Troubleshooting

### The browser can play it, but `inspect` fails

The browser is authenticated and the CLI is anonymous. Export cookies for the target domain, set
`READ_VIDEO_YTDLP_COOKIES`, and retry `inspect`. If the direct media URL is not supported by
`yt-dlp`, use a local file you are permitted to download instead.

### The agent cannot see or control Chrome

- Confirm Google Chrome, not another Chromium browser, is being used.
- Confirm the ChatGPT Chrome extension is installed, enabled, and connected to the desktop app.
- Approve access to the specific site or tab when prompted.
- Confirm the current agent environment exposes its Chrome-control skill/tool.
- Retry with one tab before attempting a collection or multi-tab workflow.

Browser control and CLI authentication are independent. Fixing one does not automatically fix the
other.

### It works without a VPN but fails with one

A VPN can change region, trigger a login challenge, cause rate limiting, or make browser and CLI
requests leave through different routes. Voidscape does not manage VPN configuration.

- Retry a public URL with the VPN disabled.
- If a VPN is required, use a stable permitted region and verify the site still works in Chrome.
- Reauthenticate and re-export site cookies after the site's session changes.
- Do not use a VPN or cookies to bypass access controls, regional rights, or a platform's terms.

### Cookies still fail

- Confirm the file exists and is Netscape format, not JSON.
- Export only after signing in and opening the target site.
- Re-export if the site logged you out or rotated the session.
- Update `yt-dlp`; platform extractors change frequently.
- Test a public URL from the same platform to separate an extractor/network problem from an account
  problem.
- Never put the cookie contents in an issue, log, screenshot, or support message.

### Substack opens in Chrome but fails in the CLI

That is expected for an article page. Voidscape currently reads media, not general web pages. A
browser-connected agent can read the page after access approval; Substack/RSS ingestion remains a
planned adapter.

## Future account connections

A future hosted product can replace cookie export with a familiar connect-account flow: choose a
provider, review requested scopes, grant permission, and revoke it later. That requires provider
APIs/OAuth, credential storage, revocation, multi-user isolation, and policy review. It is roadmap
work, not a current CLI claim.
