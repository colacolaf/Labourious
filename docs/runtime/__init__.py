"""runtime — the Labourious runtime layer (CLI + flows + adapters + thesis register).

Submodules:
    runtime     — the CLI + execute_flow_* + run_flow_stream
    adapters    — model provider adapters (Anthropic, Ollama, Groq, OpenAI-compat)
    tools       — connector adapters (SEC EDGAR, news, market_data, web_fetch)
    thesis_register — SQLite thesis memory
    evals       — the pytest eval suite (behavior-based, replaces the v2 validator)
    events      — typed Event dataclasses (the TUI contract)
"""
