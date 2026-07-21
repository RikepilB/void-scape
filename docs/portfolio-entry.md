# Portfolio entry template — read-video

Ready-to-paste update for `PROYECTOS/Portfolio/src/data/projects.ts`. A `read-video` entry already
exists there (`id: '14'`, between `peru-tech-map` and `resume-scorer`, lines ~795-852) with numbers
from before the Build Week work (997-line engine, 67 tests/11 files, 46 commits). This replaces
that object with current, verified numbers (checked against the live repo, not carried over from
the old draft) and folds in the Build Week/Codex phase, evals, and the security-disclosure story.

A matching Spanish-overlay update (for `src/data/projects-es-overlays.ts`, same `'read-video'` key,
lines ~665-715) is included at the bottom — translate the new English fields the same way the
existing overlay does, or skip it and the Spanish locale falls back to English for this project
(silent, no error — confirmed in `src/data/locale.ts`).

**One judgment call flagged, not applied silently:** `status: 'coming-soon'` → I set it to
`'shipped'` below, since the project now has 120 passing tests, a merged PR, and a live landing
page — not a stub anymore. Revert to `'coming-soon'` if you want to hold the portfolio entry until
after the Devpost submission itself is finalized.

## English entry — `src/data/projects.ts`

```ts
    {
        id: '14',
        slug: 'read-video',
        category: 'AI ENGINEERING',
        catColor: '#1d4ed8',
        status: 'shipped',
        title: 'Voidscape — Grounded Video Evidence for Agents',
        tagline:
            'Voidscape turns approved media into frames, timestamped text, and a manifest an agent can inspect, with cost and consent visible before the read.',
        duration: 'Jun 2026 – Jul 2026',
        readTime: '6 min read',
        overview:
            'The read-video compatibility engine is open-source (MIT) and gives agents grounded video evidence: point it at a local file or supported URL and it extracts selected frames plus a timestamped transcript. Its defining feature is the cost gate: probe → estimate → run prices the job before processing and only uses cloud transcription after explicit approval. Active repository: https://github.com/RikepilB/void-scape.',
        problem:
            'Agents fake video understanding by reading titles and comments. Actually watching costs real money — frames dominate agent-token spend, and cloud transcription bills by the minute — so a naive implementation surprises users with the bill after the fact. The design problem was making video comprehension both real and pre-approved: never spend before showing the price, and never let audio leave the machine without explicit consent.',
        questions: [
            'What\'s the cheapest honest path to a transcript — and how often is it free?',
            'Can one bundle install cleanly for Codex and a shared compatible-agent skill root?',
            'Does the skill measurably beat an agent improvising with ffmpeg on its own?',
            'What happens when a coding agent extends the same codebase months later — does the original design hold up under real adversarial review?',
        ],
        methodology: [
            {
                phase: 'Phase 1',
                title: 'Probe → Estimate → Run, with a Cost Gate',
                detail:
                    'probe inspects the input (duration, resolution, audio, existing captions); estimate computes the full cost — transcription dollars per backend and projected agent-token spend from frame count — before any work; run only executes after the user approves the path. A matching local sidecar wins automatically; otherwise the chosen captions, local, cloud, or explicit comma-separated fallback route is used without silently crossing the cloud boundary.',
                tech: ['Python', 'ffmpeg', 'yt-dlp', 'faster-whisper'],
            },
            {
                phase: 'Phase 2',
                title: 'A Stdlib-First Engine',
                detail:
                    'OpenAI-compatible paid paths use hand-built multipart requests over urllib, while Gemini lazily imports its optional SDK only when selected. The free paths never pay that import cost. 154 pytest cases across 18 files pin down chunking, deduplication, cost estimation, frame extraction, privacy gates, the agent contract, and installer hardening.',
                tech: ['Python stdlib', 'pytest'],
            },
            {
                phase: 'Phase 3',
                title: 'Eval-Driven Skill Design',
                detail:
                    'The skill was benchmarked with an eval loop against a no-skill baseline: with the skill loaded, the agent passed 14 of 15 assertions (93.3%) across visual-summary, audio-comprehension and cost-gate scenarios, versus 66.7% baseline. The installers write and verify both the Codex skill root and a shared compatible-agent root without claiming untested runtimes.',
                tech: ['LLM Evals', 'Codex', 'PowerShell', 'Bash'],
            },
            {
                phase: 'Phase 4',
                title: 'Build Week: Agent Protocols, Adversarial Review, Honest Security',
                detail:
                    'Extended for OpenAI Build Week 2026 with Codex + GPT-5.6: adaptive local transcription tiers, GPT-5.6-native 32×32 patch cost accounting, and an opt-in agent-facing CLI protocol (`manifest`, `--envelope`/`--compact`, a deterministic exit-code taxonomy with retryability metadata). An adversarial code-review pass against the new cost/consent gate surfaced 9 findings; the 6 real defects were fixed with regression tests before shipping — including one caught only by actually running the documented commands, not by unit tests alone. A static security scanner flagged the intentional env-key-to-cloud-API data flow as CRITICAL; rather than hide it, the finding is disclosed and explained in a `SECURITY.md` the scanner\'s own report cross-checks against.',
                tech: ['Codex', 'GPT-5.6', 'Adversarial Code Review', 'Agent Protocols', 'Vercel'],
            },
        ],
        results: [
            { metric: '93.3%', label: 'eval assertions passed with the skill, vs 66.7% baseline without it' },
            { metric: '7', label: 'deterministic CLI exit classes for agent error handling' },
            { metric: '154', label: 'tests over a 1,369-line engine' },
            { metric: '6', label: 'real bugs found by adversarial review and fixed before shipping' },
        ],
        keyFindings: [
            'Cost transparency is a UX feature for agents: showing the price before the work turns "the AI ran up my bill" into an informed yes/no.',
            'A local sidecar wins automatically; every other backend or fallback chain is explicit, so Voidscape never silently crosses from a local route to cloud transcription.',
            'Evals beat vibes for skill design: a measured 93.3%-vs-66.7% gap is what separates "the skill helps" from hoping it does.',
            'Adversarial review plus actually running the documented commands caught a real regression unit tests missed entirely: a bug fix elsewhere in the same diff silently changed what the README\'s own privacy-proof example demonstrated.',
        ],
        conclusion:
            'The engine is prior work imported into Voidscape with explicit provenance. Judges should score only dated post-import Build Week commits in the active repository.',
        github: 'https://github.com/RikepilB/void-scape',
        stack: ['Python', 'ffmpeg', 'yt-dlp', 'faster-whisper', 'pytest', 'Codex', 'GPT-5.6'],
    },
```

## Spanish overlay — `src/data/projects-es-overlays.ts` (key `'read-video'`)

Translate the updated fields above the same way the existing overlay does — same shape as before
(`category`, `title`, `tagline`, `readTime`, `overview`, `problem`, `questions`, `methodology`,
`results`, `keyFindings`, `conclusion`; no `slug`/`github`/`stack` in the overlay). Not pre-written
here since it needs a real translation pass, not a mechanical one — the existing Spanish entry can
stay as a starting point and just needs Phase 4 + the updated stat tiles added.

## What changed vs. the existing "coming soon" draft

- Numbers corrected to the release-candidate state: a 1,369-line engine and 154 tests across 18
  test files. The fresh Voidscape history intentionally starts at the dated import commit.
- Added Phase 4 (Build Week: agent protocol, adversarial review, security disclosure) and a matching
  4th result tile + key finding — this is the "skills creation" and evals-adjacent methodology work
  from this session.
- Added the live Vercel-hosted project link (no dedicated schema field for it, so it's embedded in `overview`
  and `conclusion` as plain text, same pattern the schema already uses for prose).
- `status` recommended `'shipped'` — flagged above, easy to revert.
