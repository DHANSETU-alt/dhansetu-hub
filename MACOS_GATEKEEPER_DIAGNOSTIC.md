# macOS Gatekeeper Diagnostic — esbuild / workerd

## Headline finding

**Neither `esbuild` nor `workerd` exist anywhere in `/Users/apple/shakthi-os`.** A full recursive search of this project (including `dashboard/node_modules`) found zero matches for either binary. **SHAKTHI OS does not depend on them, directly or transitively.** This is not an assumption — it's a `find` across the whole project tree that came back empty.

They exist in a completely different, pre-existing set of projects under `/Users/apple/Documents/ChatGPT/box AI/` (and mirrored copies under `~/.codex/.chatgpt-projects/` and `~/Documents/Codex/`) — most relevantly `dhansetu-hub-live`, `dhansetu-pdf-studio`, and `dhansetu-peopledesk`. If the Gatekeeper blocks are happening while you work in this Mac generally, they're coming from one of *those* projects, not from anything built in this session.

## 1. Exact esbuild path

Checked in `dhansetu-hub-live` (the most likely candidate — same issue confirmed present in `dhansetu-pdf-studio`, `dhansetu-peopledesk`, `partner-roadmap`, and `public-landing` too, see §6):

```
/Users/apple/Documents/ChatGPT/box AI/dhansetu-hub-live/node_modules/.bin/esbuild
  → symlinks to →
/Users/apple/Documents/ChatGPT/box AI/dhansetu-hub-live/node_modules/esbuild/bin/esbuild
  (this is a JS shim script, not the real binary)

Real native binary:
/Users/apple/Documents/ChatGPT/box AI/dhansetu-hub-live/node_modules/@esbuild/darwin-x64/bin/esbuild
```
`file` confirms: `Mach-O 64-bit executable x86_64` — matches this Mac's architecture (`uname -m` → `x86_64`, an Intel Mac).

