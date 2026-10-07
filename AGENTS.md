# Market Analyzer Agent Instructions

This repository uses the Ponytail development philosophy from DietrichGebert/ponytail, adapted for this project's financial-ML requirements.

Source: https://github.com/DietrichGebert/ponytail
Source files consulted: AGENTS.md and skills/ponytail/SKILL.md on 2026-10-07.
License: MIT.

## Mode

Ponytail is active for coding work in this repository by default at the full intensity level.

The goal is efficient engineering, not careless under-building. The project remains governed by its existing research, leakage, security, and correctness requirements. An explicit user request overrides Ponytail's preference for a smaller implementation.

## Before writing code

Read the task and the code it touches. Trace the real flow end to end before editing.

Then stop at the first applicable rung:

1. Does this need to exist at all? Avoid speculative work (YAGNI).
2. Does the codebase already have the helper, utility, type, or pattern? Reuse it.
3. Can the Python standard library solve it?
4. Can an existing platform feature solve it?
5. Can an already-installed dependency solve it?
6. Can the correct solution be expressed more simply?
7. Only then write the minimum correct code.

Do not add abstractions, factories, interfaces, configuration, scaffolding, or dependencies unless the problem actually requires them.

## Bug fixes

Fix root causes, not individual symptoms. Before changing a shared function, inspect all of its callers. Prefer one shared correction over repeated caller-specific patches.

The smallest change in the wrong location is not a good fix.

## Change discipline

Prefer deletion over addition, boring implementations over clever ones, and the fewest files that solve the problem.

Do not add code for hypothetical future requirements.

When deliberately accepting a known technical ceiling, record it with a `ponytail:` comment naming the ceiling and the upgrade trigger. Example: `# ponytail: O(n^2) scan; replace if profiling shows this path is material.`

Complex requests should first receive the smallest correct version that satisfies the explicit requirement. Do not stall waiting for clarification when a safe default is available.

## Non-negotiable exceptions for Market Analyzer

Ponytail must never be used to justify removing or weakening:

- temporal/leakage controls
- point-in-time universe membership
- causal availability timestamps
- OOS or nested-OOS evaluation boundaries
- validation required to protect financial data integrity
- error handling that can prevent data loss or corrupt research outputs
- authentication, credential handling, or other security controls
- auditability and reproducibility required for investor/bank use
- tests required to detect research-regression or leakage bugs
- any feature or behavior explicitly requested by the user

A minimal implementation is acceptable only when it remains methodologically correct.

## Research-specific correctness

Never optimize for a smaller diff at the expense of methodological validity.

Historical features, context, fundamentals, news, universe membership, model fitting, calibration, portfolio construction, and backtests must remain causal and chronologically valid.

Do not reuse survivor-based/static context where the task requires point-in-time context.

Do not retrain or retune merely because a metric is disappointing. First establish the correct evaluation path, compare against transparent baselines, and preserve the evaluation definition.

## Testing

Non-trivial logic must leave one runnable check behind. For this repository, the existing pytest regression suite is preferred because it already covers financial/research invariants. Do not create redundant test frameworks or large fixture systems merely to satisfy the Ponytail principle.

At minimum after material changes, run the smallest directly relevant tests first, then the broader regression suite when appropriate.

## Output discipline for coding-agent sessions

Prefer code/diff first. Keep explanations short unless the user explicitly requests a walkthrough, research report, audit, or handover update.

For code changes, state what was intentionally skipped and the condition that would justify adding it when useful.

## Useful operating rule

The shortest path to a correct, validated result is the right path.

Do not confuse "less code" with "less engineering." In this repository, careful research methodology, testing, and auditability are part of the minimum correct solution.
