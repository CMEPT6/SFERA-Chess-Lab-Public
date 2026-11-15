# CMEPT6 Engine — исходный код

Движок CMEPT6 Engine 1.1 входит в проект SFERA Chess Lab и хранится отдельно: [engines/CMEPT6](engines/CMEPT6/README.md).

- Язык C++17, интерфейс UCI.
- Исходники: `engines/CMEPT6/src/main.cpp`.
- Сборка: `cmake -S engines/CMEPT6 -B build/cmept6 -DCMAKE_BUILD_TYPE=Release` и `cmake --build build/cmept6`.
- Тесты: `engines/CMEPT6/tests`.
- Windows/Linux: GitHub Actions (`cmept6-windows.yml`, `cmept6-linux.yml`).
- Лицензия: MIT (см. `engines/CMEPT6/LICENSE`).

**Статус:** исследовательский движок, не подтверждённая сила уровня Stockfish.
