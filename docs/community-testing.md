# Community prototype testing

Use this protocol to learn whether a new tester can complete Voidscape's core workflow and
understand its privacy gate. This is prototype research, not statistically representative market
validation.

For low-friction responses from people recruited through social media, use the matching
[public feedback form specification](community-feedback-form.md). For the 50-60 second social
video, follow the [community showcase shot list](community-showcase-shot-list.md).

## Recommended first round

Run 5-8 moderated usability sessions. Include a mix of content creators, students/researchers, and
developers. Ask each participant to use either the included demo fixture, a public URL, or media
they own and are comfortable processing.

Measure these outcomes:

- Can the participant complete `inspect -> preview -> read`?
- Do they understand what the preview estimates and what requires approval?
- Can they find a useful answer and trace it to a timestamp?
- Where do they need facilitator help?
- Would they use the workflow again for a real task?

Do not coach during the first attempt. Ask the participant to think aloud, note where they pause,
and help only after recording the point of friction.

## Before each session

1. Explain that Voidscape is a prototype and that failures are product feedback, not participant
   mistakes.
2. Explain that local processing is the default and cloud/model-download actions require explicit
   approval.
3. Do not ask for passwords, cookies, private source URLs, filenames, or account access.
4. Ask separately before recording screen, voice, name, or contact information. This protocol does
   not require any of them.
5. Tell the participant that survey answers are saved locally on the machine running the survey and
   will only be shared if they choose to export and send them.

## Prototype task

From the Voidscape repository root:

```powershell
python scripts/create-demo-fixture.py
python skill/scripts/voidscape.py inspect samples/build-week-demo.mp4
python skill/scripts/voidscape.py preview samples/build-week-demo.mp4 --tier both --backend captions
python skill/scripts/voidscape.py read samples/build-week-demo.mp4 --tier both --backend captions --workdir samples/community-test-output
```

Complete the platform-specific installation steps in the [README](../README.md) before the session.
The four commands above are otherwise the same on PowerShell, Bash, and zsh.

Ask the participant to inspect the transcript, frames, and manifest, then answer:

> What happens in this media, and which timestamps support your answer?

After the fixture succeeds, optionally repeat with one public URL or participant-owned local file.
Signed-in/saved media is advanced coverage and requires the user-controlled authentication steps in
[Authenticated sources](authenticated-sources.md).

## Run the survey

The survey is a dependency-free `.mjs` definition consumed by
[`@crafter/survey-cli`](https://github.com/RikepilB/survey-cli). Bun 1.1 or newer is required.

```powershell
bunx @crafter/survey-cli take voidscape-prototype --dir research/surveys
```

Answers are stored under the survey CLI's local data directory. For facilitated sessions, run every
survey on the facilitator's machine so responses remain together. For remote sessions, the
participant can export their own response and send it through a channel they trust:

```powershell
New-Item -ItemType Directory -Force research\responses | Out-Null
bunx @crafter/survey-cli responses voidscape-prototype --export json |
  Out-File -Encoding utf8 research\responses\voidscape-survey-responses.json
```

Bash/zsh export:

```bash
mkdir -p research/responses
bunx @crafter/survey-cli responses voidscape-prototype --export json \
  > research/responses/voidscape-survey-responses.json
```

The `research/responses/` directory and common survey-export filenames are ignored by Git. Review
exports before sharing: free-text answers may still contain information a participant entered by
mistake.

## Synthesis after 5-8 sessions

Group evidence into four buckets:

1. Task failures that block the core workflow.
2. Consent or privacy misunderstandings.
3. Comprehension problems with frames, transcripts, manifests, or timestamps.
4. Feature requests that are valuable but do not block the prototype.

Fix repeated blockers first. Preserve exact anonymous quotes only when `quote_permission` is true.
Do not treat a small convenience sample or a high average rating as proof of broad demand.
