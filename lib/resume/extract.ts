export const MAX_RESUME_BYTES = 5 * 1024 * 1024;
export const MAX_RESUME_TEXT = 100_000;

const STOP_WORDS = new Set([
  "about", "after", "again", "also", "and", "are", "from", "have", "into",
  "more", "over", "that", "their", "there", "these", "this", "those", "with",
]);

export function normalizeResumeText(value: string) {
  return value.replace(/\u0000/g, "").replace(/\r\n?/g, "\n").replace(/[ \t]+/g, " ").replace(/\n{3,}/g, "\n\n").trim().slice(0, MAX_RESUME_TEXT);
}

export function keywordGaps(resumeText: string, jobDescription: string) {
  const resume = new Set((resumeText.toLowerCase().match(/[a-z][a-z0-9+#.-]{2,}/g) ?? []));
  const terms = (jobDescription.toLowerCase().match(/[a-z][a-z0-9+#.-]{2,}/g) ?? [])
    .filter((term) => !STOP_WORDS.has(term));
  return [...new Set(terms)].filter((term) => !resume.has(term)).slice(0, 30);
}

export function isSupportedResume(fileName: string, mimeType: string) {
  const extension = fileName.toLowerCase().split(".").pop();
  return (extension === "pdf" && (!mimeType || mimeType === "application/pdf"))
    || (extension === "docx" && (!mimeType || mimeType === "application/vnd.openxmlformats-officedocument.wordprocessingml.document"));
}
