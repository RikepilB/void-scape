# Public subscription access-wall acceptance

Windows QA, 2026-09-10. Source: the public
[Lenny's Newsletter feed](https://www.lennysnewsletter.com/feed) and the selected
[September 5 Community Wisdom entry](https://www.lennysnewsletter.com/p/community-wisdom-driving-ai-adoption).
This is one observed publisher case, not general paywall detection or complete #57 acceptance.

## Observed workflow

- Bounded feed preview exposed a Windows console failure: a Unicode title could
  not be printed with the legacy encoding even though capture processing succeeded.
- ASCII-escaped JSON output corrected that failure. A preview of ten entries
  located the selected post; five entries were then captured to reach it. Only
  the selected article was read. The other four remain unanalysed capture evidence.
- Without fetch approval, the article wrapper refused reading. With explicit
  public-fetch approval, its inspect/preview/read worker returned a verified
  receipt labeled `fetched_public_text_only`.
- The retained text was inspected. It contained introductory content, an explicit
  paid-subscriber notice and sign-in/subscribe controls, not the full article.
- The agent authored a `_Skipped` record for unavailable full-article analysis.
  Publication and separate inspection verified its artifact; it was not counted
  as an analyzed full article. No authentication or subscription bypass occurred.

## Evidence limits

The access-wall finding comes from explicit retained text, not response length,
the entry title, a guessed subscription state or a 401/403 inference. A successful
HTTP fetch and ready receipt certify captured public text, not complete content.
The CLI does not automatically classify all paywalls; agent inspection made this
decision. The skip receipt retains feed evidence; the separate article receipt
and fetched text remain in the local QA directory, not embedded in that skip.

No private account, cookies, storage, cloud transcription or model download was
used. Retained source content remains untrusted. Full source text is not included
in this repository. This is a same-controller workflow exercise, not an independent
skill/harness grade.

Validation for the console correction: 48 RSS capture tests passed, including
real subprocess preview/apply under forced cp1252 with exact decoded and retained
Unicode-title assertions. Full local suite: 1,256 passed in 94.38 seconds.