There are also **4 duplicate copies** of esbuild vendored inside nested `node_modules` (normal for npm's dependency resolution, not a bug):
```
node_modules/esbuild/bin/esbuild
node_modules/drizzle-kit/node_modules/esbuild/bin/esbuild
node_modules/wrangler/node_modules/esbuild/bin/esbuild
node_modules/@esbuild-kit/core-utils/node_modules/esbuild/bin/esbuild
```

## 2. Exact workerd path

```
/Users/apple/Documents/ChatGPT/box AI/dhansetu-hub-live/node_modules/@cloudflare/workerd-darwin-64/bin/workerd
```

## 3. Which package installed them — real root cause

This is the actual, verified reason for the blocks, not a guess:

```
$ codesign -dv ".../@esbuild/darwin-x64/bin/esbuild"
  code object is not signed at all

$ spctl -a -vv ".../@esbuild/darwin-x64/bin/esbuild"
  rejected
  source=no usable signature

$ codesign -dv ".../@cloudflare/workerd-darwin-64/bin/workerd"
  code object is not signed at all

$ spctl -a -vv ".../@cloudflare/workerd-darwin-64/bin/workerd"
  rejected
  source=no usable signature
```

**Both binaries are completely unsigned**, and `spctl` — the actual command-line tool behind Gatekeeper's assessment — rejects both outright. `xattr -l` also shows a `com.apple.provenance` attribute on both (a newer macOS attribute, related to but distinct from the classic `com.apple.quarantine` flag, also tracked by Gatekeeper). This is why the blocks are *repeated*: it's not one bad download that a quarantine-clear would fix once — every fresh `npm install` re-downloads these same unsigned binaries from npm's registry, so the condition recurs.

**Honest note on scope of this evidence**: this is the real, current, static state of the files — confirmed with `codesign`/`spctl`, the authoritative tools. I also attempted to pull historical Gatekeeper denial events from the unified system log (`log show --predicate 'eventMessage CONTAINS "esbuild"' --last 14d`) to timestamp-correlate against when you actually saw the blocks, but that query didn't return within a reasonable time and I didn't wait indefinitely for it — so this report is grounded in *why the block would happen*, verified directly, not in a captured log of the exact moment it did.

## 4. Which SHAKTHI OS component depends on them

**None.** Confirmed by:
```
$ find /Users/apple/shakthi-os -path "*/node_modules/*" -iname "esbuild"   → no results
$ find /Users/apple/shakthi-os -path "*/node_modules/*workerd*"            → no results
$ grep -c "esbuild\|workerd" dashboard/package-lock.json                   → 0
```
SHAKTHI OS's dashboard uses Next.js's own bundled Turbopack (not esbuild) and has no Cloudflare dependency anywhere.

## 5. Whether the binaries are required — for the projects that actually have them

Real dependency chain, from `npm explain` inside `dhansetu-hub-live`:

**esbuild** — required by two independent paths:
```
esbuild ← tsx ← drizzle-kit (root devDependency, DB schema/migration tool)
esbuild ← peerOptional of vite (root devDependency, the dev server/bundler)
```
**Yes, required** — `vite` (the actual local dev server for this app) and `drizzle-kit` (DB migrations) both need a working esbuild. Without it, `npm run dev` and any `drizzle-kit` command fail outright, unsigned-binary block or not.

**workerd** — required by:
```
workerd ← miniflare ← wrangler (root devDependency, Cloudflare's CLI)
workerd ← miniflare ← @cloudflare/vite-plugin (root devDependency)
workerd ← peerOptional of @cloudflare/unenv-preset ← wrangler
```
**Conditionally required** — only if this project's local dev workflow actually uses `wrangler dev` or `@cloudflare/vite-plugin`'s dev server, which emulate the Cloudflare Workers runtime locally via a real `workerd` process. Given the project is named `dhansetu-hub-live` and both `wrangler` and `@cloudflare/vite-plugin` are intentional (not accidental transitive) devDependencies, this strongly suggests the app deploys to Cloudflare Pages/Workers — in which case `workerd` is genuinely needed to test that locally. If it turns out this project *doesn't* actually deploy to Cloudflare, `wrangler` + `@cloudflare/vite-plugin` could be removed entirely, and `workerd` would disappear with them.

## 6. Dependency tree (verbatim from `npm explain`, `dhansetu-hub-live`)

```
esbuild@0.28.0 dev
node_modules/esbuild
  esbuild@"~0.28.0" from tsx@4.22.1
  node_modules/tsx
    tsx@"^4.21.0" from drizzle-kit@0.31.10 (root devDependency)
    peerOptional tsx@"^4.8.1" from vite@8.0.13 (root devDependency)
  peerOptional esbuild@"^0.27.0 || ^0.28.0" from vite@8.0.13 (root devDependency)

workerd@1.20260515.1 dev peer
node_modules/workerd
  workerd@"1.20260515.1" from miniflare@4.20260515.0
  node_modules/miniflare
    miniflare@"4.20260515.0" from wrangler@4.92.0 (root devDependency)
    miniflare@"4.20260515.0" from @cloudflare/vite-plugin@1.37.1 (root devDependency)
  peerOptional workerd from @cloudflare/unenv-preset@2.16.1 ← wrangler
```

**Same tech-stack template, same exposure, confirmed present in 4 other local projects** (checked `package.json` directly, not assumed): `dhansetu-pdf-studio`, `dhansetu-peopledesk`, `partner-roadmap`, `public-landing` all declare the identical `vite` + `wrangler` + `drizzle-kit` + `@cloudflare/vite-plugin` devDependency set. Whatever fix is applied to one, apply to all — they'll all hit the same block.

## Recommended fix

Three real options, in order of how much they actually solve vs. how invasive they are:

1. **Clear the provenance/quarantine attribute on the specific binaries** (quick, but has to be redone after every `npm install` since a fresh download re-triggers it):
   ```bash
   cd "/Users/apple/Documents/ChatGPT/box AI/dhansetu-hub-live"
   xattr -dr com.apple.quarantine node_modules
   xattr -dr com.apple.provenance node_modules
   ```

2. **Ad-hoc sign the binaries locally** (more durable than clearing the attribute alone, since it gives them a real — if self-issued — signature `spctl` will accept):
   ```bash
   codesign --force --deep -s - "node_modules/@esbuild/darwin-x64/bin/esbuild"
   codesign --force --deep -s - "node_modules/@cloudflare/workerd-darwin-64/bin/workerd"
   ```
   Same caveat: a fresh `npm install` overwrites these with new unsigned copies, so this needs to be a `postinstall` script if you want it to survive reinstalls.

3. **Automate it with a `postinstall` script** (the durable fix — do this once per project, survives every future `npm install`):
   ```json
   // package.json
   "scripts": {
     "postinstall": "find node_modules -type f \\( -name esbuild -o -name workerd \\) -perm +111 -exec codesign --force -s - {} \\;"
   }
   ```

**Not recommended**: disabling Gatekeeper system-wide (`spctl --master-disable`) — that removes a real security control for every app on the Mac to fix a dev-tooling annoyance in a handful of projects. The targeted fixes above solve the actual problem without that trade-off.

**If `workerd` turns out to be unused** (i.e., these projects don't actually deploy to Cloudflare): removing `wrangler` and `@cloudflare/vite-plugin` from `devDependencies` and running `npm install` again eliminates it entirely — no signing workaround needed for that one. `esbuild` can't be removed the same way; it's load-bearing for `vite` and `drizzle-kit`, both of which are genuinely used.
