# AI Test Case Generator Agent

An AI-powered web application that reads a software requirement written in plain English and designs **structured, prioritised software test cases** for it: positive, negative and edge-case scenarios with test steps, test data and expected results. Sessions are stored in SQLite, test cases can be edited, added and deleted, and everything can be exported to CSV.

> M.Tech final-year project · Python · LangChain · Streamlit · SQLite · Ollama / Google Gemini

---

## 1. Problem statement

Manual test design is slow, inconsistent and depends heavily on the tester's experience. Requirements are often incomplete, so testers either miss scenarios or silently invent rules. Most "AI test generators" just produce generic, repetitive lists that ignore what the requirement actually says.

## 2. Objectives

1. Understand a natural-language requirement before writing any tests: its functionality, actors, inputs and the validation rules that are **explicitly** stated.
2. Identify missing or unclear information. Ask for clarification when the requirement is too vague, and label every assumption explicitly instead of inventing business rules.
3. Generate non-duplicated positive, negative and edge-case test cases with actionable steps, realistic test data, verifiable expected results and High/Medium/Low priority.
4. Validate every LLM response against a schema and repair or reject invalid output, so the application never crashes on a bad AI response.
5. Persist sessions, allow review and editing, and export to CSV.

## 3. Technology stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit 1.67, custom CSS design system, inline SVG icons, Plotly charts |
| AI agent | LangChain (`langchain-core` prompts and runnables) |
| LLM (primary) | Ollama, a locally running model (default `qwen2.5:7b`) |
| LLM (optional) | Google Gemini via `langchain-google-genai` (default `gemini-3.6-flash`) |
| Validation | Pydantic v2 schemas and custom normalisation |
| Database | SQLite (foreign keys, cascades, parameterised SQL) |
| Data / export | Pandas → CSV (UTF-8 with BOM, Excel friendly) |
| Testing | Pytest, Streamlit AppTest, LangChain `FakeListChatModel` |

## 4. System architecture

```
 ┌──────────────────────────── Streamlit UI (app.py + views/) ────────────────────────────┐
 │ Dashboard │ Generate │ Results (edit/add/delete) │ History │ Export │ System Status     │
 └──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                        │ (UI never calls the LLM or SQL directly)
                         test_case_generator.py  ── service layer
                          │                                   │
                agent.py (LangChain agent)               database.py (SQLite)
   ┌───────────────────────────────────────────┐      sessions ─1:1─ session_metadata
   │ 1 validate input      (validators.py)     │          └──1:N── test_cases
   │ 2 check provider      (Ollama / Gemini)   │
   │ 3 ANALYSE requirement (prompts.py)        │      export_utils.py (Pandas → CSV)
   │ 4 clarification gate                      │
   │ 5 GENERATE test cases (prompts.py)        │
   │ 6 VALIDATE JSON + self-repair             │
   │ 7 filter scenario types + de-duplicate    │
   └───────────────────────────────────────────┘
```

### Agent workflow

1. **Input validation**: empty, too short, unreadable or too-long requirements are rejected before any LLM call.
2. **Provider readiness**: for Ollama, the agent checks that the server is running and the model is pulled. For Gemini, it checks that a key is configured.
3. **Requirement analysis (LLM call 1)**: returns a title, summary, main functionality, actors, inputs, *stated* validation rules, missing information, assumptions, applicable scenarios and a clarity rating (`clear` / `partially_clear` / `unclear`).
4. **Clarification gate**: if the requirement is `unclear`, the agent stops and shows clarification questions. The user can refine the requirement, or explicitly choose to continue with labelled assumptions.
5. **Test design (LLM call 2)**: grounded in the analysis, targets a case count proportional to the selected scenario types, and puts any rule not in the requirement into an `assumption` field.
6. **Structured validation**: JSON is extracted (code fences and stray prose are tolerated) and validated with Pydantic. Field aliases and label synonyms are normalised (e.g. `critical` → `High`, `boundary` → `Edge Case`). Invalid items are dropped with warnings. If the whole response is invalid, the agent sends the validation error back to the LLM once (**self-repair**) before failing gracefully.
7. **Post-processing**: removes scenario types the user did not select, removes duplicates using exact and fuzzy similarity, warns about uncovered scenario types and sorts the results.

### Error handling

Every provider exception is mapped to a typed error with a "how to fix" hint, so the UI shows a clear message and never a stack trace:

