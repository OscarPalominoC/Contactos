"""Cuenta los valores distintos de columnas de estado y motivo (solo lectura)."""
import re
import sys
from collections import Counter

SPEC = {
    "contacto": [9],
    "revision": [11],
    "soat1": [4],
    "bitacora_llamadas": [2, 5],
    "bitacora_llamadas_rtmyg": [2, 5],
    "bitacora_llamadas_soat": [2, 5],
}
VALOR = re.compile(r"'(?:[^'\\]|\\.)*'|NULL|-?\d+(?:\.\d+)?")
conteos = {(t, i): Counter() for t, ix in SPEC.items() for i in ix}
with open(sys.argv[1], encoding="latin-1") as dump:
    for linea in dump:
        m = re.match(r"INSERT INTO `(\w+)` VALUES \(", linea)
        if not m or m.group(1) not in SPEC:
            continue
        tabla = m.group(1)
        for fila in linea[m.end():].rstrip().rstrip(";").rstrip(")").split("),("):
            valores = VALOR.findall(fila)
            for i in SPEC[tabla]:
                if i < len(valores):
                    conteos[(tabla, i)][valores[i]] += 1
for clave, cont in conteos.items():
    print(clave, len(cont), cont.most_common(8))
