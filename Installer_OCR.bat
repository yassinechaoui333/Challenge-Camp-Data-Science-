@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Installation des bibliothèques OCR locales. Node.js 22 ou ultérieur est nécessaire.
call npm install --omit=dev
if errorlevel 1 (
  echo Installation incomplète. Vérifiez que Node.js et npm sont installés et que la connexion Internet fonctionne.
) else (
  echo Installation terminée. Lancez Lancer_demo.bat.
)
pause
