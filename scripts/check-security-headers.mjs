import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {contentSecurityPolicy} from '../config/content-security-policy.mjs';
import config from '../next.config.mjs';

const production={NODE_ENV:'production',NEXT_PUBLIC_SUPABASE_URL:'https://project.supabase.co'};
function directives(policy){return new Map(policy.split(';').map(x=>{const [key,...values]=x.trim().split(/\s+/);return [key,values];}));}
test('production limits active content and forbids eval',()=>{
 const policy=contentSecurityPolicy(production), d=directives(policy);
 assert.deepEqual(d.get('object-src'),["'none'"]);assert.deepEqual(d.get('base-uri'),["'self'"]);
 assert.deepEqual(d.get('frame-ancestors'),["'none'"]);assert.deepEqual(d.get('form-action'),["'self'"]);
 assert.ok(!policy.includes("'unsafe-eval'"));assert.ok(policy.includes('upgrade-insecure-requests'));
 assert.ok(d.get('script-src').includes("'unsafe-inline'"),'Existing static Next hydration remains compatible');
 assert.ok(!d.get('script-src').includes('https:'));assert.ok(!policy.includes('\n'));
});
test('existing payment, font, video, analytics and auth origins are retained',()=>{
 const d=directives(contentSecurityPolicy(production));
 for(const value of ['https://checkout.razorpay.com','https://connect.facebook.net','https://app.posthog.com'])assert.ok(d.get('script-src').includes(value));
 assert.ok(d.get('style-src').includes('https://fonts.googleapis.com'));
 assert.ok(d.get('font-src').includes('https://fonts.gstatic.com'));
 assert.ok(d.get('media-src').includes('https://d8j0ntlcm91z4.cloudfront.net'));
 assert.ok(d.get('img-src').includes('https://d2ol7oe51mr4n9.cloudfront.net'));
 assert.ok(d.get('connect-src').includes('https://project.supabase.co'));
 assert.ok(d.get('connect-src').includes('wss://project.supabase.co'));
});
test('custom analytics and Supabase URLs become origins, never policy fragments',()=>{
 const policy=contentSecurityPolicy({...production,NEXT_PUBLIC_POSTHOG_HOST:'https://metrics.example.com/path?x=1'});
 assert.ok(policy.includes('https://metrics.example.com'));assert.ok(!policy.includes('/path?'));
 for(const value of ['javascript:alert(1)','https://user:password@example.com','http://metrics.example.com'])assert.ok(!contentSecurityPolicy({...production,NEXT_PUBLIC_POSTHOG_HOST:value}).includes(value));
});
test('eval is allowed in development only',()=>{
 const policy=contentSecurityPolicy({NODE_ENV:'development'});assert.ok(policy.includes("'unsafe-eval'"));assert.ok(!policy.includes('upgrade-insecure-requests'));
});
test('global Next headers and no-store API behavior coexist',async()=>{
 const rules=await config.headers();const headers=rules.find(x=>x.source==='/(.*)').headers;
 assert.equal(headers.filter(h=>h.key==='Content-Security-Policy').length,1);
 assert.ok(headers.some(h=>h.key==='Strict-Transport-Security'));
 assert.equal(rules.find(x=>x.source==='/api/:path*').headers[0].value,'no-store');
 assert.ok(rules.find(x=>x.source==='/.well-known/security.txt').headers.some(h=>h.value.startsWith('text/plain')));
});
test('security.txt has contact, canonical HTTPS URI and a future expiry within one year',async()=>{
 const text=await readFile(new URL('../public/.well-known/security.txt',import.meta.url),'utf8');
 assert.match(text,/^Contact: mailto:support@dhansetuhub.in$/m);
 assert.match(text,/^Canonical: https:\/\/dhansetuhub.in\/\.well-known\/security.txt$/m);
 const expiry=Date.parse(text.match(/^Expires: (.+)$/m)[1]);assert.ok(expiry>Date.now());assert.ok(expiry-Date.now()<366*86400000);
});
