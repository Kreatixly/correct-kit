---
name: architect
description: Settle the interface before writing code that crosses a module boundary - callers' usage, types, invariants, error modes and where it lives - and design it so agents get it right from a single file. Use before adding or changing a service, provider, model, or any function other modules call; and whenever `correct` proposes an architecture or type-level fix.
---

# Architect

Code that crosses a module boundary is expensive to change later, and agents
copy whatever shape it has. Decide the shape on purpose, before the
implementation.

Read the project contract (`.claude/contract.md` when the repo runs Claude Code, `.github/agent-contract.md` when it runs GitHub Copilot — use whichever exists) first: it names the project's design vocabulary
(`## Vocabulary`), its rules, and its verify commands. Use that vocabulary
exactly.

## Process

1. **Start from the callers.** Find every existing and planned call site. Write
   the call as it should read at each one, before any signature exists. If the
   calls disagree, that disagreement is the design question.
2. **Name the interface.** Everything a caller must know: types, invariants,
   ordering, error modes, configuration, cost. Keep it small; hide the rest.
3. **Place the seam.** Which module owns this, and is there exactly one obvious
   place for it? Introduce a seam only when two adapters actually vary across it.
4. **Push invariants up the ladder.** For each invariant ask, in order: can the
   wrong state be made unrepresentable? Can the type system reject it? Can a
   check catch it? Only then: document it.
5. **Prototype when unsure.** If a question can be answered by writing the call
   site or a throwaway spike, do that instead of asking. Keep spikes on a local
   branch named per the contract.
6. **Write the design note** — short, in the contract's report language:
   call sites, interface, invariants and how each is enforced, where it lives,
   what was rejected and why.

## Designing for agents

An agent edits one file at a time and copies the nearest example. The repo is
agent-friendly when **a change that looks right from one file is right for the
whole repo**. Concretely:

- **Make illegal states unrepresentable.** If step B must only run on the
  output of step A, give A's output its own type that only A can construct.
  Skipping A then fails to compile instead of failing review.
- **One obvious place per concern.** Central registries for things that must
  stay consistent (prompts, config, routes, constants), found by name. Two
  plausible places means agents will use both.
- **The code you want copied is the code that exists.** Delete or migrate
  legacy patterns instead of leaving them as examples. An outdated pattern next
  to the new one is an instruction to repeat it.
- **No hidden coupling.** Avoid implicit ordering, stringly-typed keys shared
  across files, and side effects a caller cannot see from the signature.
- **Fail loudly, early, and helpfully.** Errors and check failures name the
  rule and the fix ("use X from Y"), so the agent corrects itself.
- **Fast, local feedback.** Checks an agent can run on one file in seconds get
  run; a 20-minute suite gets skipped.
- **Greppable names.** Avoid magic that hides call sites (reflection, dynamic
  dispatch by string, surprising codegen) unless the contract accepts it.
- **The interface is the test surface.** Tests call what callers call. If a test
  must reach past the interface, the module has the wrong shape.

## Done when

- every call site reads naturally against the interface
- each invariant has a named enforcement level, highest feasible
- the contract's verify commands are green for any code written
- the design note exists, and nothing beyond it was implemented without the
  approval the contract requires
