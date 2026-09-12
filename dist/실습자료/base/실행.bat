@echo off
chcp 65001 > nul
cd /d "%~dp0"
title AI App - 이 창을 닫으면 앱이 꺼집니다

echo.
echo  ============================================
echo   AI App 을 시작합니다
echo  ============================================
echo.

where node > nul 2>&1
if errorlevel 1 (
  echo  [Node.js 가 없습니다]
  echo.
  echo   nodejs.org 에서 LTS 를 설치한 뒤 다시 실행해 주세요.
  echo.
  pause
  exit /b
)

netstat -ano | findstr ":8787 " | findstr LISTENING > nul
if not errorlevel 1 (
  echo   * 이미 떠 있는 앱이 하나 있습니다. 그건 그대로 두고, 이 앱은 다른 주소로 엽니다.
  echo.
)

echo   잠시 뒤 브라우저가 열립니다.
echo   열리지 않으면 아래 READY 뒤에 적힌 주소를 주소창에 넣어 주세요.
echo.
echo   * 이 창을 닫으면 앱이 꺼집니다. 쓰는 동안은 그대로 두세요.
echo.

node server.js --open

echo.
echo   앱이 종료되었습니다.
pause
