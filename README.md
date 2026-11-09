# DFA: resultados y análisis reproducible

Código y resultados exportados de *Closed-Form Depth-Fusion Readout versus Parameter-Efficient Adaptation of Speech Foundation Models for Low-Resource Clinical Screening from Voice*.

Autores: José Manuel Ramírez Sánchez, Laura Docío-Fernández, Alejandro A. García-Caballero y Carmen García-Mateo.

## Ejecutar

```bash
uv sync --locked
uv run --locked playwright install chromium
uv run --locked pytest -q
uv run --locked python tools/reproduce.py
```

Python 3.11.12 y dependencias fijadas en `uv.lock`. En Linux, Chromium necesita sus bibliotecas del sistema: consultar `playwright install --with-deps chromium` si faltan. Se admite `CHROME_BIN` para un navegador instalado. El procesamiento usa CPU y archivos locales después de instalar las dependencias.

El análisis parte de 2.025 ejecuciones: 828 en `screening_stage/` y 1.197 en `extension_stage/`. Calcula 58 contrastes y genera las tablas y figuras actuales en `outputs/current/`. El informe de reproducción guarda hashes y comparaciones con las referencias. Los CSV de cohortes y modelos están en `metadata/`: son agregados declarados, no se infieren de las métricas de entrenamiento. El entorno no entrena modelos ni recalcula AUROC/F1 desde predicciones individuales. No incluye audio ni registros identificativos de participantes.

`paper/` contiene las referencias numéricas para comprobar el resultado; los generadores calculan salidas nuevas desde los bundles. Los originales conservan sus manifiestos SHA-256. Las tablas históricas no activas en el artículo se mantienen fuera del perfil predeterminado. Véanse `DATA_DICTIONARY.md` y `docs/KNOWN_LIMITS.md` para la procedencia y los límites.

## Auditoría de texto

```bash
uv run --locked python tools/audit_text.py . --git
```

Detecta atribuciones automáticas, restos de herramientas, caracteres invisibles, controles bidireccionales, codificación dañada y diferencias de normalización Unicode. Los signos tipográficos legítimos se clasifican por separado. No determina si un texto fue escrito por una persona o un modelo; tampoco modifica archivos. `--json /ruta/informe.json` guarda el resultado y `--strict` convierte advertencias en errores de salida. `--pdf` examina también el texto y metadatos de PDF cuando está disponible pypdf. Las declaraciones editoriales de uso de herramientas se identifican como tales y no son firmas de autoría.

## Comprobar el proyecto LaTeX adjunto

```bash
uv run --locked python tools/reproduce.py --manuscript-dir ../repo_latex
```

Para construir un archivo autocontenido después de una reproducción correcta: `uv run --locked python tools/package_release.py`. No publica ni crea tags. Código MIT; datos agregados CC BY 4.0, según `LICENSE` y `LICENSE-DATA`.
