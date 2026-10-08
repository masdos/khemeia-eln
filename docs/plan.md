# Documento de Planificación (PLAN): Khemeia ELN

**Versión:** 6.0
**Stack Principal:** Python, NiceGUI, SQLite.

---

## **1. Arquitectura del Sistema**

El sistema sigue un patrón de **Arquitectura en Capas** con separación explícita entre lógica de negocio y acceso a datos:

```
UI (NiceGUI)
    └── Services          ← Lógica de negocio
         └── Repositories ← Acceso a datos (SQL)
              └── SQLite
```

* **Capa de Interfaz (UI):** NiceGUI en modo escritorio (`native=True`). Revisar [DESIGN.md](DESIGN.md) para detalles.
* **Capa de Servicios (Services):** Contiene la lógica de negocio y las reglas de validación. Cada servicio depende de uno o más repositorios para acceder a los datos.
* **Capa de Repositorios (Repositories):** Un repositorio por entidad de dominio. Los servicios nunca ejecutan SQL directamente.
* **Capa de Datos (Persistence):** SQLite para metadatos y relaciones. Sistema de archivos local para adjuntos, con rutas resueltas en tiempo de ejecución.

---

## **2. Modelo de Datos (Esquema SQLite)**

Revisar [docs/data_model.md](data_model.md) para el esquema completo y diagrama ER.

---

## **3. Estrategia Técnica y Componentes**

### **A. Configuración y Perfil de Usuario**

La aplicación es monousuario. No existe tabla `users`. El perfil se gestiona mediante un fichero `config.json`.

```json
{
  "user_name": "Ada Lovelace",
  "user_email": "adaLovelace@example.com",
  "institution": "Universidad (opcional)",
  "last_used_model": "qwen3.5:4b (opcional)"
}
```

Al arrancar la aplicación, si `config.json` no existe o le faltan `user_name` o `user_email`, se muestra un formulario de bienvenida bloqueante. En modo escritorio (`native=True`). El formulario pide la institución como campo opcional.

El usuario puede modificar su perfil desde la pantalla de ajustes en cualquier momento (nombre, email e institución). `last_used_model` recuerda el último modelo Ollama usado tras una generación exitosa y se descarta si ya no está instalado. Los cuatro campos aceptan override desde entorno (`.env`): `USER_NAME`, `USER_EMAIL`, `INSTITUTION`, `LAST_USED_MODEL` (y variantes con prefijo `KHEMEIA_`).


### **B. Patrón Repository**

Ningún servicio ejecuta SQL directamente. La cadena de dependencias es:

```
ExperimentService
    └── ExperimentRepository   → SELECT / INSERT / UPDATE sobre experiments
    └── ReagentRepository      → consultas sobre reagents y experiment_reagents
```


### **C. Integración de IA — Ollama local**

Ollama es el único backend de IA, sin selección ni abstracción de proveedores:

```
AIService
    └── OllamaClient   → http://localhost:11434
```

`AIService` recibe el modelo y el idioma como parámetros explícitos (elegidos por el usuario); nunca resuelve ni asume ninguno por su cuenta. No existe ningún campo `ai_provider` en `config.json`. El sistema funciona al 100% como cuaderno si Ollama no está disponible: `generate_report()` devuelve `None` sin propagar la excepción (incluido `IncompleteGenerationError` por respuesta truncada).

Detalles vigentes (`app/services/ollama_client.py`, `app/services/ai_service.py`):

* Cliente sobre el SDK oficial de Ollama (`list`/`generate`), endpoint `http://localhost:11434`.
* `RECOMMENDED_MODEL = "qwen3.5:4b"` solo como sugerencia informativa; listo = servidor responde y hay al menos un modelo instalado (`OllamaStatus.is_ready`), sin consultar modelos en memoria.
* Generación solo por streaming (`generate_stream` + callback `on_progress` en `AIService`); la UI la ejecuta en hilo de trabajo con previsualización en vivo y guardia de salida Stay/Leave.
* Llamada con `system` propio (no concatenación), `think=False` explícito y `done_reason` verificado.
* Opciones deterministas: `num_ctx 8192`, `num_predict 2000`, `temperature 0.1`, `top_p 0.2`, `top_k 10`; timeout de generación 1800 s, timeout de estado 2 s.
* Prompt con reglas de verdad (solo hechos de los registros, sin inventar ni calcular), fórmulas planas (`H2SO4`, sin LaTeX/HTML/Unicode), apéndices con tabla de adjuntos y título en el idioma del informe. El selector de idioma acepta valores tecleados.

