<!-- Thanks for the PR! Keep changes focused; see CONTRIBUTING.md. -->

## What & why
<!-- What does this change, and what problem does it solve? -->

## How tested
<!-- Exact commands + outcome. "probe/estimate emit valid JSON", "transcribed a 60s clip with backend X", etc. -->
```
$ python -m py_compile skill/scripts/video.py
$ python skill/scripts/video.py estimate "samples/clip.mp4" --tier both --human
```

## Checklist
- [ ] Cost gate still blocks spend/upload before a user yes
- [ ] No secrets / media / personal config added; `.gitignore` intact
- [ ] `py_compile` clean; `probe` / `estimate` JSON valid on a file and (if relevant) a URL
- [ ] Docs updated if behavior or flags changed
- [ ] Change is focused (no unrelated refactors)
