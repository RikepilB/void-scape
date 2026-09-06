# Source capabilities

Voidscape separates two questions that are easy to blur:

1. **Can a permitted URL or local file be read?** The video, image, and article readers create
   evidence after `inspect -> preview -> read`.
2. **Can Voidscape enumerate or mutate a saved account collection?** That needs a platform-specific
   capture adapter, separate authorization, terms review, and live-account evidence.

Run `voidscape sources --json` for the machine-readable registry and
`voidscape route <input> --json` for one source. `best_effort` means the public reader is available,
not that every post shape or authenticated collection has been certified.
Route output strips URL credentials, query values, and fragments so discovery logs do not copy
tokens or private collection identifiers.

Known account listing routes (YouTube `/feed/playlists`, LinkedIn `/my-items/saved-posts`,
and Instagram `/<user>/saved/all-posts`) have no direct reader. Select a permitted item in
the signed-in browser first; reader overrides cannot bypass this selection step.
For these recognized routes, `requires_browser_auth: true` describes the browser selection
step, not permission for Voidscape to import authentication. A false value elsewhere is not
a guarantee that a remote page is public; access remains best-effort and is not probed by routing.

## Current matrix

| Source | Public reading | Saved/account capture | Default route | Current boundary |
| --- | --- | --- | --- | --- |
| Local video/audio | Shipped | Not applicable | `video` | Local by default; model/cloud gates remain separate |
| Local image/carousel | Shipped | Not applicable | `image` | Local, non-recursive, 100-image cap |
| Local article/RSS/Atom | Shipped | Not applicable | `article` | Local text is still untrusted evidence |
| YouTube | Best effort through `yt-dlp` | Dev-only private-playlist helper | `video` | Real OAuth/account mutation remains unverified |
| Instagram | Best-effort Reels through `yt-dlp` | Dev-only, browser-observed helper | `video` | Posts/carousels may need local images or a permitted tab capture |
| Substack | Shipped for public article/RSS fetch | Direct feed/URL only | `article` | Subscriber sessions remain browser-owned |
| X / Twitter | Best-effort media; public text can use article override | Not shipped | `video` | Bookmarks and account automation need a separate API/ToS design |
| Reddit | Best-effort text or media | Not shipped | `article` | Use `--reader video` only when the selected post is media-first |
| LinkedIn | Best-effort public text or selected media | Not shipped | `article` | Most useful pages are signed-in; browser session is never imported |
| TikTok | Best-effort direct public media | Not shipped | `video` | Saved collection remains harness-owned |
| Vimeo/Twitch/Dailymotion/SoundCloud/Facebook | Best-effort public media | Not shipped | `video` | Extractor and platform behavior can change |
| Other web page | Approved public article fetch; media override when known | Direct URL only | `article` | Remote image fetch is not shipped; localize or capture permitted tab |

## Routing overrides

Mixed-media sites need an explicit source-shape choice when automatic routing is wrong:

```powershell
voidscape route "https://www.reddit.com/r/example/comments/..."
voidscape inspect "https://www.reddit.com/r/example/comments/..." --reader video
voidscape preview "https://www.linkedin.com/posts/..." --reader article
```

An override selects a reader. It never grants cloud, model-download, browser, cookie, or account
permission and cannot bypass public-network validation.

## Security and evidence labels

- Remote article/feed requests allow only standard-port HTTP(S), reject credentials in URLs,
  revalidate DNS, connect to the validated public IP without a second resolver lookup, reject HTTPS
  downgrades, cap redirects/bytes, and accept only uncompressed text/XML content types.
- Remote media URLs receive the same initial public-address and URL-shape check before `yt-dlp`.
  Extractor-discovered requests cannot currently be IP-pinned by Voidscape, so public media remains
  `best_effort` and must never be launched automatically from untrusted source text.
- Every produced manifest marks source content as `untrusted`. Titles, pages, transcripts, images,
  and frames may contain prompt-like text; agents analyze it as evidence and never execute it.
- Browser selection and CLI authentication are separate. Voidscape never discovers browser
  credentials, cookies, storage, headers, or profiles.
- A platform moves from `best_effort` or `dev-only` only after a recorded fixture/live test for the
  exact source shape, version, permission flow, and expected failure cases.
