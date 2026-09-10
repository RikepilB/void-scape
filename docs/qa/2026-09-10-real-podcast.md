# Real public podcast acceptance

Tested on Windows against BBC's public
[6 Minute English feed](https://podcasts.files.bbci.co.uk/p02pc9tn.rss), selecting
the September 3 episode, “Climate change and extreme weather”. This is one
provider case, not completion of issue #57 or independent harness acceptance.

- Feed preview, explicit capture and enclosure selection succeeded.
- Anonymous download retained 3,645,271 bytes of audio/mpeg through three redirects
  under a 16 MiB budget. Original bytes and normalized media have verified hashes.
- Inspect reported 446.01 seconds. Audio preview reported cached local small
  Whisper, with no install, cloud-transfer or model-download gate.
- Local media reading completed. The full retained ASR transcript was inspected;
  it contains the programme and advertising at its boundaries.
- A short authored note with actual retained timestamps published successfully;
  a separate publisher inspection verified its retained artifacts.

The audio was not independently listened to or aligned against an authoritative
reference transcript. No word-error-rate or transcription-accuracy claim is made.
Ad insertion means these timestamps apply only to the retained media version.
Private accounts, cloud transcription and model downloads were not used. The
full transcript and media remain local QA artifacts, outside the repository.

## Defect reproduced and corrected

The original capture stored an empty body despite a 957-character HTML description.
The official feed also includes an empty Media RSS `media:content` attachment.
Matching only the local tag name selected that attachment ahead of the description.

The reader now selects recognized RSS/Atom body namespaces and skips empty body
candidates. Regression cases cover empty and nonempty Media RSS attachments and
an empty Atom content field with an available summary. A fresh real-feed capture
retained 691 characters of cleaned description. The original capture and its
hash-bound read receipt were preserved; existing evidence was not rewritten.

Validation: 46 article-reader tests passed. The full suite reported 1,253 passed
and one stale generated-plugin failure; after regenerating the bundled copy,
that exact test passed. Final hosted checks are recorded on the associated PR.
Generating the repository bundle does not install or clear its adoption gate.
