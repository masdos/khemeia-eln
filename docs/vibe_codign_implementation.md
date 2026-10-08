# Registro de implementaciones fuera del backlog

Este documento conserva las mejoras funcionales y de experiencia de usuario
implementadas después de la referencia `444f9aaee42b60361f6aa47ee65b759bfee741f1`.
Complementa `feature_list.json`: no sustituye su planificación ni modifica el
estado de sus funcionalidades.

## Modalidad de implementación

Las capacidades registradas en este documento se incorporaron mediante un ciclo
iterativo de conversación con un agente y un modelo de lenguaje: se describía
la necesidad por chat, se implementaba o ajustaba la solución y se refinaba con
nuevas indicaciones. En este documento se denomina a esa práctica *vibe
coding* o desarrollo guiado por prompts.

Este flujo es distinto del desarrollo planificado desde `feature_list.json`:
en ese método, el agente lee una funcionalidad pendiente con sus criterios de
aceptación y realiza su implementación de forma secuencial. Las entradas de
este registro documentan ampliaciones surgidas durante la interacción, no
nuevas funcionalidades formalizadas previamente en el backlog.

## Periodo cubierto

La práctica descrita abarca los commits posteriores a
`444f9aaee42b60361f6aa47ee65b759bfee741f1` y hasta
`aa7a3f385b1a9b2333578743e3250ad145dae938`, último commit de la
rama `main` al elaborar esta actualización (8 de octubre de 2026).

El registro inicial cubría hasta
`cca6117f80c6961e2b9a6a239417d25d92abb8e4` (10 de septiembre de 2026).
Esta actualización añade el intervalo posterior
`cca6117f80c6961e2b9a6a239417d25d92abb8e4..aa7a3f385b1a9b2333578743e3250ad145dae938`
sin modificar las secciones ya consolidadas.

## Metodología y alcance

El registro se obtuvo al contrastar las funcionalidades declaradas en
`docs/feature_list.json` (versión `7.0`, todas las funcionalidades en estado
`done`, incluidas las de la fase `ai_reports` hasta la número `31`) con los
mensajes de los commits posteriores a la referencia indicada y hasta el último
commit de la rama `main` analizado.

Se incluyen capacidades nuevas o ampliaciones visibles para el usuario que no
están definidas explícitamente en el backlog. Se excluyen correcciones aisladas,
refactorizaciones internas, cambios de documentación y reglas de Git que no
añaden una capacidad funcional o de experiencia independiente.

En el primer intervalo las funcionalidades de la fase `ai_reports`
permanecían pendientes. En el segundo intervalo (`cca6117` en adelante) se
completaron en el backlog `report_repository`, cliente Ollama, `AIService`,
exportación de informes IA, páginas AI Assistant y selector de modelo e idioma
(funcionalidades `24` a `31`); por tanto, esas implementaciones base no se
repiten aquí. Este documento recoge solo lo que las excede.

## Flujo de experimentos

Estas mejoras amplían las funcionalidades MVP de ExperimentRepository,
ExperimentService, Dashboard y Experiment Detail.

- Se permite eliminar experimentos desde el flujo de gestión y se muestra el
  proyecto asociado en los listados de experimentos.
- La creación inicial de un experimento se realiza en un diálogo rápido del
  dashboard; la captura detallada se completa después en su ficha.
- El registro científico del experimento se reorganizó en los campos
  **pregunta**, **procedimiento experimental**, **resultado** y
  **conclusiones**, sustituyendo la terminología anterior por etiquetas más
  claras para el usuario.
- La ficha de un experimento existente muestra sus fechas de creación y última
  modificación.

## Inventario y recursos

Estas mejoras amplían InventoryService, las relaciones entre experimentos y
recursos, y la página Inventory del MVP.

- Desde la ficha del experimento se pueden vincular y desvincular reactivos y
  equipos existentes. Cuando el inventario está vacío, la interfaz guía al
  usuario para crear el recurso necesario.
