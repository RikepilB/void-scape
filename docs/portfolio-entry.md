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
        title: 'read-video — Teaching AI Agents to Watch Video',
        tagline:
            'An AI coding agent can read images and PDFs — not video. read-video decomposes any video into frames plus a transcript, and prices the whole job before spending a cent or a token.',
        duration: 'Jun 2026 – Jul 2026',
        readTime: '6 min read',
        overview:
            'read-video is an open-source (MIT) Codex / Codex skill that gives AI agents genuine video comprehension: point it at a local file or a URL (YouTube, Loom, Vimeo…) and it extracts frames for the visual track and a transcript for the audio track — the two things an agent can actually consume. Its defining feature is the cost gate: a probe → estimate → run pipeline that prices the entire job (transcription dollars and agent-token cost) up front, defaults to free local transcription with faster-whisper, and only touches paid cloud backends after explicit approval. The engine is a single 1,300-line Python CLI built on the standard library, with an opt-in machine-readable protocol (`manifest`, `--envelope`, deterministic exit codes) added for agent callers. Live demo/landing page: https://rikepilb.github.io/read-video/.',
        problem:
            'Agents fake video understanding by reading titles and comments. Actually watching costs real money — frames dominate agent-token spend, and cloud transcription bills by the minute — so a naive implementation surprises users with the bill after the fact. The design problem was making video comprehension both real and pre-approved: never spend before showing the price, and never let audio leave the machine without explicit consent.',
        questions: [
            'What\'s the cheapest honest path to a transcript — and how often is it free?',
            'Can one skill serve multiple agent harnesses (Codex, Codex, Gemini CLI, Copilot CLI) from a single install?',
            'Does the skill measurably beat an agent improvising with ffmpeg on its own?',
            'What happens when a coding agent extends the same codebase months later — does the original design hold up under real adversarial review?',
        ],
        methodology: [
            {
                phase: 'Phase 1',
                title: 'Probe → Estimate → Run, with a Cost Gate',
                detail:
                    'probe inspects the input (duration, resolution, audio, existing captions); estimate computes the full cost — transcription dollars per backend and projected agent-token spend from frame count — before any work; run only executes after the user (or a zero-dollar threshold) approves. Nine transcription paths are ordered cheapest-and-most-private first: sidecar subtitles, URL captions, local faster-whisper and trx (all free) before Groq, OpenAI, OpenRouter and Gemini.',
                tech: ['Python', 'ffmpeg', 'yt-dlp', 'faster-whisper'],
            },
            {
                phase: 'Phase 2',
                title: 'A Stdlib-Only Engine',
                detail:
                    'The paid-API paths use hand-built multipart requests over urllib — no SDKs — so the free paths never pay an import cost and a missing optional dependency can never break probe or estimate. 120 pytest cases across 17 files pin down chunking, deduplication, cost estimation, frame extraction, and hardening (including an anchor fix against lookalike-domain spoofing and a subprocess-level test suite for the agent CLI contract).',
                tech: ['Python stdlib', 'pytest'],
            },
            {
                phase: 'Phase 3',
                title: 'Eval-Driven Skill Design',
                detail:
                    'The skill was benchmarked with an eval loop against a no-skill baseline: with the skill loaded, the agent passed 14 of 15 assertions (93.3%) across visual-summary, audio-comprehension and cost-gate scenarios, versus 66.7% baseline. One install script wires it into four harnesses: Codex, Codex, Gemini CLI and Copilot CLI.',
                tech: ['LLM Evals', 'Codex', 'PowerShell', 'Bash'],
            },
            {
                phase: 'Phase 4',
                title: 'Build Week: Agent Protocols, Adversarial Review, Honest Security',
                detail:
                    'Extended for OpenAI Build Week 2026 with Codex + GPT-5.6: adaptive local transcription tiers, GPT-5.6-native 32×32 patch cost accounting, and an opt-in agent-facing CLI protocol (`manifest`, `--envelope`/`--compact`, a deterministic exit-code taxonomy with retryability metadata). An adversarial code-review pass against the new cost/consent gate surfaced 9 findings; the 6 real defects were fixed with regression tests before shipping — including one caught only by actually running the documented commands, not by unit tests alone. A static security scanner flagged the intentional env-key-to-cloud-API data flow as CRITICAL; rather than hide it, the finding is disclosed and explained in a `SECURITY.md` the scanner\'s own report cross-checks against.',
                tech: ['Codex', 'GPT-5.6', 'Adversarial Code Review', 'Agent Protocols', 'GitHub Pages'],
            },
        ],
        results: [
            { metric: '93.3%', label: 'eval assertions passed with the skill, vs 66.7% baseline without it' },
            { metric: '9', label: 'transcription backends, ordered free-and-local first' },
            { metric: '120', label: 'tests over a 1,300-line stdlib-only engine' },
            { metric: '6', label: 'real bugs found by adversarial review and fixed before shipping' },
        ],
        keyFindings: [
            'Cost transparency is a UX feature for agents: showing the price before the work turns "the AI ran up my bill" into an informed yes/no.',
            'Local-first ordering (captions → Whisper on-device → paid APIs) makes the free path the default path — most videos never cost a cent to read.',
            'Evals beat vibes for skill design: a measured 93.3%-vs-66.7% gap is what separates "the skill helps" from hoping it does.',
            'Adversarial review plus actually running the documented commands caught a real regression unit tests missed entirely: a bug fix elsewhere in the same diff silently changed what the README\'s own privacy-proof example demonstrated.',
        ],
        conclusion:
            'read-video is the most complete open-source piece in this portfolio: MIT-licensed with contribution docs, issue templates, a demo GIF, a live GitHub Pages landing page (https://rikepilb.github.io/read-video/), 60+ commits of real iteration, and a measured eval improvement. It\'s also honest about scale — the eval set is small and iteration continues — but the shape is what production agent-tooling looks like: priced, tested, local-first, multi-harness, and reviewed like real software rather than shipped on vibes. Submitted to OpenAI Build Week 2026 (Developer Tools track).',
        github: 'https://github.com/RikepilB/read-video',
        stack: ['Python', 'ffmpeg', 'yt-dlp', 'faster-whisper', 'pytest', 'Codex', 'Codex', 'GPT-5.6'],
    },
```

## Spanish overlay — `src/data/projects-es-overlays.ts` (key `'read-video'`)

Translate the updated fields above the same way the existing overlay does — same shape as before
(`category`, `title`, `tagline`, `readTime`, `overview`, `problem`, `questions`, `methodology`,
`results`, `keyFindings`, `conclusion`; no `slug`/`github`/`stack` in the overlay). Not pre-written
here since it needs a real translation pass, not a mechanical one — the existing Spanish entry can
stay as a starting point and just needs Phase 4 + the updated stat tiles added.

## What changed vs. the existing "coming soon" draft

- Numbers corrected to the actual current repo state (not carried over from the pre-Build-Week
  draft): 997 → 1,300 line engine; 67 tests/11 files → 120 tests/17 files; 46 → 60+ commits on `main`.
- Added Phase 4 (Build Week: agent protocol, adversarial review, security disclosure) and a matching
  4th result tile + key finding — this is the "skills creation" and evals-adjacent methodology work
  from this session.
- Added the live GitHub Pages link (no dedicated schema field for it, so it's embedded in `overview`
  and `conclusion` as plain text, same pattern the schema already uses for prose).
- `status` recommended `'shipped'` — flagged above, easy to revert.
