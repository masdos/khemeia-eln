# **Spec: Khemeia ELN**

**Descripción General**: Sistema de gestión de laboratorio para investigadores químicos. Centraliza experimentos, asegura la trazabilidad de reactivos/equipos y usa IA local para reportes, priorizando la integridad mediante firmas digitales (hashing).

## **Historias de Usuario (El "Qué")**

### **Historia 1: Gestión del Flujo Experimental**

**Como** investigador, **quiero** crear y categorizar mis experimentos, **para** mantener un historial organizado de mi progreso.

* **Criterios de Aceptación:**  
  * Permite estados: Running, Success, Fail.  
  * Buscador por etiquetas y texto.

### **Historia 2: Editor Científico y Archivos**

**Como** químico, **quiero** usar Markdown, fórmulas LaTeX y ver estructuras SMILES, **para** registrar datos técnicos precisos.

* **Criterios de Aceptación:**  
  * Renderizado en tiempo real de fórmulas.  
  * Posibilidad de adjuntar imágenes y documentos directamente a la entrada del experimento.

### **Historia 3: Trazabilidad de Inventario (Simplificado)**

**Como** usuario, **quiero** asociar reactivos y equipos a mi experimento, **para** tener un registro histórico de los recursos utilizados.

* **Criterios de Aceptación:**  
  * Selector de reactivos/equipos existentes.  
  * Consulta de "uso histórico": ver en qué experimentos se utilizó un reactivo específico.
  * Consulta de reactivos y equipos asociados a un experimento específico.

### **Historia 4: Asistente de IA Local**

**Como** estudiante, **quiero** que la IA analice mis experimentos seleccionados, **para** redactar borradores de informes técnicos o diapositivas.

* **Criterios de Aceptación:**  
  * Integración con LM Studio/Gemma local.  
  * Generación de archivos Markdown exportables.

### **Historia 5: Seguridad e Integridad (SHA-256)**

**Como** autor, **quiero** generar una firma digital (hash) de mi experimento al finalizarlo, **para** garantizar que los datos no han sido alterados a posteriori.

* **Criterios de Aceptación:**  
  * Generación automática del hash SHA-256 al cerrar el experimento.  

## ---

**Casos Borde y Escenarios de Error**

* **Falta de Reactivo en Lista:** Si el usuario usa algo que no está en el inventario, el sistema debe permitir añadirlo "al vuelo" para no bloquear la investigación.  
* **Falla de IA:** El sistema debe funcionar al 100% como cuaderno aunque el motor de IA esté apagado.

## **Requisitos Clave (Must-Haves)**

* **Local-First:** Todo ocurre en la máquina del usuario.  
* **Interoperabilidad:** Exportación a PDF y formato .eln (RO-Crate).  
* **Seguridad:** Hashing SHA-256 para integridad de datos.