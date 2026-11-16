# Ejecuta la auditoría de accesibilidad (axe-core + Playwright) contra la app real.
# Crea una cuenta administradora efímera, corre las pruebas y la elimina al final.
# Requiere backend (127.0.0.1:8000) y frontend (localhost:5173) en ejecución.
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$python = "$raiz\backend\.venv\Scripts\python.exe"
$nip = "e2e" + (Get-Random -Minimum 1000 -Maximum 9999)
$bytes = New-Object byte[] 18
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$clave = "E2e-" + [Convert]::ToBase64String($bytes).Replace("/", "x").Replace("+", "y")

$crear = "from apps.cuentas.models import Usuario; u=Usuario.objects.create_user('$nip','CUENTA DE PRUEBA E2E','$clave',rol='administrador'); u.debe_cambiar_clave=False; u.save()"
$borrar = "from apps.cuentas.models import Usuario, Ingreso; Usuario.objects.filter(nip='$nip').delete(); Ingreso.objects.filter(nip_usuario='$nip').delete()"

Push-Location "$raiz\backend"
& $python manage.py shell -c $crear | Out-Null
Pop-Location
try {
    $env:E2E_NIP = $nip
    $env:E2E_CLAVE = $clave
    Push-Location "$raiz\frontend"
    npx playwright test
    $codigo = $LASTEXITCODE
    Pop-Location
} finally {
    Push-Location "$raiz\backend"
    & $python manage.py shell -c $borrar | Out-Null
    Pop-Location
    Remove-Item Env:E2E_NIP, Env:E2E_CLAVE -ErrorAction SilentlyContinue
}
exit $codigo
