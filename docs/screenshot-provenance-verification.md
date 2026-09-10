# Screenshot provenance acceptance — issue #92

Date: 2026-09-10. Scope: optional local image sidecars, not a screenshot provider integration.

## Reproducible synthetic visual check

Use fresh output folders:

```text
python scripts/create-screenshot-fixture.py --out screenshot-fixture
python skill/scripts/voidscape.py inspect screenshot-fixture --json
python skill/scripts/voidscape.py preview screenshot-fixture --json
python skill/scripts/voidscape.py read screenshot-fixture --workdir screenshot-evidence --json
```

The generator creates a 320×240 original with green upper half and red lower half, plus a
320×120 crop containing only the upper half. It never captures a real website or screen.

Executed all three reader stages locally, then opened both produced evidence images with the
image inspection tool. Observed green above red in `[image 1]`; only green in `[image 2]`.
The red region is absent from the crop, not evidence that the original had no red content.
The manifest preserved the original bytes, natural order, crop bounds and untrusted parent
hash claim. Both images retained `coverage: unknown`. No OCR, live browser QA, producer
authentication or page-completeness proof is claimed by this test.

## Automated gates

`tests/test_image_provenance.py` covers missing metadata at each stage, origin-only URL
redaction, bounded malformed/duplicate metadata, unknown versions and path fields, invalid
geometry including nonfinite/huge scale, injection-shaped text, replaced inputs, copy-time
hash/dimension changes, ordering, sidecar symlinks and derived scope.
`tests/test_image_reader.py` retains the existing image format and byte-copy regressions.
`tests/test_read_stages.py` retains partial-copy evidence semantics using the extended probe
shape. Invalid metadata fails closed; a hash/dimension mismatch cannot publish a completed
manifest. Earlier completed items can still be represented honestly as partial evidence.

The Windows installer was exercised against two temporary skill roots (not user globals),
with frontmatter and CLI checks passing for Voidscape and its compatibility alias.
The installed CLI completed the generated 12-second demo's inspect → audio preview → read
using its local transcript sidecar, with no cloud transfer or model download. Plugin mirror
and generated documentation checks passed; synchronizing source files did not install or
enable the plugin. Iris and plugin installation restrictions remain unchanged.

## Deliberate limitations

- URL paths are discarded, sacrificing exact page identity to avoid retaining path tokens.
- Producer IDs and hostnames are not authenticated or general-purpose secret detection.
- Parent hashes and full-page labels remain producer claims, even when syntactically valid.
- Metadata is a snapshot of local claims at import; consumers must treat it as untrusted.
- No screenshot provider, browser extension, scheduler or account action is introduced.
