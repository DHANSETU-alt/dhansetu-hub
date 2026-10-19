const zone = process.env.CLOUDFLARE_ZONE_ID;
const token = process.env.CLOUDFLARE_API_TOKEN;
if (!zone || !token) { console.error('Set CLOUDFLARE_ZONE_ID and CLOUDFLARE_API_TOKEN'); process.exit(2); }
const res = await fetch(`https://api.cloudflare.com/client/v4/zones/${zone}/dns_records?per_page=100`, { headers: { Authorization: `Bearer ${token}` } });
if (!res.ok) throw new Error(`Cloudflare API ${res.status}`);
const body = await res.json();
const records = body.result ?? [];
const banned = records.filter(r => r.type === 'A' && /^(104|172)\./.test(r.content));
console.log(JSON.stringify({ zone, records, banned, correctRecords: [{ type: 'CNAME', name: '@', content: 'dhansetu-hub.onrender.com', proxied: false }, { type: 'CNAME', name: 'www', content: 'dhansetu-hub.onrender.com', proxied: false }] }, null, 2));
if (banned.length) process.exitCode = 1;
