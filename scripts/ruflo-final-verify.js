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
  writeFileSync("NEXT_STEPS.md", `# Next steps\n\nLive gate failed: ${JSON.stringify(result)}\n\n1. Render Dashboard -> dhansetu-hub -> Settings -> Custom Domains -> add and verify dhansetuhub.in and www.dhansetuhub.in.\n2. Cloudflare DNS -> CNAME @ and www to dhansetu-hub.onrender.com, Proxied ON.\n3. Purge Cloudflare cache.\n4. Run: \`VERIFY_SECONDS=300 ./scripts/plan-b-fallback.sh\`\n`);
  console.error(JSON.stringify(result));
  process.exitCode = 1;
}
