import { notFound } from "next/navigation";
import { findPdfTool } from "../tools";
import ToolWorkspace from "./ToolWorkspace";

export default async function PdfToolPage({ params }: { params: Promise<{ tool: string }> }) {
  const { tool: slug } = await params;
  const tool = findPdfTool(slug);
  if (!tool) notFound();
  return <ToolWorkspace tool={tool} />;
}
