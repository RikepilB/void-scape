# Voidscape community feedback form

Build this as a Google Form for low-friction feedback from X, LinkedIn, and WhatsApp. Keep the
terminal survey in `research/surveys/voidscape-prototype.mjs` for facilitated technical tests.

## Form identity

**Title:** Help me improve the Voidscape prototype

**Description:**

> Voidscape is a local-first prototype that turns video or audio into selected frames, a
> timestamped transcript, and a manifest an AI agent can inspect. This form takes about 3-5
> minutes. Please do not enter passwords, cookies, private URLs, filenames, or confidential media
> details. You may respond anonymously. Your feedback will be used to improve the prototype.
>
> Prototype: https://voidscape.club/
> Source: https://github.com/RikepilB/void-scape

## Settings

- Do not collect email addresses automatically.
- Do not require sign-in and do not limit to one response.
- Do not shuffle questions.
- Show a progress bar.
- Keep response editing off unless there is a clear need.
- Do not publish raw responses or connect them to public spreadsheets.
- Retain raw responses only for this prototype iteration; review free text before sharing quotes.

**Confirmation message:**

> Thank you. I will use this feedback to fix repeated blockers before expanding the prototype. If
> you are open to a short follow-up test, message me directly through the channel where you found
> this form.

## Section 1 — About the respondent

1. **Which perspective best describes you today?**
   - Type: Multiple choice, required
   - Choices: Content creator; Student or researcher; Developer or agent builder; Business or
     professional user; Other

2. **Have you tried the Voidscape prototype?**
   - Type: Multiple choice, required, branching
   - `Yes, I completed the core flow` -> Section 2
   - `Yes, but I only completed part of it` -> Section 2
   - `Not yet, I only watched the showcase` -> Section 3

## Section 2 — For people who tested it

3. **What kind of source did you test?**
   - Type: Multiple choice, required
   - Choices: Included demo fixture; My own local media; Public YouTube video; Other public media
     URL; Signed-in or saved media

4. **What were you mainly trying to get from the media?**
   - Type: Multiple choice, required
   - Choices: Summary; Specific answer; Timestamped evidence; Transcript; Content review or
     feedback; Other

5. **Were you able to complete that task?**
   - Type: Multiple choice, required
   - Choices: Yes without help; Yes with some help; Partially; No

6. **How clear was the preview before processing?**
   - Type: Linear scale 1-5, required
   - Labels: `1 = not clear`, `5 = completely clear`

7. **How confident were you about what stayed local or could go to a cloud service?**
   - Type: Linear scale 1-5, required
   - Labels: `1 = not confident`, `5 = completely confident`

8. **How useful were the timestamped results?**
   - Type: Linear scale 1-5, required
   - Labels: `1 = not useful`, `5 = extremely useful`

9. **Where did you hesitate, get confused, or need help?**
   - Type: Paragraph, required

10. **What did you expect Voidscape to do that it did not do?**
    - Type: Paragraph, optional

11. **Would you use Voidscape again for a real task?**
    - Type: Multiple choice, required
    - Choices: Yes; Maybe; No

After this section, continue to Section 4.

## Section 3 — For people who watched but did not test

3. **Which use case feels most relevant to you?**
   - Type: Multiple choice, required
   - Choices: Saved learning videos; Meetings or calls; Courses or tutorials; Content review;
     Research; Personal recordings; None yet; Other

4. **What would most likely stop you from trying it?**
   - Type: Multiple choice, required
   - Choices: Installation; Command line; Privacy concerns; Supported sources; Unclear value; Time;
     Other

5. **What result would make this worth trying?**
   - Type: Paragraph, required

6. **How likely are you to try it after watching the showcase?**
   - Type: Linear scale 1-5, required
   - Labels: `1 = very unlikely`, `5 = very likely`

After this section, continue to Section 4.

## Section 4 — Final feedback

12. **What seems most valuable about this idea?**
    - Type: Paragraph, required

13. **What is the single most important improvement you would make?**
    - Type: Paragraph, required

14. **May I quote your feedback anonymously when describing what I learned?**
    - Type: Multiple choice, required
    - Choices: Yes; No

15. **Anything else I should know?**
    - Type: Paragraph, optional

## Interpretation

Use 5-8 completed prototype sessions for usability findings. Treat wider form responses from people
who only watched as concept feedback, not proof that the workflow works. Prioritise repeated task
failures and privacy misunderstandings before feature requests.
