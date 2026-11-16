"""Lectura en streaming de un dump de MySQL: devuelve las filas de los INSERT sin ejecutar SQL."""

from collections.abc import Iterator
from pathlib import Path

ESCAPES = {"0": "\0", "n": "\n", "r": "\r", "t": "\t", "Z": "\x1a", "b": "\b"}
Valor = str | None


def _parsear_valores(texto: str, inicio: int) -> Iterator[list[Valor]]:
    """Recorre `(v1,'v2',NULL),(...)` desde `inicio` con un autómata; respeta comillas y escapes de MySQL."""
    i = inicio
    n = len(texto)
    while i < n:
        caracter = texto[i]
        if caracter == "(":
            fila: list[Valor] = []
            i += 1
            while True:
                caracter = texto[i]
                if caracter == "'":
                    i += 1
                    partes: list[str] = []
                    while True:
                        caracter = texto[i]
                        if caracter == "\\":
                            siguiente = texto[i + 1]
                            partes.append(ESCAPES.get(siguiente, siguiente))
                            i += 2
                        elif caracter == "'":
                            if i + 1 < n and texto[i + 1] == "'":
                                partes.append("'")
                                i += 2
                            else:
                                i += 1
                                break
                        else:
                            fin = i
                            while fin < n and texto[fin] not in "\\'":
                                fin += 1
                            partes.append(texto[i:fin])
                            i = fin
                    fila.append("".join(partes))
                else:
                    fin = i
                    while texto[fin] not in ",)":
                        fin += 1
                    crudo = texto[i:fin].strip()
                    fila.append(None if crudo.upper() == "NULL" else crudo)
                    i = fin
                caracter = texto[i]
                if caracter == ",":
                    i += 1
                    continue
                if caracter == ")":
                    i += 1
                    break
            yield fila
        elif caracter in ",; \r\n":
            i += 1
        else:
            raise ValueError(f"Carácter inesperado en el dump en la posición {i}: {caracter!r}")


def filas_de_tabla(ruta: Path, tabla: str) -> Iterator[list[Valor]]:
    """Filas de `INSERT INTO `tabla` VALUES ...` del dump (latin-1 → str)."""
    # Prefijo de texto para comparar con startswith; no se construye ni ejecuta SQL.
    prefijo = f"INSERT INTO `{tabla}` VALUES "  # noqa: S608  # nosec B608
    with ruta.open(encoding="latin-1", newline="") as dump:
        for linea in dump:
            if linea.startswith(prefijo):
                yield from _parsear_valores(linea, len(prefijo))


def reparar_texto(valor: str) -> str:
    """El dump declara latin1, pero algunas filas contienen UTF-8 guardado como latin1 (mojibake). Se repara si aplica."""
    if "Ã" in valor or "Â" in valor:
        try:
            return valor.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return valor
    return valor
