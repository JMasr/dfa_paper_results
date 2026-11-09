# Descriptores agregados publicados

Estos CSV convierten en entradas explícitas los descriptores que la entrega anterior conservaba únicamente en tablas y macros LaTeX. Proceden de los agregados medidos y publicados por los autores; su procedencia está en el manifiesto de esta entrega. No contienen registros individuales, audio ni identificadores de participantes.

`build_metadata.py` reconstruye las dos colecciones de macros y las tablas de cohortes, particiones y demografía desde estos CSV. Esta transformación reproduce los artefactos de descripción; no vuelve a calcular edades o composición desde datos privados. `check_splits.py` contrasta adicionalmente los conteos de hablantes con los logs de protocolo.

Los campos de texto conservan el formato LaTeX de presentación cuando es necesario (rangos, unidades y notas); las cabeceras identifican su significado. Un dato ausente permanece ausente: no se convierte en cero.
