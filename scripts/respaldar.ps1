# Copia de seguridad local de la base de datos (formato custom de pg_dump, comprimido).
# Uso: powershell -ExecutionPolicy Bypass -File scripts\respaldar.ps1
# Programación sugerida: Programador de tareas de Windows, a diario fuera del horario de atención.
# El cifrado del archivo de respaldo está pendiente de definir con la empresa (ver plan.md §13).
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$pg = "C:\Program Files\PostgreSQL\18\bin"
$destino = Join-Path $raiz "respaldos"
New-Item -ItemType Directory -Force $destino | Out-Null

$env:PGPASSWORD = (Get-Content -Raw "$raiz\.secrets\pg_superuser.txt").Trim()
$archivo = Join-Path $destino ("check_contactos-{0:yyyy-MM-dd-HHmm}.dump" -f (Get-Date))
& "$pg\pg_dump.exe" -h localhost -p 5433 -U check_super -Fc -f $archivo check_contactos
Remove-Item Env:PGPASSWORD

# Conserva los 14 respaldos más recientes.
Get-ChildItem $destino -Filter "check_contactos-*.dump" | Sort-Object LastWriteTime -Descending |
    Select-Object -Skip 14 | Remove-Item
Write-Host "Respaldo creado: $archivo"
