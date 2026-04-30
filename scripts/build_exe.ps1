$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

python -m pip install -r requirements.txt
python -m pip install pyinstaller

python -m PyInstaller `
  --name MatchAI `
  --onefile `
  --console `
  --paths "$Root" `
  --hidden-import api `
  --hidden-import main `
  --collect-all flet `
  --collect-all chromadb `
  --collect-all groq `
  --collect-all psycopg `
  --add-data ".env.example;." `
  --add-data "docker-compose.yml;." `
  "scripts/run_matchai.py"

Write-Host "Executavel gerado em dist/MatchAI.exe"