- Las secciones de reactivos y equipos incorporan búsqueda local para localizar
  registros sin abandonar la página.
- El servicio de inventario ofrece consulta y actualización de reactivos y
  equipos, habilitando su edición desde la interfaz.
- Los reactivos muestran el número de lote tanto en el inventario como en los
  recursos asociados al experimento.
- Existen fichas de consulta para proyectos, protocolos, reactivos y equipos.
  La navegación desde las tablas usa una acción de vista; la ficha de proyecto
  muestra sus experimentos y la de reactivo protege CAS y SMILES cuando ya hay
  historial de uso.

## Adjuntos y exportación

Estas mejoras amplían FileService, la sección de adjuntos de Experiment Detail y
ExportService.

- La carga de adjuntos se adaptó a la API actual de NiceGUI y mantiene la
  lectura asíncrona en la interfaz antes de entregar los bytes a FileService.
- Al eliminar un adjunto también se elimina su fichero físico, evitando que
  queden archivos huérfanos en el almacenamiento local. La interfaz informa de
  la ubicación de ese almacenamiento.
- Las exportaciones Markdown y PDF incluyen fecha, datos de autoría, proyecto,
  protocolo, estado, secciones científicas, adjuntos y recursos usados.
- Las líneas de reactivos exportadas incluyen el número de lote cuando está
  disponible, y la exportación PDF conserva formato Markdown básico de negrita
  y cursiva.

## Navegación y experiencia de usuario

Estas mejoras refinan las páginas MVP y su navegación principal.

- La aplicación usa una carcasa de una sola página: al navegar se actualiza el
  contenido sin reconstruir toda la interfaz.
- La barra lateral permanece visible durante el desplazamiento, mantiene el
  elemento activo y conserva su estado al cambiar de vista.
- La interfaz adopta un diseño de paneles, iconos de navegación, logo centrado
  y favicon para la ventana nativa.
- Los formularios señalan los campos obligatorios, usan acciones primarias y
  de cancelación consistentes, y el perfil se presenta como información de
  lectura con edición en un diálogo.
- Las tablas de experimentos, proyectos, protocolos, reactivos y equipos
  incorporan paginación clásica con diez filas por página.

## Componentes reutilizables y edición de contenido

Estas implementaciones amplían las páginas MVP mediante patrones de interfaz
compartidos.

- Se creó una biblioteca de componentes compartidos para diálogos, formularios,
  tablas, listas, metadatos, pictogramas GHS y edición Markdown. Las páginas
  existentes se migraron a estos componentes para ofrecer patrones uniformes.
- El editor Markdown de protocolos y de las secciones científicas del
  experimento añade una barra de herramientas y previsualización en vivo.
- Las pantallas de detalle reutilizan un patrón de navegación de consulta y
  edición que centraliza acciones, metadatos y retorno a la lista.

## Centro de IA

La navegación de IA se unificó en una única entrada lateral para evitar
duplicidades confusas para el público no técnico.

- La barra lateral muestra solo **AI Assistant** con el icono robot; la
  entrada **AI Reports** desapareció y su ruta se eliminó.
- La vista `ai_assistant` es un centro en dos columnas: a la izquierda
  explica qué es Ollama, por qué los modelos locales (los datos nunca salen
  del equipo, sin cuentas ni APIs de terceros, funciona sin conexión) y los
  requisitos en 3 pasos estáticos con sus recursos (url oficial, web y
  comando de descarga de modelo, comando y web de arranque del servidor);
  debajo, el indicador de estado (que parte de "Not checked") y un botón
  para comprobar los requisitos a demanda, con spinner mientras trabaja y
  sin comprobación automática al cargar. Los mensajes de estado son cortos
  y no repiten comandos ni webs.
- La tarjeta del menú se llama Report generator, como la página a la que
  navega.
