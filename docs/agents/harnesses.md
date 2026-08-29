# Harness support

This page separates harness capabilities from behavior verified in Voidscape.

[Back to agent docs](index.md) · Canonical source: [multi-harness support](../harness-support.md)

## Evidence labels

| Label | Meaning |
| --- | --- |
| `personally-tested` | Reproduced on Richard's named setup and date |
| `vendor-documented` | Supported by current official vendor docs, not reproduced as a Voidscape test |
| `unverified` | Design intent or incomplete integration test; do not market as working |

## Support matrix

| Harness | Harness capability | Voidscape composition | Evidence |
| --- | --- | --- | --- |
| Codex or ChatGPT with Chrome | Work in user-approved tabs and continue a paired host session remotely | Select a permitted URL, then run the local CLI on the host | `vendor-documented`; browser-to-host CLI flow `personally-tested` on Richard's Windows setup |
| Claude Code with Claude in Chrome | Work in approved signed-in sites and continue the running local session remotely | Run Voidscape beside the local Claude Code session | Harness behavior `vendor-documented`; complete Voidscape composition `unverified` |
| Generic shell-capable agent | Execute commands and read local files | Drive guided or raw JSON commands while preserving gates | CLI contract `shipped`; harness discovery and approvals are harness-specific |
| Generic MCP-capable agent | Consume tool schemas when an MCP host exists | No production Voidscape MCP host exists | `planned`, `unverified` |

## OpenAI documentation

- [Codex Chrome extension](https://developers.openai.com/codex/chrome-extension/)
- [Codex remote connections](https://developers.openai.com/codex/remote-connections/)
- [Codex app browser](https://developers.openai.com/codex/app/browser/)

These links establish vendor capabilities. They do not prove that browser login state transfers to
the CLI; it does not.

## Anthropic documentation

- [Use Claude Code with Chrome](https://docs.anthropic.com/en/docs/claude-code/chrome)
- [Continue local sessions with Remote Control](https://docs.anthropic.com/en/docs/claude-code/remote-control)
- [Get started with Claude in Chrome](https://support.anthropic.com/en/articles/12012173-getting-started-with-claude-for-chrome)

## Host and authentication boundary

Remote control continues work on a host; it does not move that host's files, browser profile, or CLI
credentials to the phone. A browser connection may view a page the user is permitted to access,
but `yt-dlp` remains separately authenticated. For allowed account-scoped media, the user may set a
site-scoped Netscape cookie file through `READ_VIDEO_YTDLP_COOKIES`. Voidscape never discovers,
exports, or reads cookies from a browser profile.

See [authenticated sources](../authenticated-sources.md) and the
[browser/CLI evidence matrix](../chrome-use-case-matrix.md).
