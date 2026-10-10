export const modes = [
  {
    id: "tutor",
    label: "Guided learning",
    description: "Work through the idea, one step at a time.",
    prompt: "Explain the main concept and ask me a question.",
  },
  {
    id: "explainer",
    label: "Explain",
    description: "Unpack a concept using your document.",
    prompt: "Explain the key concept in detail.",
  },
  {
    id: "summarizer",
    label: "Study notes",
    description: "Condense the selected passages.",
    prompt: "Summarize this document",
  },
  {
    id: "quizzer",
    label: "Practice",
    description: "Test your understanding with questions.",
    prompt: "Create practice questions about the key concepts.",
  },
  {
    id: "reviewer",
    label: "Review my answer",
    description: "Compare your understanding with the source.",
    prompt: "",
  },
];
export function validatePages(start, end, total) {
  const from = start === "" ? null : Number(start);
  const to = end === "" ? null : Number(end);
  if (
    [from, to].some(
      (v) => v !== null && (!Number.isInteger(v) || v < 1 || v > total),
    )
  )
    return "Use page numbers within this document.";
  if (from && to && from > to)
    return "The start page must come before the end page.";
  return null;
}
export function sessionMarkdown(book, turns) {
  return (
    `# ${book.title}\n\nDRAX study session — generated content requires source review.\n\n` +
    turns
      .map(
        (t) =>
          `## ${t.query}\n\n${t.response.answer}\n\nMode: ${t.response.mode}\n\n` +
          (t.response.sources || [])
            .map((s) => `### [${s.id}] Page ${s.page}\n\n${s.text}`)
            .join("\n\n"),
      )
      .join("\n\n---\n\n")
  );
}
