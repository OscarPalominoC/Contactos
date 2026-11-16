# Arranca PostgreSQL local del proyecto, el backend Django y el frontend Vite.
# Uso: powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$pg = "C:\Program Files\PostgreSQL\18\bin"

& "$pg\pg_isready.exe" -h localhost -p 5433 | Out-Null
if ($LASTEXITCODE -ne 0) {
    & "$pg\pg_ctl.exe" -D "$raiz\.pgdata" -l "$raiz\logs\postgres.log" -w start
}

Start-Process -FilePath "$raiz\backend\.venv\Scripts\python.exe" `
    -ArgumentList "manage.py", "runserver", "127.0.0.1:8000" `
    -WorkingDirectory "$raiz\backend" -WindowStyle Minimized

Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" `
    -WorkingDirectory "$raiz\frontend" -WindowStyle Minimized

Write-Host "Backend:  http://127.0.0.1:8000  (API /api/v1, documentación /docs para administradores)"
Write-Host "Frontend: http://localhost:5173"