| Situation | Error shown |
|---|---|
| Ollama not running | *LLM provider not reachable* + install/start instructions |
| Ollama model missing | *Model not available* + `ollama pull <model>` |
| Gemini key missing / invalid | *Configuration problem* / *Authentication failed* |
| Gemini model unavailable | *Model not available* |
| Timeout | *LLM request timed out* |
| 429 / 503 overload | *Provider busy or quota exceeded* |
| Invalid JSON / missing fields | *Invalid AI response* (after one self-repair attempt) |
| Empty / too short requirement | *Requirement needs attention* |
| Duplicates | removed automatically and reported |

The application **never silently switches providers**. Switching is an explicit choice on the System Status page.

## 5. Folder structure

```
.
├── app.py                  Streamlit entry point: navigation, sidebar, theming
├── agent.py                LangChain agent, provider factory, readiness checks, error mapping
├── prompts.py              Analysis, generation and self-repair prompt templates
├── validators.py           Input validation, JSON extraction, Pydantic schemas, de-duplication
├── test_case_generator.py  Service layer: agent ↔ database, validated CRUD
├── database.py             SQLite schema and CRUD (parameterised SQL)
├── export_utils.py         Pandas DataFrame building, filtering, CSV export
├── errors.py               Typed application errors
├── config.py               Settings loaded from .env
├── setup_check.py          Pre-flight check used by the launch scripts
├── components/             Design system (CSS), UI primitives, charts, dialogs, test case workspace
├── views/                  Pages: dashboard, generate, results, history, export, status
├── assets/                 Logo and icon
├── tests/                  Pytest suite (unit, service, database, export, UI, opt-in live LLM)
├── data/                   SQLite database (created automatically, git-ignored)
├── .streamlit/config.toml  Theme and server settings
├── requirements.txt  .env.example  .gitignore  pytest.ini
└── run.bat / run.sh        One-click launchers
```

## 6. Installation and running

### Windows (recommended)

1. Open the project folder in VS Code.
2. Configure `.env` (copied from `.env.example` on first run). Use **Gemini**: `LLM_PROVIDER=gemini` and `GEMINI_API_KEY=...`, or **Ollama** (see below).
3. Double-click **`run.bat`** (or run `.\run.bat` in the VS Code terminal).

The script finds Python 3.10–3.13, creates `.venv`, installs dependencies (again only when `requirements.txt` changes), creates `.env` if missing, initialises the database, checks the LLM provider and opens http://localhost:8501.

### Linux / macOS

```bash
chmod +x run.sh && ./run.sh
```

### Manual

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## 7. LLM configuration

All settings live in `.env`, which is never committed; see `.env.example`.

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama` or `gemini` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Any instruction-following model you have pulled |
| `GEMINI_API_KEY` | – | Key from https://aistudio.google.com/apikey |
| `GEMINI_MODEL` | `gemini-3.6-flash` | Gemini model name |
| `LLM_TEMPERATURE` | `0.2` | Low temperature for consistent, grounded output |
| `LLM_TIMEOUT_SECONDS` | `120` | Per-request timeout |
| `MAX_TEST_CASES` | `20` | Upper bound on the requested number of cases |
| `MAX_REPAIR_ATTEMPTS` | `1` | Self-repair retries for invalid JSON |
| `DATABASE_PATH` | `data/test_cases.db` | SQLite file |

**Using Ollama (local, free, offline).** Ollama is a separate install:

1. Install it from https://ollama.com/download. It runs in the background after installation.
2. Pull the model: `ollama pull qwen2.5:7b` (about 4.7 GB; 8 GB+ RAM recommended). Smaller alternative: `ollama pull llama3.2:3b`, then set `OLLAMA_MODEL=llama3.2:3b`.
3. Set `LLM_PROVIDER=ollama` and restart. Use **System Status → Test connection** to verify.

API keys are only read server-side from `.env`. They are never sent to the browser; the UI shows only a masked hint.

## 8. Database design

| Table | Key columns | Notes |
|---|---|---|
| `sessions` | `id`, `title`, `requirement`, `scenario_types`, `created_at`, `updated_at` | One row per analysed requirement |
| `session_metadata` | `session_id` (PK, FK), `provider`, `model`, `analysis_json`, `warnings_json`, `generation_seconds`, `raw_case_count`, `duplicates_removed`, `repair_attempts` | 1:1 with sessions, holds the AI analysis and quality metrics |
| `test_cases` | `id`, `session_id` (FK), `case_code` (TC-001…), `scenario`, `scenario_type`, `steps`, `test_data`, `expected_result`, `priority`, `assumption`, `source` (ai/manual), `position` | N:1 with sessions. `CHECK` constraints on priority and type, `UNIQUE(session_id, case_code)` |

- `PRAGMA foreign_keys = ON` with `ON DELETE CASCADE`: deleting a session removes its metadata and test cases in one transaction.
- Every statement is parameterised (`?` placeholders), so search input such as `' OR 1=1 --` is treated as plain text.
- WAL journal mode, and the schema is created automatically on startup. Data persists across restarts.

