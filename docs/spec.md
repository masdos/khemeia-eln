# **Spec: Khemeia ELN**

**Versión:** 6.0

**Descripción General**: Sistema de gestión de laboratorio para investigadores químicos. Centraliza experimentos, asegura la trazabilidad de reactivos/equipos y usa IA local para reportes.

## **Historias de Usuario (El "Qué")**

### **Historia 1: Gestión del Flujo Experimental**

**Como** investigador, **quiero** crear y categorizar mis experimentos, **para** mantener un historial organizado de mi progreso.

* **Criterios de Aceptación:**  
  * Permite estados: Running, Success, Fail.
  * Buscador por texto y filtro por estado; cada fila muestra proyecto y fecha (solo día).
  * Creación rápida desde el dashboard y ficha con pregunta, procedimiento, resultado y conclusiones.
  * Tablas con paginación de diez filas por página.

### **Historia 2: Editor Científico y Archivos**

**Como** químico, **quiero** usar Markdown, fórmulas LaTeX y ver estructuras SMILES, **para** registrar datos técnicos precisos.

* **Criterios de Aceptación:**
  * Subir, listar y borrar adjuntos desde la ficha del experimento, con descripción editable por el usuario.
  * Editor Markdown con previsualización en vivo; al introducir un SMILES válido se muestra su SVG (RDKit, con degradación a `None` si no está disponible o el SMILES es inválido).
  * Cantidad de reactivo con precisión exacta de laboratorio (valor almacenado como texto, sin redondeos) y edición vía diálogo.
  * Exportación del experimento a Markdown, PDF y DOCX, con tablas reales y cabecera de autoría.

### **Historia 3: Trazabilidad de Inventario (Simplificado)**

**Como** usuario, **quiero** asociar reactivos y equipos a mi experimento, **para** tener un registro histórico de los recursos utilizados.

* **Criterios de Aceptación:**
  * Selector de reactivos/equipos existentes.
  * Consulta de "uso histórico": ver en qué experimentos se utilizó un reactivo o equipo específico.
  * Consulta de reactivos y equipos asociados a un experimento específico (tablas con GHS, cantidad y lote).
  * Borrado protegido: no se puede borrar un reactivo o equipo en uso (botón desactivado en tabla y error de negocio claro).
  * Filtro de stock en reactivos (All / In Stock / Out of Stock) combinado con la búsqueda.

### **Historia 4: Asistente de IA Local**

**Como** estudiante, **quiero** que la IA analice mis experimentos seleccionados, **para** redactar borradores de informes técnicos.

* **Criterios de Aceptación:**
  * Integración solo con Ollama local (`http://localhost:11434`); sin LM Studio ni selección de proveedores.
  * Dropdown con los modelos instalados (revalidado en cada carga, vacío por defecto); el modelo recomendado `qwen3.5:4b` es solo sugerencia informativa. La última elección se recuerda en `last_used_model`.
  * Selector de idioma (Spanish/English por defecto, acepta valores tecleados); el informe se escribe en el idioma elegido con título traducido.
  * Generación por streaming con previsualización en vivo y guardia de salida (Stay/Leave) si se abandona a mitad de generación.
  * Borrador técnico en Markdown con fórmulas planas (sin LaTeX/HTML), sin sección Discussion y con apéndices de adjuntos citados por nombre de fichero en texto plano.
  * El generador es proyecto-primero y termina guardando el informe en base de datos (título obligatorio); la exportación a Markdown, PDF o DOCX se hace desde el informe guardado.
  * Si Ollama no está listo o el modelo no está instalado, se muestra aviso sin romper la interfaz.

### **Historia 5: Perfil de Usuario**

**Como** usuario, **quiero** registrar mi nombre y email al iniciar la aplicación por primera vez, **para** que queden asociados como autor en cada experimento que cree.

* **Criterios de Aceptación:**
  * El usuario puede editar su perfil (nombre, email e institución opcional) desde una pantalla accesible en cualquier momento.
  * La página muestra un enlace clicable a la carpeta de datos de la aplicación.

### **Historia 6: Gestión de Informes Guardados**

**Como** investigador, **quiero** guardar, buscar y editar mis informes, **para** recuperarlos sin regenerarlos con IA.

* **Criterios de Aceptación:**
  * Página Reports con búsqueda, alta manual y borrado; detalle con edición y exportación a Markdown, PDF y DOCX.
  * La ficha de proyecto muestra sus informes.

## ---

**Casos Borde y Escenarios de Error**

* **Falta de Reactivo en Lista:** Si el usuario usa algo que no está en el inventario, el sistema debe permitir añadirlo "al vuelo" para no bloquear la investigación.  
* **Falla de IA:** El sistema debe funcionar al 100% como cuaderno aunque el motor de IA esté apagado.
* **Guardado rechazado:** Si el informe no se puede guardar (p. ej. sin título), se muestra aviso explícito; el guardado nunca parece silencioso.

## **Requisitos Clave (Must-Haves)**

* **Local-First:** Todo ocurre en la máquina del usuario.
* **Interoperabilidad:** Exportación a PDF, Markdown y DOCX.