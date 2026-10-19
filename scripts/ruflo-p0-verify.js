const fs = require('node:fs');

const checks = [
  ['origin health', 'https://dhansetu-hub.onrender.com/api/health'],
  ['public health', 'https://dhansetuhub.in/api/health'],
  ['homepage', 'https://dhansetuhub.in/'],
  ['sitemap', 'https://dhansetuhub.in/sitemap.xml'],
];

async function probe(label, url) {
  const response = await fetch(url, { cache: 'no-store' });
  const body = await response.text();
  return { label, url, status: response.status, paymentReady: body.includes('"paymentReady":true'), og: /og:title|Dhansetu Hub/.test(body), body: body.slice(0, 500) };
}

async function main() {
  const attempts = [];
  for (let attempt = 1; attempt <= 20; attempt += 1) {
    const results = await Promise.all(checks.map(([label, url]) => probe(label, url).catch((error) => ({ label, url, status: 0, error: String(error) }))));
    const pass = results[0].status === 200 && results[0].paymentReady && results[1].status === 200 && results[1].paymentReady && results[2].status === 200 && results[2].og && results[3].status === 200;
    attempts.push({ attempt, at: new Date().toISOString(), pass, results });
    if (pass) {
      fs.writeFileSync('LAUNCH_SUCCESS_P0.md', `# P0 launch verification\n\nPassed on attempt ${attempt}.\n\n\`\`\`json\n${JSON.stringify(results, null, 2)}\n\`\`\`\n`);
      return;
    }
    if (attempt < 20) await new Promise((resolve) => setTimeout(resolve, 15000));
  }
  fs.writeFileSync('NEXT_RETRY_P0.json', JSON.stringify({ reason: 'P0 live checks did not pass', attempts }, null, 2));
  process.exitCode = 1;
}

main();
