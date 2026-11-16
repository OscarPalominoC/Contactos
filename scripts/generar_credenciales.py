"""Genera contraseñas temporales para los usuarios del dump legado.

No lee ni copia la columna `clave` legada: solo nip, nombre y tipo.
Uso: python -I generar_credenciales.py <dump.sql> <salida.md> <salida.json> <fecha_firma>
"""
import json
import os
import re
import secrets
import string
import sys

DUMP, SALIDA_MD, SALIDA_JSON, FIRMA = sys.argv[1:5]
AMBIGUOS = set("O0Il1|")
MAYUS = [c for c in string.ascii_uppercase if c not in AMBIGUOS]
MINUS = [c for c in string.ascii_lowercase if c not in AMBIGUOS]
DIGITOS = [c for c in string.digits if c not in AMBIGUOS]
SIMBOLOS = list("#$%*+-=?@_")
TODOS = MAYUS + MINUS + DIGITOS + SIMBOLOS
LONGITUD = 16


def generar_clave() -> str:
    base = [secrets.choice(g) for g in (MAYUS, MINUS, DIGITOS, SIMBOLOS)]
    base += [secrets.choice(TODOS) for _ in range(LONGITUD - len(base))]
    secrets.SystemRandom().shuffle(base)
    return "".join(base)


linea = ""
with open(DUMP, encoding="latin-1") as dump:
    for fila in dump:
        if fila.startswith("INSERT INTO `usuario` VALUES "):
            linea = fila
            break
tuplas = re.findall(r"\('([^']*)','([^']*)','[^']*','([^']*)'\)", linea)
usuarios = sorted(({"nip": n, "nombre": nom, "tipo": t} for n, nom, t in tuplas), key=lambda u: (u["tipo"], u["nombre"]))
usadas: set[str] = set()

def _obtener_clave_inicial() -> str | None:
    clave = os.getenv("CLAVE_TEMPORAL_INICIAL")
    if clave:
        return clave.strip()
    rutas = [
        os.path.join(os.path.dirname(__file__), "..", "backend", ".env"),
        os.path.join(os.path.dirname(__file__), "..", ".env"),
        os.path.join(os.path.dirname(__file__), ".env"),
        "backend/.env",
        ".env",
    ]
    for ruta in rutas:
        if os.path.isfile(ruta):
            with open(ruta, encoding="utf-8", errors="ignore") as f:
                for l in f:
                    l = l.strip()
                    if l.startswith("CLAVE_TEMPORAL_INICIAL="):
                        val = l.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
    return "CheckLTDA!"

clave_fija = _obtener_clave_inicial()
for usuario in usuarios:
    if clave_fija:
        clave = clave_fija
    else:
        clave = generar_clave()
        while clave in usadas:
            clave = generar_clave()
        usadas.add(clave)
    usuario["clave_temporal"] = clave

with open(SALIDA_JSON, "w", encoding="utf-8") as js:
    json.dump(usuarios, js, ensure_ascii=False, indent=2)

filas = "\n".join(f"| `{u['nip']}` | {u['nombre']} | {u['tipo']} | `{u['clave_temporal']}` |" for u in usuarios)
md = f"""---
persona: oscar
ia: Claude Code (Claude Opus 5.5)
actualizado: {FIRMA}
zona_horaria: America/Bogota
estado: CONFIDENCIAL — entregar en persona y borrar tras el primer ingreso
---
# Credenciales temporales — Check Contactos

> **CONFIDENCIAL.** Este documento contiene contraseñas de acceso. No se envía por correo ni por chat, no se versiona en Git (está en `.gitignore`) y se destruye en cuanto todos los usuarios hayan cambiado su clave.

## Por qué existe
El sistema legado guardaba las claves en texto plano y muchas eran triviales. **Ninguna clave antigua se migra.** Cada usuario recibe una contraseña temporal aleatoria de {LONGITUD} caracteres (módulo `secrets` de Python, sin caracteres ambiguos `O 0 I l 1 |`). En la aplicación se guarda solo su hash Argon2id con la marca `debe_cambiar_clave = Sí`.

## Instrucciones de primer ingreso
1. Abrir la aplicación en `http://localhost:5173` e ingresar con el **usuario (nip)** y la **contraseña temporal**.
2. El sistema obliga a cambiar la clave antes de mostrar cualquier pantalla.
3. La nueva clave debe tener **mínimo 12 caracteres** y no puede ser la cédula, el nombre, una clave común ni la clave temporal.
4. Tras 5 intentos fallidos la cuenta se bloquea 1 hora; un administrador puede desbloquearla desde Django Admin.

## Usuarios ({len(usuarios)})
| Usuario (nip) | Nombre | Rol | Contraseña temporal |
|---|---|---|---|
{filas}

## Pendientes `[POR CONFIRMAR]`
- La empresa debe confirmar si las cuentas de prueba (por ejemplo, la cuenta `PRUEBA`) se desactivan en lugar de migrarse.
- La empresa debe confirmar qué usuarios siguen activos; los que ya no trabajen en Check se desactivan desde Django Admin.
"""
with open(SALIDA_MD, "w", encoding="utf-8") as salida:
    salida.write(md)
print(f"usuarios={len(usuarios)} claves_unicas={len(usadas)}")
