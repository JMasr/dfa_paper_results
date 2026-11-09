# Alcance y límites

La reproducción empieza en los resultados por ejecución de dos campañas ya realizadas. Los contrastes, bootstrap y costes seleccionados se calculan desde los CSV; no se requiere el código que entrenó los modelos. Los datos originales conservan sus hashes.

Los 58 contrastes actuales no utilizan como entradas los resúmenes ni los q históricos: una prueba ejecuta el análisis con esos archivos físicamente ausentes. Existen 85 discrepancias entre q históricos y BH estándar bajo las familias declaradas; sus tablas exhaustivas no están activas y no forman parte de la validación actual. Se mantienen los archivos originales para trazabilidad, sin corregirlos artificialmente.

Cinco archivos de descriptores se generan desde metadatos agregados declarados. No se recalculan edades, sexo o características de modelos desde métricas de entrenamiento. Los conteos de partición se contrastan con los logs.

La sensibilidad se verifica a precisión publicada desde diferencias por bloque: seis resúmenes y cuatro tests. La correlación padding-rendimiento (rho=-0.429, p=0.3965, n=6) permanece como agregado reportado: no están incluidas sus seis parejas originales. Esto no afecta a las tablas de contrastes ni a las figuras principales.

Las figuras cuantitativas siguen la ruta CSV regenerados, HTML, PDF/PNG. Sus valores se comprueban; la identidad de píxeles entre versiones distintas de Chromium o fuentes no se presupone. Las barras de rango son el intervalo intercuartílico; las líneas de diferencias son el rango entre particiones.

La descripción editorial del protocolo debe alinearse con MedianPruner y dos búsquedas externas por celda, con seis/doce trials por búsqueda en los comparadores entrenados. La reproducción no altera resultados para resolver diferencias de redacción.
