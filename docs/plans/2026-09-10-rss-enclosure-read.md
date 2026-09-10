# Selected RSS enclosure workflow

Issue #57 continuation, authorized under the engineering/test/QA/docs/merge goal.

- Preview one retained resource and exact byte/time limits without network/writes.
- Acquire anonymous public audio/video through existing pinned transport, checking
  redirects, type, bytes, truncation and explicit fetch approval.
- Remux through already-open descriptors with restricted protocols/demuxers;
  retain original bytes and a separate normalized first-video/audio representation.
- Follow local inspect/preview/read with independent processing permission and
  available local backend. Never download a model or upload to AI automatically.
- Bind completed media receipts, source identity, citations and notes. Preserve
  partial evidence; reject mutation or uncertain source provenance.

Validate transport failures/redirects/limits, actual descriptor remux and playlist
refusal, local backend gates, receipt/citation integrity and full suite. Run a
public media fetch plus visual read and controlled speech fixture plus local ASR,
inspect actual evidence, publish verified notes and test reuse. Neither fixture
proves a live podcast, subscriber/paywall workflow or independent harness success.

Descriptor behavior reference: [FFmpeg protocols](https://ffmpeg.org/ffmpeg-protocols.html#fd).
No upstream implementation code copied. No Iris or new provider installed.
