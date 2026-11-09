# Contribuir al paquete de reproducción

Este repositorio reconstruye el análisis del artículo desde resultados agregados. Repetir entrenamientos requiere el código experimental y los datos originales autorizados.

- Usar ramas `feature/`, `fix/` o `docs/`; no trabajar directamente en `main`.
- Usar `uv sync --locked` y versionar `uv.lock`.
- Conservar entradas científicas y registrar procedencia y versiones; no cambiar datos para ajustar una referencia.
- Separar entradas, salidas regeneradas y referencias. Nunca copiar referencias como salidas para hacer pasar una comparación.
- Toda cifra debe vincularse con sus CSV, configuración y código. Registrar diferencias y datos ausentes de forma explícita.
- No incluir audio, identificadores personales, credenciales ni archivos `.env`.
- Ejecutar pruebas de integridad, reproducción y comparación antes de proponer una release.
- Commits y documentos de entrega en español; código, nombres y comentarios técnicos en inglés. Sin atribuciones automáticas en los mensajes de Git.
- Revisar cambios y metadatos antes de publicar. La reproducción no debe publicar, crear tags/releases ni modificar servicios externos.
