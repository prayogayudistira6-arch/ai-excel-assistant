# Repository Guidance

- Run `pytest -q` after changing source files.
- Do not use `eval()` or `exec()` for model output.
- Keep planner output and executor actions separate.
- Prefer small, testable changes.
- Keep mock runtime working without API keys.
