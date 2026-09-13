# TASK-0001 — FOUNDATION AUDIT & FREEZE

## Цель
Получить независимый аудит текущей SFERA перед следующим крупным merge.

Если модель физически не видит нужный файл — статус `NOT VERIFIED` / `BLOCKED_BY_INPUT`. Нельзя имитировать аудит.

## Проверить
1. Windows launcher / PySide6 UI
2. Interactive Board
3. PGN importer
4. Lichess/Chess.com Downloader
5. TWIC Manager
6. Position Genome
7. DB schema + migrations
8. Stockfish / LCZero bridges
9. Engine Lab 21 / Engine Jury
10. Batch Analyzer 1–8 engines
11. Research Tree persistence
12. Memory / Concepts / Conflicts
13. Curiosity / Discovery
14. Teacher Bridge
15. SFERA REPORT
16. Updater / rollback / data safety

## Обязательный вывод
`MODULE | STATUS | EVIDENCE | BUG | PRIORITY`

Статусы:
`WORKING / PARTIAL / BROKEN / PLACEHOLDER / NOT IMPLEMENTED / NOT VERIFIED`

## Главный вопрос
Какие 3 вещи сейчас сильнее всего мешают SFERA стать полезнее ChessBase/Aquarium в реальной работе?

## Freeze
До завершения аудита не объявлять новую версию.
