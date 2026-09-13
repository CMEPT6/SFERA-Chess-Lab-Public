# SFERA COUNCIL RESPONSE TEMPLATE

Каждый ответ должен начинаться с этого блока:

```text
SFERA_COUNCIL_SIGNATURE
MODEL: <название модели или сервиса>
PROVIDER: <компания или платформа>
ROLE: <роль из ROLE_MATRIX.md>
TASK_ID: TASK-0001
SESSION_TAG: <уникальный тег, например GEMINI-2026-09-13-A>
ACCESS_MODE: GITHUB_DIRECT / WEB_URL / USER_PASTED_FILES / PARTIAL
CODE_SEEN: YES / PARTIAL / NO
TESTS_ACTUALLY_RUN: <число или 0>
SIGNATURE: <MODEL>-<SESSION_TAG>
```

Далее структура ответа:

## FINDINGS

## SOLUTION

## PATCH / FILES

## TESTS

## BENCHMARK

## RISKS

## WHAT_I_REJECTED

## CONFIDENCE
0.00–1.00

В самом конце обязательно:

`SIGNED: <MODEL> | <SESSION_TAG> | <TASK_ID>`

Ответ без подписи считается неидентифицированным и не участвует в Council Merge.
