# Recruiter Pitch Script — AI Excel Assistant

## 1) Business Problem
Many teams still depend on manual Excel workflows for operational reporting.  
That creates repeatable issues: duplicate rows, missing ownership fields, broken date formats, numeric text errors, and inconsistent status values. These issues reduce reporting trust and increase manual review time.

## 2) What This Product Does
AI Excel Assistant is a Streamlit chatbot for spreadsheet modernization:

1. Upload CSV/XLSX
2. Auto-profile data quality
3. Ask questions in natural language
4. Get a safe action plan
5. Confirm changes
6. Run Python tools
7. Download a management-ready workbook

## 3) Where Python / Pandas / OpenPyXL / API / AI Are Used
- **Python** orchestrates the workflow and tool execution.
- **pandas** handles profiling, cleaning, conversion, grouping, and validation.
- **openpyxl** generates styled output workbooks (headers, filters, freeze panes, highlights).
- **requests** integrates external API enrichment with fallback if API fails.
- **AI/LLM planner** maps user prompts to structured, validated tool calls (OpenAI/OpenRouter/Mock).

## 4) Why It Reduces Manual Work
- Replaces repetitive spreadsheet cleanup with guided automation.
- Converts informal user requests (chat prompts) into safe actions.
- Produces consistent outputs (summary, flagged issues, management report) in one run.
- Maintains operation history for auditability.

## 5) Why It Is Safe
- No `eval` / `exec`.
- LLM never executes arbitrary code.
- Only whitelisted tools can run.
- Tool arguments are schema-validated (Pydantic).
- Destructive actions require explicit user confirmation.

## 6) Why It Fits AI & Automation Specialist Role
- Demonstrates end-to-end automation mindset for Excel-heavy operations.
- Shows production-style modular architecture (profiler/planner/executor/exporter/UI).
- Combines AI workflow design with practical Python data engineering.
- Produces outputs that management can directly use for decision support.

## 7) 90-Second Demo Talk Track
1. Open app and show provider settings + file upload.
2. Upload messy spreadsheet and show automatic profile summary.
3. Ask: `Analyze what can be improved`.
4. Ask: `Color the Division column red` and `Split by Division`.
5. Show confirmation gate for risky actions.
6. Run plan and download workbook with cleaned data + management report.

