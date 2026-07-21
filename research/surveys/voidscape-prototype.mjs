export default {
  id: "voidscape-prototype",
  title: "Voidscape prototype feedback",
  description:
    "A short anonymous survey after trying inspect, preview, and read. Do not enter names, emails, private URLs, filenames, or cookie data.",
  anonymous: true,
  questions: [
    {
      id: "tester_context",
      type: "select",
      prompt: "Which perspective best describes you today?",
      choices: [
        "content creator",
        "student or researcher",
        "developer or agent builder",
        "business or professional user",
        "other",
      ],
    },
    {
      id: "source_type",
      type: "select",
      prompt: "What kind of source did you test?",
      choices: [
        "included demo fixture",
        "my own local media",
        "public YouTube video",
        "other public media URL",
        "signed-in or saved media",
      ],
    },
    {
      id: "task_goal",
      type: "select",
      prompt: "What were you mainly trying to get from the media?",
      choices: [
        "summary",
        "specific answer",
        "timestamped evidence",
        "transcript",
        "content review or feedback",
        "other",
      ],
    },
    {
      id: "task_completion",
      type: "select",
      prompt: "Were you able to complete that task?",
      choices: [
        "yes without help",
        "yes with some help",
        "partially",
        "no",
      ],
    },
    {
      id: "preview_clarity",
      type: "select",
      prompt: "From 1 to 5, how clear was the preview before processing?",
      choices: [
        "1 - not clear",
        "2",
        "3",
        "4",
        "5 - completely clear",
      ],
    },
    {
      id: "privacy_confidence",
      type: "select",
      prompt: "From 1 to 5, how confident were you about what stayed local or could go to a cloud service?",
      choices: [
        "1 - not confident",
        "2",
        "3",
        "4",
        "5 - completely confident",
      ],
    },
    {
      id: "citation_usefulness",
      type: "select",
      prompt: "From 1 to 5, how useful were the timestamped results?",
      choices: [
        "1 - not useful",
        "2",
        "3",
        "4",
        "5 - extremely useful",
      ],
    },
    {
      id: "most_valuable",
      type: "longtext",
      prompt: "What was the most valuable part of the experience?",
    },
    {
      id: "biggest_friction",
      type: "longtext",
      prompt: "Where did you hesitate, get confused, or need help?",
    },
    {
      id: "missing_outcome",
      type: "longtext",
      prompt: "What did you expect Voidscape to do that it did not do?",
    },
    {
      id: "would_use_again",
      type: "select",
      prompt: "Would you use Voidscape again for a real task?",
      choices: ["yes", "maybe", "no"],
    },
    {
      id: "quote_permission",
      type: "confirm",
      prompt: "May the team quote your anonymous feedback when describing what was learned?",
    },
  ],
};
