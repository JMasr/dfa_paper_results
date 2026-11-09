# Referencias de artefactos del artículo

`current_artifacts.json` recoge las entradas literales de los wrappers Elsevier del artículo y suplemento con comentarios excluidos: 19 archivos TeX y cuatro figuras. También conserva hashes de las fuentes y las entradas comentadas, sin reproducir el texto del artículo. `used_macros.json` contiene las 188 macros científicas utilizadas.

`generated/` y `layout/` son referencias de comparación. Los scripts escriben salidas nuevas en `outputs/current/`; no copian estos TeX como resultados. El perfil predeterminado excluye `supps_tab_all_one.tex` y `supps_tab_all_two.tex`, que ya no están activas en el manuscrito. El resto de artefactos inactivos que se recalculan desde ejecuciones se conserva como detalle adicional, identificado por el mapa de cobertura.

| Grupo activo | Generación |
|---|---|
| Tablas de rendimiento, contrastes, controles, corpus y costes | `build_paper_sota.py --from-runs`, con resultados por ejecución y bundle de costes |
| Estadísticas completas, brazos adicionales y relanzamiento entre etapas | Mismo generador; nuevas familias de p/q desde las filas originales |
| Tres vistas editoriales | `build_editorial_views.py`, desde tablas recién calculadas |
| Macros del protocolo | `build_protocol_macros.py`, desde configuración/logs exportados |
| Sensibilidad | `build_sensitivity_macros.py`, JSON con diferencias por bloque y agregados; precisión verificada |
| Cinco archivos de descriptores | `build_metadata.py`, desde CSV de metadatos agregados; conteos de partición comprobados con logs |
| Figuras de diferencias y rangos | CSV regenerados → `build_readable_figures.py` → HTML → PDF/PNG |
| Esquema de métodos | HTML editable → mismo renderizador |

Las antiguas tablas exhaustivas y cuatro matrices por bloque permanecen en las referencias históricas. Sus nombres/números de tabla antiguos no deben interpretarse como la numeración del suplemento actual. Véase `docs/ANNEX_DECISION.md`.