- La vista secundaria `ai_report_generator`
  (sin entrada propia en el menú, con botón de volver): el formulario
  anterior con selector de experimentos, desplegable de modelo, borrador
  editable y exportación a Markdown o PDF. Los botones de exportar nacen
  deshabilitados hasta que el borrador tiene contenido, se eliminó el icono
  informativo de modelos recomendados y la generación es asíncrona (botón
  deshabilitado y spinner, sin congelar la interfaz). La lógica de readiness se
  conservó en `app/ui/pages/ai_reports.py` como módulo importado por el
  centro, sin constructor de página propio.

## Ampliaciones posteriores a `cca6117` (hasta `aa7a3f3`)

Intervalo `cca6117f80c6961e2b9a6a239417d25d92abb8e4..aa7a3f385b1a9b2333578743e3250ad145dae938`.
Se excluyen las implementaciones que cierran las funcionalidades `24` a `31`
del backlog y las tareas de documentación, limpieza, formato y apagado.

### Informes guardados y gestión

Amplían `ReportRepository` y `ExportService` más allá de `export_ai_report_*`.

- Los informes se remodelan alrededor de `project_id`, título y
  `content_markdown` para poder recuperar borradores desde la base de datos.
- El generador pasa a ser proyecto-primero: los experimentos se cargan solo
  para el proyecto elegido y guardar exige título.
- Se separan responsabilidades: Guardar persiste en base de datos mientras
  Exportar solo escribe ficheros, igual que en experimentos.
- Nueva página Reports con búsqueda, diálogo de creación manual y borrado
  desde la barra lateral.
- Nueva página de detalle de informe con edición manual y sección de
  exportación Markdown/PDF/DOCX.
- La ficha de proyecto muestra sus informes, igual que su tabla de
  experimentos.
- En el generador se elimina la exportación directa de borradores: el flujo
  termina guardando el informe para exportarlo después. El borrador avisa con
  popup si el guardado es rechazado y el campo título queda marcado como
  obligatorio.

### Centro AI Assistant y generación

Amplían las páginas `ai_reports`, `ai_assistant` y `ai_report_generator`.

- El hub se organiza en pestañas (Assistant Features y Setup) con las
  funciones en rejilla guiada por la lista `FEATURES` y estado visible en la
  cabecera.
- La vista de fórmulas pide Markdown estándar con fórmulas planas
  (por ejemplo `H2SO4`), sin LaTeX, HTML ni subíndices Unicode; el borrador
  se sanea en local antes de previsualizar o exportar a PDF.
- Se elimina la sección Discussion del informe y se mantiene Conclusions; el
  encabezado de la rejilla pasa a llamarse Features.
- La comprobación de requisitos pasa a validación automática silenciosa al
  entrar, con indicador solo en cabecera y zona de Check solo para mensajes.
- La carga de modelos instalados se hace en hilo de trabajo para no bloquear
  la navegación; la generación avisa de que el borrador puede tardar varios
  minutos.
- La generación usa streaming con previsualización en vivo: el cliente expone
  `generate_stream`, `AIService` acepta callback `on_progress` y la UI sondea
  una cola con temporizador mostrando spinner y borrador parcial. El
  streaming queda como única vía de generación en producción.
- Guardia de salida durante la generación: al abandonar a mitad del stream
  se pide confirmación con diálogo Stay/Leave y cancelación cooperativa.
- El prompt del sistema se enriquece con nombre de protocolo, reactivos,
  equipos y adjuntos por id, con cantidades, lotes y peligros GHS; solo se
  aporta el nombre del protocolo.
- Opciones Ollama ajustadas para borradores factuales y estables
  (`num_ctx 8192`, `temperature 0.1`, `top_p 0.2`, `top_k 10`), con registro
  de tokens y aviso si el contexto está casi lleno.
- Nuevas reglas de informe: apéndices con tabla de adjuntos (File name,
  Description, más Experiment si hay varios), prohibición de sintaxis de
  imagen/enlace para adjuntos (solo nombre de fichero en texto plano) y
  título del informe en el idioma del informe en vez de copiar el Title del
  experimento.
