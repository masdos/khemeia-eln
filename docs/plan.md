# Documento de Planificación (PLAN): Khemeia ELN

**Versión:** 5.0
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
  "user_email": "adaLovelace@example.com"
}
```

Al arrancar la aplicación, si `config.json` no existe o está incompleto, se muestra un formulario de bienvenida bloqueante. En modo escritorio (`native=True`).

El usuario puede modificar su perfil desde la pantalla de ajustes en cualquier momento.


### **B. Patrón Repository**

Ningún servicio ejecuta SQL directamente. La cadena de dependencias es:

```
ExperimentService
    └── ExperimentRepository   → SELECT / INSERT / UPDATE sobre experiments
    └── ReagentRepository      → consultas sobre reagents y experiment_reagents
```


### **C. Integración de IA — Interfaz AIProvider**

Se define una interfaz `AIProvider` que desacopla el backend de IA del resto del código:

```
AIProvider (interfaz)
    ├── LMStudioProvider   → http://localhost:1234/v1
    ├── OllamaProvider     → http://localhost:11434/v1
    └── RemoteAPIProvider  → endpoint configurable
```

El proveedor activo se configura en `config.json`. `AIService` solo conoce la interfaz, no la implementación concreta. El sistema funciona al 100% como cuaderno si ningún proveedor está disponible.

### **D. Gestión de Adjuntos**

`FileService` es el único componente que conoce el sistema de archivos. Resuelve rutas a partir de `BASE_DIR`:

`BASE_DIR` se resuelve siempre mediante `platformdirs` en tiempo de ejecución, nunca configurable por el usuario.

```
BASE_DIR/attachments/{experiment_id}/{stored_name}
BASE_DIR/reports/{stored_name}
```
1. Usuario selecciona archivo
2. Se copia a la carpeta de la aplicación
3. Se renombra con un UUID aleatorio
4. Se guarda el nombre físico en SQLite `stored_name` en la tabla correspondiente , reports o attachments.

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

Datos del usuario (fuera del proyecto, gestionado por platformdirs):
Linux:   ~/.local/share/khemeia/
macOS:   ~/Library/Application Support/khemeia/
Windows: %APPDATA%\khemeia\
   ├── config.json
   ├── database.db
   ├── attachments/{experiment_id}/
   ├── reports/
   └── exports/

---

## **5. Estrategia de Testing**

Ningún servicio se considera completo sin su test unitario correspondiente.
