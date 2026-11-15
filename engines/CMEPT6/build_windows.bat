@echo off
setlocal
cd /d "%~dp0"
where cl >nul 2>nul
if not errorlevel 1 (
  echo [CMEPT6 1.1] Compiling with MSVC C++17 x64 ...
  cl /nologo /O2 /MT /EHsc /std:c++17 /W4 /Fe:CMEPT6-Engine.exe src\main.cpp
  if errorlevel 1 goto failed
  goto success
)
where g++ >nul 2>nul
if not errorlevel 1 (
  echo [CMEPT6 1.1] Compiling with MinGW-w64 C++17 ...
  g++ -O2 -std=c++17 -pthread -static-libgcc -static-libstdc++ src\main.cpp -o CMEPT6-Engine.exe
  if errorlevel 1 goto failed
  goto success
)
echo [ERROR] No MSVC cl.exe or MinGW-w64 g++ found in PATH.
echo Use "x64 Native Tools Command Prompt for VS 2022" (or newer).
exit /b 1
:failed
echo [ERROR] Windows C++ compilation failed.
exit /b 1
:success
echo [OK] CMEPT6-Engine.exe created. Add it to Arena/Cute Chess as a UCI engine.
exit /b 0
