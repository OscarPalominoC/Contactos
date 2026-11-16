import re, sys
SRC, DST = sys.argv[1], sys.argv[2]
KEEP = {'bitacora_llamadas','bitacora_llamadas_rtmyg','bitacora_llamadas_soat','contacto',
        'entrada_sistema','revision','soat1','usuario','moto','marca','linea'}
marker = re.compile(r'^-- Table structure for table `(\w+)`')
footer = '/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;'
filas = {}
keep = True; pending = None
with open(SRC, encoding='latin-1', newline='') as f, open(DST, 'w', encoding='latin-1', newline='') as out:
    for line in f:
        m = marker.match(line)
        if m:
            keep = m.group(1) in KEEP
            if keep and pending is not None: out.write(pending)
            pending = None
        elif line.startswith(footer):
            keep = True
        if line.rstrip('\r\n') == '--' and not m:
            # podría ser el "--" previo a un marcador: aplazar
            if pending is not None and keep: out.write(pending)
            pending = line; continue
        if pending is not None:
            if keep: out.write(pending)
            pending = None
        if keep:
            out.write(line)
            mi = re.match(r'INSERT INTO `(\w+)` VALUES ', line)
            if mi: filas[mi.group(1)] = filas.get(mi.group(1), 0) + line.count('),(') + 1
    if pending is not None and keep: out.write(pending)
for t in sorted(KEEP): print(f'{t:28} {filas.get(t,0):>8}')
