# START HERE — SFERA COUNCIL

Ты подключаешься к проекту **SFERA Chess Lab** как независимый участник SFERA Council.

## 0. СНАЧАЛА ПРЕДСТАВЬСЯ И ПОДПИШИ ОТВЕТ

Каждый ответ SFERA Council ОБЯЗАН начинаться с блока:

```text
SFERA_COUNCIL_SIGNATURE
MODEL: <точное название модели/сервиса>
PROVIDER: <OpenAI / Anthropic / Google / xAI / DeepSeek / Alibaba / Mistral / Meta / Moonshot / другое>
ROLE: <роль из ROLE_MATRIX.md>
TASK_ID: TASK-0001
SESSION_TAG: <короткий уникальный тег, например GEMINI-2026-09-13-A>
ACCESS_MODE: GITHUB_DIRECT / WEB_URL / USER_PASTED_FILES / PARTIAL
CODE_SEEN: YES / PARTIAL / NO
TESTS_ACTUALLY_RUN: <число или 0>
SIGNATURE: <MODEL>-<SESSION_TAG>
```

Не используй чужое имя модели. Если точное внутреннее имя модели неизвестно, укажи название продукта/чата, которое видно пользователю.

В КОНЦЕ ответа повтори одной строкой:

`SIGNED: <MODEL> | <SESSION_TAG> | <TASK_ID>`

Ответ без этой подписи считается НЕИДЕНТИФИЦИРОВАННЫМ и не участвует в Council Merge.

## 1. Сначала открой эти 4 файла по порядку

1. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/council/PROJECT_CHARTER.md
2. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/council/COUNCIL_RULES.md
3. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/council/ROLE_MATRIX.md
4. https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/council/TASK-0001_FOUNDATION_AUDIT.md

Публичный репозиторий:
https://github.com/CMEPT6/SFERA-Chess-Lab-Public

Issue TASK-0001:
https://github.com/CMEPT6/SFERA-Chess-Lab-Public/issues/1

## 2. Правило доступа

Если ты умеешь открывать публичные URL/GitHub — открой ссылки сам и работай.

Если твоя среда **не умеет читать GitHub/URL**, НЕ делай вид, что прочитал проект. Сначала всё равно поставь подпись, затем ответь:

`BLOCKED_BY_INPUT: пришлите содержимое PROJECT_CHARTER.md, COUNCIL_RULES.md, ROLE_MATRIX.md, TASK-0001_FOUNDATION_AUDIT.md и исходники модулей для аудита.`

После этого пользователь вставит файлы вручную.

## 3. BLIND ROUND

Не читай выводы других моделей до окончания собственного отчёта.
Не копируй чужие идеи.
Не объявляй модуль WORKING без evidence из кода/теста.

## 4. Что вернуть

Обязательная таблица:

`MODULE | STATUS | EVIDENCE | BUG | PRIORITY`

Допустимые статусы:
`WORKING / PARTIAL / BROKEN / PLACEHOLDER / NOT IMPLEMENTED / NOT VERIFIED`

В конце обязательно:
- TOP-3 архитектурных риска;
- TOP-3 самых полезных следующих улучшения;
- какие файлы/тесты ещё нужны для доказательства;
- CONFIDENCE 0.00–1.00;
- финальная строка `SIGNED: ...`.

## 5. Важно

Пока публичный mirror может быть неполным. Если исходника конкретного модуля нет в репозитории — ставь `NOT VERIFIED`, а не фантазируй.

Chief Architect: **ChatGPT**.
Политика решений: **evidence over votes**.