## 9. Features

- **Dashboard**: live KPIs with animated counters (requirements analysed, test cases, High/Medium/Low), scenario coverage and priority distribution charts, daily activity, recent sessions, and quick actions. Every number comes from SQLite; nothing is hard-coded.
- **Generate**: requirement workspace with five example requirements, a clear button, scenario-type selection, a live agent progress panel (animated loader, progress bar, step log) and a clarification workflow.
- **Results**: the requirement and its AI analysis (summary, rules, gaps, assumptions); search and priority/type filters; card view and selectable table view; edit, add and delete through modal dialogs with confirmation; export of filtered or selected rows.
- **History**: searchable, sortable, paginated list of saved sessions with open, CSV download and delete-with-confirmation.
- **Export**: single session or all sessions, priority/type/keyword filters, a preview, and a CSV download. Empty datasets are handled gracefully.
- **System Status**: provider switch, a live connection test that makes a real round-trip to the model, database health and Ollama setup guide.
- **UX**: navy/blue enterprise design system, toast notifications, modal transitions, hover states, card entrance animations, responsive layout, and support for `prefers-reduced-motion`.

## 10. Testing

```bash
.venv\Scripts\python -m pytest                 # 92 offline tests (mocked LLM)
$env:RUN_LIVE_LLM=1; .venv\Scripts\python -m pytest tests/test_live_llm.py   # real LLM (PowerShell)
RUN_LIVE_LLM=1 .venv/bin/python -m pytest tests/test_live_llm.py            # real LLM (bash)
```

| Required scenario | Covered by |
|---|---|
| Empty requirement | `test_validators.py::test_empty_requirement_rejected`, `test_app_pages.py::test_generate_page_empty_requirement_shows_error`, `test_agent.py::test_empty_requirement_never_calls_llm` |
| Valid registration requirement | `test_agent.py::test_registration_requirement_generates_structured_cases`, `test_live_llm.py` |
| Login requirement | `test_agent.py::test_login_requirement` |
| Negative / edge-case scenarios | `test_agent.py::test_unselected_scenario_types_are_filtered[...]`, `test_missing_selected_type_is_reported` |
| Unclear requirement | `test_agent.py::test_unclear_requirement_asks_for_clarification`, `..._can_proceed_with_assumptions`, `test_live_llm.py` |
| Invalid LLM response | `test_agent.py::test_invalid_json_is_repaired`, `..._after_repair_raises`, `test_missing_fields_in_all_cases_raises`, `test_validators.py` |
| Editing test cases | `test_database.py::test_update_test_case`, `test_export_and_service.py::test_edit_add_delete_through_service` |
| Deleting test cases | `test_database.py::test_delete_test_case`, `test_delete_session_cascades` |
| Saving and retrieving history | `test_export_and_service.py::test_generation_is_saved_to_history` |
| CSV export | `test_export_and_service.py::test_csv_*`, `test_filtered_export` |
| Database operations | `test_database.py` (schema, CRUD, constraints, injection safety, statistics) |
| Restart and persistence | `test_database.py::test_data_persists_after_restart`, `test_export_and_service.py::test_history_survives_restart` |
| Provider errors | `test_agent.py::test_ollama_not_running`, `test_ollama_model_not_installed`, `test_gemini_without_key`, `test_exception_classification[...]` |
| UI pages | `test_app_pages.py` (all pages render; example and clear buttons) |

Mock LLM responses are used **only** in automated tests (LangChain `FakeListChatModel`). The application always calls the real configured provider.

## 11. Limitations and future work

- Output quality depends on the model. Small local models (3B) produce fewer and simpler cases than larger ones.
- Generation needs two LLM calls, typically 20–40 s with Gemini Flash; local speed depends on your hardware.
- The tests are manual/functional test cases; automation script generation (Selenium/Playwright) is future work.
- Single-user, local SQLite. A multi-user deployment would need authentication and a server database.
- Possible extensions: requirement document upload (PDF/DOCX), traceability matrix, Jira/TestRail push, and re-generating a single test case.
