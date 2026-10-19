import { describe, expect, it } from "vitest";
import { isSupportedResume, keywordGaps, normalizeResumeText } from "./extract";

describe("resume extraction helpers", () => {
  it("normalizes untrusted extracted text and caps its size", () => {
    expect(normalizeResumeText("A\r\n\r\n\r\n B\u0000")).toBe("A\n\n B");
  });

  it("returns only explainable missing job terms", () => {
    expect(keywordGaps("TypeScript and React", "React TypeScript Kubernetes AWS")).toEqual(["kubernetes", "aws"]);
  });

  it("accepts only PDF and DOCX uploads", () => {
    expect(isSupportedResume("resume.pdf", "application/pdf")).toBe(true);
    expect(isSupportedResume("resume.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")).toBe(true);
    expect(isSupportedResume("resume.exe", "application/octet-stream")).toBe(false);
  });
});
