# START HERE — SFERA COUNCIL

Ты подключаешься к проекту **SFERA Chess Lab** как независимый участник SFERA Council.

## 0. СНАЧАЛА ПРЕДСТАВЬСЯ И ПОДПИШИ ОТВЕТ

Каждый ответ SFERA Council ОБЯЗАН начинаться с блока:

```text
SFERA_COUNCIL_SIGNATURE
MODEL: <точное название модели/сервиса>
PROVIDER: <провайдер>
ROLE: <роль из ROLE_MATRIX.md>
TASK_ID: <текущая задача>
SESSION_TAG: <уникальный тег>
ACCESS_MODE: GITHUB_DIRECT / WEB_URL / USER_PASTED_FILES / PARTIAL
CODE_SEEN: YES / PARTIAL / NO
TESTS_ACTUALLY_RUN: <число или 0>
SIGNATURE: <MODEL>-<SESSION_TAG>
```

В конце ответа:

`SIGNED: <MODEL> | <SESSION_TAG> | <TASK_ID>`

## 1. ПРОЧИТАЙ ПО ПОРЯДКУ

1. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/council/PROJECT_CHARTER.md
2. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/council/COUNCIL_RULES.md
3. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/council/ROLE_MATRIX.md
4. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/council/ADR-0001_CANONICAL_BASELINE.md
5. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/council/MODULE_MAP.md
6. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/audit_snapshot/v1.5.0/BASELINE_MANIFEST.md
7. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/audit_snapshot/v1.5.0/04_TESTS_META.md
8. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/audit_snapshot/v1.5.0/source/sfera/identity.py.md
9. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/audit_snapshot/v1.5.0/source/sfera/pgnstream.py.md
10. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/audit_snapshot/v1.5.0/source/sfera/genome.py.md
11. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/audit_snapshot/v1.5.0/source/sfera/db.py.part01.md
12. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/audit_snapshot/v1.5.0/source/sfera/db.py.part02.md
13. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/audit_snapshot/v1.5.0/source/sfera/db.py.part03.md
14. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/audit_snapshot/v1.5.0/source/sfera/engine.py.md
15. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/audit_snapshot/v1.5.0/source/sfera/engine_lab21.py.md
16. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/audit_snapshot/v1.5.0/source/sfera/discovery.py.md
17. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/audit_snapshot/v1.5.0/source/sfera/report.py.part01.md
18. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/audit_snapshot/v1.5.0/source/sfera/report.py.part02.md
19. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/council/TASK-0001_FOUNDATION_AUDIT.md

## 2. КАНОНИЧЕСКИЙ BASELINE

Для Council сейчас канонический артефакт:

`SFERA_Chess_Lab_v1.5_SFERA_REPORT.zip`

SHA-256:

`b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892`

Chief Architect прогнал именно этот архив:

`python -m pytest -q` → `18 passed in 1.59s`.

Если твой старый локальный ZIP, ветка или созданная тобой версия имеет другой hash/другой тестовый набор — это ДРУГОЙ baseline.

## 3. ЧТО СЕЙЧАС УЖЕ МОЖНО АУДИРОВАТЬ ПО ПУБЛИЧНОМУ КОДУ

Опубликован канонический evidence-pack для:

- DB schema + migrations;
- PGN streaming/import;
- Position Genome + position identity;
- Stockfish/Lc0 generic UCI bridge;
- Research Tree;
- Engine Lab 21 / Jury;
- Discovery;
- SFERA Report;
- базовых tests/meta.

Остальные модули, которых ещё нет в `audit_snapshot`, помечай `NOT VERIFIED`, а не переноси выводы со старой локальной копии.

## 4. ВАЖНЫЙ КОНФЛИКТ ПЕРВОГО РАУНДА

Некоторые ранние ответы описывали другой локальный v1.5. Например, в одном отчёте было 22 теста и утверждение, что SFERA Report отсутствует. В каноническом архиве выше тестов 18, а `sfera/report.py` и `tests/test_report_v15.py` реально существуют.

Поэтому сначала проверяй canonical source, затем делай вывод.

## 5. ПРАВИЛО ДОСТУПА

Если умеешь открывать публичные URL/GitHub — открой ссылки сам.

Если среда не умеет читать URL, поставь подпись и ответь `BLOCKED_BY_INPUT`, перечислив конкретные файлы.

## 6. BLIND ROUND

Не читай ответы других участников до окончания собственного отчёта.
Не объявляй модуль WORKING без evidence из canonical source/test.

Chief Architect: **ChatGPT**

Политика решений: **EVIDENCE OVER VOTES**
