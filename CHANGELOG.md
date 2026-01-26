# Changelog

## [0.1.3] - 2026-01-26
- Initial project scaffolding with core, analysis, planning, devops, and orchestration modules.
- Added example usage script and baseline tests.
- Documented setup steps in README.
- Introduced TODO list for upcoming work.

## [0.1.4] - 2026-01-26

## [0.1.5] - 2026-01-26

## [0.1.6] - 2026-01-26

## [0.1.7] - 2026-01-26

## [0.1.8] - 2026-01-26

## [0.1.9] - 2026-01-26

## [0.1.10] - 2026-01-26

## [0.1.11] - 2026-01-26

## [0.1.12] - 2026-01-26

## [0.1.13] - 2026-01-26

## [0.1.14] - 2026-01-26

## [0.1.15] - 2026-01-26

- Added `extensions.test_command` to support running tests in non-Python repositories (e.g. `npm test`, `make test`).
- Planner can auto-append a `run_command` test step when `extensions.test_command` is configured and the plan has no tests.
- Orchestrator persists stdout/stderr for plan-level test command steps as `plan_test_command_*` run artifacts.
- CLI `work logs` can display `plan_test_command_*` artifacts.
- Hardened executor allowlist: only allow exact configured `extensions.test_command` (in addition to safe prefixes).

## [Unreleased]
