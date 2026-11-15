# CMEPT6 Engine 1.1 — нативная сборка Windows x64

## Вариант A: Windows 10/11, одна команда

1. Установите **Visual Studio 2022 или 2026 Build Tools** (компонент *Desktop development with C++*, MSVC x64).
2. Распакуйте релиз в каталог без пробелов в имени по возможности, например `C:\CMEPT6`.
3. Запустите **x64 Native Tools Command Prompt** (не обычный CMD).
4. Выполните:

```bat
cd /d C:\CMEPT6
build_windows.bat
```

Будет создан `CMEPT6-Engine.exe` (консольный UCI-движок, без шахматной доски). Команда `CMEPT6-Engine.exe` в терминале и ввод `uci` должны напечатать `id name CMEPT6 Engine 1.1` и `uciok`.

Проверки при установленном Python 3:

```bat
python tests\run_tests.py CMEPT6-Engine.exe
python tests\test_regression.py CMEPT6-Engine.exe
python tests\test_release.py CMEPT6-Engine.exe
python tests\test_referee.py
```

Альтернатива — MinGW-w64 (g++ в PATH). Установленный C++-компилятор необходим: ZIP содержит исходный код, готового Windows EXE в нём пока нет.

## Вариант B: GitHub Actions — без установки C++ на ПК

1. Загрузите **содержимое** папки релиза в GitHub (в репозитории SFERA Chess Lab используется `.github/workflows/cmept6-windows.yml` в корне).
2. На GitHub откройте **Actions → CMEPT6 1.1 - Windows x64 release → Run workflow**.
3. После зелёного статуса выберите **Artifacts → CMEPT6-Engine-1.1-Windows-x64**.
4. Распакуйте артефакт. Внутри — `CMEPT6-Engine.exe` и документация.

Workflow строит нативный MSVC x64 EXE, запускает все тесты и двухпартийный матч, затем публикует файл. **Здесь workflow ещё не запускался, поэтому готовый Windows EXE не заявляется проверенным.**

## Добавление в шахматную программу

В Arena / Cute Chess GUI откройте меню управления движками, добавьте путь к `CMEPT6-Engine.exe` как **UCI**, установите Hash 32–128 MB. Для первых испытаний оставьте `UncertaintySearch=false`.
