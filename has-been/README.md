# has-been/ — Archive of dead files

Files moved here on 2026-08-13 because they no longer do any work in the
Network Fantasy War project. They are preserved (not deleted) and can be
restored with `git mv` if ever needed.

## What was moved

| File | Reason |
|---|---|
| `prototype/demo.py` | Auto-demo script (two bots play a few turns). Not imported by anything. References the old "mini-set" prototype design. |
| `prototype/simulate.py` | Smart-AI simulation ("full 80-card set"). Only imported by `deep_analysis.py` and `tournament.py` (both also moved). Card count predates the current 370-card pool. |
| `prototype/deep_analysis.py` | Deck tournament analysis (head-to-head matrix). Not imported. |
| `prototype/composition_analysis.py` | Deck composition analysis (layer/stat breakdowns). Not imported. |
| `prototype/tournament.py` | Round-robin deck tournament runner. Not imported. |
| `CHANGELOG.md` | Stale project changelog (ends at v5.5 / 2026-07-25; project is now v6.8+). Passive history, no code references it. |

## What was deleted (regenerable)

- `__pycache__/`, `.pytest_cache/` and nested `__pycache__/` dirs — Python
  bytecode/test caches, regenerated automatically on next run. Not source.

## What was kept and why (the "does work" set)

- `prototype/` engine: `__init__.py, ability_executor.py, ability_registry.py,
  ai.py (BotPlayer — imported by both webui apps), board.py, card.py, cli.py
  (working hotseat CLI entry point), combat.py, decks.py, enums.py, game.py,
  modifier.py, modifier_engine.py, network.py, serialize.py, turn_manager.py`.
- `webui/` — `app.py` (single-player), `multiplayer/app.py` (Railway main),
  templates (`game.html`, `lobby.html`, `mp-game.html`), `static/NFW-Reglas-Jugador.pdf`.
- Generators — `generate_rules_pdf.py` (→ rules-reference-comprehensive.pdf),
  `generate_player_pdf.py` (→ NFW-Reglas-Jugador.pdf), `generate_pdfs.py`
  (→ ui-guide.pdf + deck-guide.pdf).
- Canonical docs — `rules-reference.md`, `rules-reference-player.md`,
  `CONTEXT.md` (domain glossary), `AGENTS.md` + `docs/` (agent methodology:
  ADRs, issue tracker, triage labels).
- Deploy/config — `railway.json`, `requirements.txt`, `.gitignore`, `README.md`.
- Generated PDFs — `rules-reference-comprehensive.pdf`, `NFW-Reglas-Jugador.pdf`,
  `ui-guide.pdf`, `deck-guide.pdf`.
- `tests/test_abilities.py`.
- `human-testing/` — recent playtest report (kept; not code).

## Notes

- `prototype/cli.py` is a functional hotseat CLI but superseded by the web UI.
  Kept because it still runs against the current engine; archive it too if the
  web UI is the only supported interface.