- El selector de idioma acepta valores tecleados (add-unique, confirma al
  perder foco) con placeholder de ayuda, más allá de la preselección
  Spanish/English del backlog.

### Exportación y ficheros

Amplían `ExportService` y la presentación de rutas.

- Nueva exportación DOCX para experimentos e informes (`python-docx`),
  con encabezados, listas y negrita/cursiva; botones con etiquetas cortas
  Markdown, DOCX y PDF.
- Las tablas Markdown estilo GitHub se renderizan como tablas en PDF
  (cabecera en negrita con reportlab) y en DOCX (tablas con rejilla).
- Cabecera unificada: fecha de modificación y autor sobre el título como
  líneas planas; reactivos y equipos como tablas Markdown con datos de
  detalle, manteniendo descripciones multilínea en una sola fila.
- Cabecera de informes con fecha, email de usuario e institución; los
  informes guardados se exportan como `report_{id}.md` y `report_{id}.pdf`.
  El detalle de informe exporta el informe guardado sin duplicar el título.
- Las etiquetas de ruta de exportación y de adjuntos pasan a ser avisos
  clicables que abren la carpeta correspondiente en el explorador.

### Experimentos y recursos

Amplían Experiment Detail e Inventory más allá del CRUD MVP.

- Los recursos vinculados se muestran en tablas con columnas de etiquetas
  GHS, cantidad y lote; los formularios de añadir pasan encima de las
  tablas y las acciones se simplifican a ver estructura/desvincular.
- Edición de cantidad de reactivo vía diálogo (re-vincula con
  `INSERT OR REPLACE`) y preservación exacta del valor introducido
  (almacenado como texto para no perder precisión ni ceros finales).
- Vista previa de equipo vinculado en diálogo sin perder el contexto del
  experimento, con acción para ir a su página completa.
- Botón de cierre en el diálogo de imagen de molécula junto a Copy SVG.
- Cada cambio de recursos (vincular reactivos, equipos o adjuntos) refresca
  `modified_at` del experimento mediante ayuda `touch`.
- Las tablas muestran fechas solo con día (`YYYY-MM-DD`) en experimentos,
  proyectos, protocolos e historial de uso.
- Los adjuntos admiten campo descripción editable por el usuario (tabla
  alineada a la izquierda con diálogo de edición), con borrado físico del
  fichero, y nombre, extensión y descripción incluidos en prompts de IA y
  exportaciones.

### Inventario y perfil

- Borrado protegido de reactivos y equipos: el repositorio rechaza borrar
  mientras haya experimentos que los referencien y el servicio lo traduce a
  error de negocio; se añade la consulta de historial de uso de equipos que
  faltaba.
- En las tablas el botón papelera nace desactivado y gris cuando el registro
  está en uso; el diálogo de confirmación borra y refresca.
- Filtro de stock en reactivos (All / In Stock / Out of Stock) combinado con
  la búsqueda de texto, alineado con el filtro de estado del dashboard.
- Campo opcional institución en perfil (`AppConfig`, página de perfil,
  diálogo de edición y formulario de bienvenida) con sustitución desde
  entorno; la página muestra además un enlace clicable a la carpeta de datos
  de la aplicación.

## Relación con el backlog

Las mejoras anteriores al corte `cca6117` enriquecen funcionalidades MVP ya
marcadas como completadas; no constituyen una nueva funcionalidad de la fase
`ai_reports` ni cambian los estados de `docs/feature_list.json`.

Las ampliaciones posteriores a `cca6117` parten de un backlog `ai_reports`
ya completado (`24` a `31` en estado `done` en la versión `7.0`) y lo exceden
en gestión de informes, generación por streaming, exportación DOCX/tablas,
recursos de experimento, inventario, adjuntos y perfil. Tampoco modifican los
estados de `docs/feature_list.json`: este documento permite distinguir el
alcance original del backlog de las capacidades incorporadas de forma
iterativa después de su definición.
