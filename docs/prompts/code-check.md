# Code Check Prompt

Paste this into Claude Code to audit the current working tree for errors.

---

```
Audit the current codebase for errors. Check ALL of the following:

**1. Python backend (backend/)**
- Import errors: run `python -c "import backend.main"` and fix any ModuleNotFoundError or ImportError
- Type mismatches: function signatures vs call sites (especially Pydantic model fields)
- Undefined names: variables used before assignment, missing imports
- SQLAlchemy: FK columns referencing tables that don't exist in models.py
- Alembic: run `alembic check` — confirm no unapplied migrations

**2. Tests**
- Run: `PYTHONPATH=. pytest tests/ -v --tb=short 2>&1 | tail -40`
- Report every FAILED or ERROR test with the exact error message
- Do NOT claim tests pass without running this command and showing output

**3. Config/env**
- Every `settings.X` reference in backend/ has a corresponding field in `backend/config.py`
- No hardcoded secrets (grep for api_key=, password=, secret= with literal string values)

**4. Frontend (frontend/src/)**
- Run: `cd frontend && npm run lint 2>&1 | head -50` — report all ESLint errors
- Undefined component imports: any JSX tag not imported in the same file
- Missing CSS variables: any `var(--X)` not defined in `frontend/src/styles/index.css`

**5. Consistency**
- Every API endpoint in backend/ has a matching call in `frontend/src/utils/api-client.js`
- Every Zustand store action called in a component is defined in the store file

Report format:
- File:line — severity (Critical/Warning/Minor) — problem — fix
- If no issues found in a section, write "✅ section: clean"
- Run every command listed above. Show the output. Do not skip any section.
```
