# Labourious

**A local-first AI portfolio manager designed as a research firm in a building.**

Labourious is designed around one calm Portfolio Manager that coordinates specialized agents across research, macro, quant, fundamental, technical, sentiment, risk, strategy, execution, memory, critique, compliance, alternative-data, crypto, control, and task-automation rooms. The intended experience is simple: ask the Portfolio Manager a question, let it delegate the relevant work, and receive one synthesized answer shaped by your rules and mandates.

> **Current status:** the repository is in active design and frontend-prototype development. The multi-agent architecture, agent prompts, room taxonomy, and visual HQ are documented, but the backend orchestration, desktop shell, memory system, and broker integrations described in the design documents are not implemented yet.

## What is implemented

The runnable work currently lives in [`frontend/ground/`](frontend/ground/):

- A browser-based Phaser 3 Ground Floor lobby using a deskrpg-faithful pixel-art pipeline.
- Agent roster pages for the building's rooms, plus a combined [`Agent Gallery`](frontend/ground/agent-gallery.html).
- A Penthouse roster for the Portfolio Manager and PM Bodyguard.
- Procedural and generated assets under [`frontend/ground/assets/`](frontend/ground/assets/), with room and building layout documentation under [`docs/frontend/`](docs/frontend/).

The current agent manifest contains **94 entries**, including example characters and the room roster. The documented HQ model organizes the operation across five levels: Ground / Intake, Floor 2 / Analysis, Floor 3 / Judgment, Floor 4 / Command, and the Penthouse / The Top.

## Run the frontend prototype

```bash
cd frontend/ground
python3 -m http.server 8080
```

Then open <http://localhost:8080/>. Use an HTTP server rather than opening the HTML files directly because the prototype uses ES modules and local assets.

## Repository map

| Path | Purpose |
|---|---|
| [`frontend/ground/`](frontend/ground/) | Runnable pixel-art lobby, room pages, roster gallery, and asset generators |
| [`docs/README.md`](docs/README.md) | Product overview, room taxonomy, and documentation index |
| [`docs/LABOURIOUS_ARCHITECTURE.md`](docs/LABOURIOUS_ARCHITECTURE.md) | Planned Portfolio Manager and subagent architecture |
| [`docs/AGENTS.md`](docs/AGENTS.md) | Agent hierarchy, room responsibilities, and calling flow |
| [`docs/FEATURES.md`](docs/FEATURES.md) | Planned product capabilities |
| [`docs/LABOURIOUS_SETUP.md`](docs/LABOURIOUS_SETUP.md) | Aspirational local-first setup guide |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Planned local-first security model |
| [`docs/frontend/README.md`](docs/frontend/README.md) | Frontend floors, rooms, and agent profile index |

## Design principles

- **Local-first:** the planned product keeps keys, data, and memory on the user's machine; cloud models are opt-in through the user's own credentials.
- **Delegation over one-shot answers:** the Portfolio Manager routes work to domain specialists rather than relying on one generic response.
- **Multiple perspectives:** research, modeling, risk, and critique agents intentionally overlap so recommendations can be challenged.
- **Inspectable world:** the HQ makes the agent system tangible through rooms, rosters, layouts, and visual identities.

## License

Labourious is intended to be released under the MIT License; the repository does not currently include a `LICENSE` file.
