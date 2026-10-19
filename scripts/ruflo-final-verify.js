import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";

const check = (url) => {
  try { return execFileSync("curl", ["-L", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "20", url], { encoding: "utf8" }).trim(); }
  catch { return "000"; }
};
const origin = check("https://dhansetu-hub.onrender.com/api/health");
const publicCode = check("https://dhansetuhub.in/api/health");
const result = { checkedAt: new Date().toISOString(), origin, public: publicCode };
if (origin === "200" && publicCode === "200") {
  writeFileSync("LAUNCH_SUCCESS.md", `# Launch success\n\n\`\`\`json\n${JSON.stringify(result, null, 2)}\n\`\`\`\n`);
  console.log(JSON.stringify(result));
} else {
  writeFileSync("NEXT_STEPS.md", `# Next steps\n\nLive gate failed: ${JSON.stringify(result)}\n\nRun after Render/Cloudflare manual repair:\n\n\`VERIFY_SECONDS=300 ./scripts/plan-b-fallback.sh\`\n`);
  console.error(JSON.stringify(result));
  process.exitCode = 1;
}
