# SkillSpector static review — 2026-09-04

## Gate result

- Command: `skillspector scan skill --no-llm --format json --output
  C:\tmp\voidscape-skillspector-final-20260904.json`
- Coverage: 13 of 13 skill components; static analysis only
- Tool: SkillSpector 2.3.7; 22 findings after heuristic filtering; no LLM meta-analysis
- Result: score `100`, severity `CRITICAL`, recommendation `DO_NOT_INSTALL`
- Raw report: `C:\tmp\voidscape-skillspector-final-20260904.json`
- SHA-256: `F797B922BC89476869EA90791AD68A445E37E622E35698DDCF96371A6D08CB1F`
- Decision: **stop install and publication**. The local plugin stays `dev-only` until Richard or an
  independent security review approves an exact remediation/suppression plan and a new scan.

The plugin skill tree is byte-for-byte synchronized with `skill/`, so this result applies to both.
Plugin schema validation is not a security approval.

## Manual disposition, not an override

| Finding group | Static severity | Observed code intent | Current disposition |
| --- | --- | --- | --- |
| Provider key reaches a network request | Critical | Existing cloud transcription reads one named provider key and sends it only to the fixed endpoint selected from the in-code backend table after the explicit per-job cloud gate | Expected product capability, but still requires independent approval before plugin install |
| Provider environment-variable reads | High | Named API-key variables for explicitly selected cloud backends | Same stop gate; never printed or placed in generated evidence |
| Subprocess/output heuristics | High/medium | Existing FFmpeg, FFprobe, yt-dlp, and optional screenpipe calls use argument arrays and `shell=False`; screenpipe status is parsed and normalized | Tests cover argument boundaries, error handling, and normalized output; scanner warning remains unsuppressed |
| `.env` credential-path heuristic | High | The detected string is an exclusion in the skill copy routine, not a credential read | False-positive shape; remains unsuppressed in the raw report |
| `sudo`/command-chain heuristic | High/medium | A platform-specific install hint printed to the user; the CLI does not execute it | Not an execution path; remains unsuppressed |
| Missing declared permissions | Medium | The current Codex skill schema and local validator pass, but SkillSpector cannot infer the consent-gated network/subprocess intent | Evaluate explicit permission metadata only against a documented supported schema |

## Required follow-up before any install

1. Independently review the built plugin tree, cloud endpoints, key handling, subprocess arguments,
   and error redaction.
2. Decide whether the installable plugin should exclude cloud backends or carry a reviewed,
   narrowly documented permission declaration.
3. If a suppression baseline is used, approve each exact rule/location with rationale; never
   suppress the whole category.
4. Rerun SkillSpector and the complete test/package/fixture gates, then record the new report hash.

No baseline was generated and no finding was suppressed in this pass.