### **D. Gestión de Adjuntos**

`FileService` es el único componente que conoce el sistema de archivos. Resuelve rutas a partir de `BASE_DIR`:

`BASE_DIR` se resuelve siempre mediante `platformdirs` en tiempo de ejecución, nunca configurable por el usuario.

```
BASE_DIR/attachments/{experiment_id}/{stored_name}
BASE_DIR/exports/{file_name}
```

No existe `BASE_DIR/reports/` en disco: los informes son filas en base de datos (ver E).

1. Usuario selecciona archivo
2. Se copia a la carpeta de la aplicación con `save_attachment_bytes(experiment_id, file_name, data)`
3. Se renombra con un UUID aleatorio (se conserva la extensión)
4. Se guarda `file_name`, `stored_name` y `extension` en `attachments`, más `description` editable por el usuario
5. Al borrar se elimina también el fichero físico; al exportar se incluye nombre, extensión y descripción

### **E. Gestión de Informes**

Los informes se persisten en SQLite para poder recuperarlos, no como ficheros sueltos:

* Tablas `reports (project_id, title, content_markdown)` y `experiment_reports` (vínculo N:M).
* `ReportService` + `ReportRepository`: crear (manual o desde el generador IA), listar por proyecto, actualizar, borrar y vincular experimentos.
* El generador IA es proyecto-primero (los experimentos se cargan solo para el proyecto elegido) y guardar exige título; el borrador avisa si el guardado es rechazado.
* Flujo separado: Guardar persiste en BD; Exportar solo escribe ficheros (igual que en experimentos).
* Páginas: Reports (búsqueda, alta manual, borrado), detalle de informe (edición + exportación) y sección de informes en la ficha de proyecto.

### **F. Exportación**

`ExportService` escribe en `BASE_DIR/exports/` y devuelve la ruta absoluta:

* Experimentos: `export_experiment_markdown/pdf/docx`; informes guardados: `export_report_markdown/pdf/docx` (nombres `report_{id}.md/pdf/docx`).
* Dependencia `python-docx` para DOCX; `reportlab` para PDF. Las tablas Markdown estilo GitHub se renderizan como tablas reales en PDF y DOCX.
* Cabecera unificada con fecha de modificación y autor (email + institución); reactivos y equipos como tablas con cantidad, lote y GHS.
* Las etiquetas de ruta en la UI son avisos clicables que abren la carpeta en el explorador.

---

## **4. Estructura de Carpetas**

```
khemeia_eln/
├── main.py                     # Entrada principal (NiceGUI native=True)
├── docs/                       # Documentación
├── app/
│   ├── database/
│   │   ├── connection.py       # Ciclo de vida de la conexión SQLite
│   │   └── schema.sql          # Migración inicial
│   ├── repositories/           # Un fichero por entidad
│   ├── services/
│   └── ui/                     # Componentes y páginas NiceGUI
├── tests/
└── .env                        # Variables de entorno opcionales (override de config.json)
```

Datos del usuario (fuera del proyecto, gestionado por platformdirs con `appname="khemeia-eln"`):
Linux:   ~/.local/share/khemeia-eln/
macOS:   ~/Library/Application Support/khemeia-eln/
Windows: %APPDATA%\khemeia-eln\
   ├── config.json
   ├── database.db
   ├── attachments/{experiment_id}/
   └── exports/

---

## **5. Estrategia de Testing**

Ningún servicio se considera completo sin su test unitario correspondiente.
