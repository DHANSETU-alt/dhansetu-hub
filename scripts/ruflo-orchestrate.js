import { execFileSync } from "node:child_process";
const run = (command, args) => execFileSync(command, args, { stdio: "inherit", env: process.env });
run("bash", ["scripts/verify-live.sh"]);
run("node", ["scripts/cloudflare-dns-audit.js"]);
run("npm", ["run", "typecheck"]);
run("npm", ["run", "lint"]);
run("npm", ["test", "--", "--run"]);
