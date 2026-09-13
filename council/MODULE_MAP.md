# SFERA Council Module Map

This file defines the expected module areas for the canonical audit snapshot.

| Area | Expected evidence |
|---|---|
| Launcher | Windows launcher and Python entry point |
| UI | PySide6 main window and dashboard |
| Board | Board widget and chess rules |
| PGN | streaming parser and importer |
| Database | schema, migrations, storage |
| Genome | position identity and transitions |
| Engines | UCI bridge, Stockfish/Lc0 integration |
| Engine Lab | registry, jury, WDL comparison |
| Batch Analyzer | scheduler and PGN annotation |
| Downloads | Lichess, Chess.com, TWIC |
| Research | Research Tree persistence |
| Memory | concepts, evidence, conflicts, journal |
| Discovery | curiosity, hypotheses, validation |
| Teacher | request and pack import/export |
| Report | SFERA Report analytics |
| Updater | backup, update, rollback, data safety |
| Tests | automated tests and benchmark runners |

When the canonical snapshot is published, replace expected evidence with exact file paths. Until then, do not infer filenames that are not present.
