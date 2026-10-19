# SHAKTHI_OS v5.1 — Work Loop

Date: 2026-09-13

## The 9-step loop

Every work session, and every discrete slice of work within a session,
follows this loop — not a giant rewrite, not a giant planning session, and
never a "done" claim without step 5's real verification:

1. **Read current goal.** The founder's actual words for this task, not an
   assumed or generalized version of it.
2. **Inspect repo/state.** Read the real files before deciding anything —
   don't reason from memory of what a file "probably" contains. (Real
   example from today: before touching dhansetuhub.in's pricing, this
   session read the actual live `origin/main` source via `git show`,
   discovering the local checkout was 22 commits behind — a fact that
   changed the whole approach.)
3. **Choose the highest-value real blocker.** Not the easiest one, not the
   most interesting one — the one that most unblocks the stated goal.
4. **Fix one small slice.** A bounded, reviewable change, not a sweeping
   rewrite.
5. **Run build/test.** Real commands, real output. If something can't be
   run (e.g. no browser tool available), say so explicitly rather than
   skip the check silently.
6. **Record evidence.** What was actually observed — a test pass/fail, a
   `curl` result, a grep with zero/nonzero matches — not a paraphrase of
   intent.
7. **Update memory/log.** The relevant doc (watchdog status, fix log,
   failure memory) gets the real result, appended, never silently
   overwritten in a way that erases prior history.
8. **Choose the next blocker.** Re-run step 3 against the updated state.
9. **Continue** — don't stop to ask "what next?" if the next blocker is
   inferable; don't stop at a plan when implementation was safe and
   possible.

## Anti-patterns this loop exists to prevent

- **Giant rewrite**: touching far more surface area than the current
  blocker requires "while I'm in there." (Contrast: today's Resume AI
  security fix touched exactly the prompt-generation path, not the whole
  page.)
- **Giant planning session**: producing a long plan document instead of
  the smallest safe real implementation step. The founder's own v5.1 spec
  says this explicitly: "do not stop at docs if a safe implementation
  improvement is available" — this session's response to that was to
  build the Command Center v5.1 panel in the same pass as these docs, not
  a follow-up.
- **Fake "done"**: reporting success without having actually run the
  verification. Real precedent from today: the ChatGPT Sites builder
  agent that shipped the pricing change did NOT claim the Resume AI
  security-fix publish succeeded when it hit a real `403` — it reported
  the exact error and left production genuinely unchanged, which is
  exactly the standard this loop requires.

## Where this loop is already running

Every Task 1 change today followed this shape in practice (inspect →
find blocker → implement → build/test → log → next), even before this
document existed. This doc formalizes what was already the working
pattern — it does not introduce a new process the session has to adopt
from scratch.
