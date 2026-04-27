# Tooling Audit

## 1. Repository Instruction Audit

Files checked before implementation:

- `AGENTS.md` (project constraints and safety)
- `README.md`
- `pyproject.toml`
- `requirements.txt`
- `docs/`

Result:

- Existing UI modules are in `app/ui/`.
- Existing agent/planner/executor modules are preserved and reused.
- No project-local MCP/plugin config folder was found inside this repo.

## 2. MCP Servers Detected

Command used:

```bash
codex mcp list
```

Detected:

- `playwright` via `npx @playwright/mcp@latest` (status: `enabled`)

## 3. MCP/Tools Actually Used

Used in this audit cycle:

- MCP management CLI:
  - `codex mcp list`
  - `codex mcp get playwright`
- Codex runtime MCP inspection tools:
  - `list_mcp_resources`
  - `list_mcp_resource_templates`

Result:

- No runtime MCP resources/templates were exposed in this execution context.
- Because runtime access to the Playwright MCP server was not available here, browser-level visual automation could not be executed directly from the MCP runtime tool calls.

## 4. Skills Available in Environment

General Codex skills are available (e.g. OpenAI docs, plugin/skill creator, image generation), but no dedicated spreadsheet UI automation skill was required for this task.

## 5. Fallback Strategy Applied

Since Playwright MCP runtime inspection was unavailable in this context, validation used:

- direct code audit (`app/ui/*.py`)
- Streamlit app structural checks
- functional state verification via tests/smoke commands

This kept sidebar/upload/provider functionality intact while polishing visual styling.

## 6. Recommended Playwright MCP Setup Command

If Playwright MCP is missing on another machine/session, run:

```bash
codex mcp add playwright npx \"@playwright/mcp@latest\"
```

Alternative config in `~/.codex/config.toml`:

```toml
[mcp_servers.playwright]
command = "npx"
args = ["@playwright/mcp@latest"]
```
