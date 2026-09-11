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
`cca6117f80c6961e2b9a6a239417d25d92abb8e4`, que era el último commit de la
rama `main` al elaborar este registro (10 de septiembre de 2026).

## Metodología y alcance

El registro se obtuvo al contrastar las funcionalidades declaradas en
`docs/feature_list.json` con los mensajes de los commits posteriores a la
referencia indicada y hasta el último commit de la rama `main` analizado.

Se incluyen capacidades nuevas o ampliaciones visibles para el usuario que no
están definidas explícitamente en el backlog. Se excluyen correcciones aisladas,
refactorizaciones internas, cambios de documentación y reglas de Git que no
añaden una capacidad funcional o de experiencia independiente.

Las funcionalidades de la fase `ai_reports` permanecen pendientes. No se ha
implementado en este intervalo la generación de informes con IA, proveedores de
IA, sus repositorios ni la página AI Assistant.

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

## Relación con el backlog

Las mejoras anteriores enriquecen funcionalidades MVP ya marcadas como
completadas; no constituyen una nueva funcionalidad de la fase `ai_reports` ni
cambian los estados de `docs/feature_list.json`. Este documento permite
distinguir el alcance original del backlog de las capacidades incorporadas de
forma iterativa después de su definición.
