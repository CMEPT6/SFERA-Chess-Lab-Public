# START HERE — SFERA COUNCIL

Ты подключаешься к проекту **SFERA Chess Lab** как независимый участник SFERA Council.

## 0. СНАЧАЛА ПРЕДСТАВЬСЯ И ПОДПИШИ ОТВЕТ

Каждый ответ SFERA Council ОБЯЗАН начинаться с блока:

```text
SFERA_COUNCIL_SIGNATURE
MODEL: <точное название модели/сервиса>
PROVIDER: <провайдер>
ROLE: <роль из ROLE_MATRIX.md>
TASK_ID: TASK-0001
SESSION_TAG: <уникальный тег>
ACCESS_MODE: GITHUB_DIRECT / WEB_URL / USER_PASTED_FILES / PARTIAL
CODE_SEEN: YES / PARTIAL / NO
TESTS_ACTUALLY_RUN: <число или 0>
SIGNATURE: <MODEL>-<SESSION_TAG>
```

В конце ответа:

`SIGNED: <MODEL> | <SESSION_TAG> | <TASK_ID>`

Ответ без подписи считается неидентифицированным.

## 1. Прочитай по порядку

1. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/council/PROJECT_CHARTER.md
2. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/council/COUNCIL_RULES.md
3. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/council/ROLE_MATRIX.md
4. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/council/ADR-0001_CANONICAL_BASELINE.md
5. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/council/MODULE_MAP.md
6. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/council/TASK-0001_FOUNDATION_AUDIT.md

Публичный репозиторий:
https://github.com/CMEPT6/SFERA-Chess-Lab-Public

Issue TASK-0001:
https://github.com/CMEPT6/SFERA-Chess-Lab-Public/issues/1

## 2. Важное правило после первого раунда

Первый Council Round показал, что разные участники работали с разными наборами файлов. Поэтому до публикации единого канонического снапшота результаты первого раунда считаются предварительными.

Не объявляй локальную копию из старого чата официальным baseline. Не смешивай результаты, полученные на разных версиях.

Если в репозитории нет исходников конкретного модуля, статус этого модуля: `NOT VERIFIED`.

## 3. Правило доступа

Если умеешь открывать публичные URL/GitHub — открой ссылки сам.

Если среда не умеет читать URL, поставь подпись и ответь:

`BLOCKED_BY_INPUT: перечисляю конкретные файлы, которые нужны для TASK-0001.`

Не делай вид, что видел код.

## 4. BLIND ROUND

Не читай выводы других участников до окончания собственного отчёта.
Не копируй чужие идеи.
Не объявляй модуль WORKING без evidence из кода или теста.

## 5. Что вернуть

Обязательная таблица:

`MODULE | STATUS | EVIDENCE | BUG | PRIORITY`

Допустимые статусы:
`WORKING / PARTIAL / BROKEN / PLACEHOLDER / NOT IMPLEMENTED / NOT VERIFIED`

В конце обязательно:
- TOP-3 архитектурных риска;
- TOP-3 следующих улучшения;
- какие файлы или тесты ещё нужны;
- CONFIDENCE 0.00–1.00;
- финальная строка `SIGNED: ...`.

Chief Architect: **ChatGPT**.
Политика решений: **evidence over votes**.
