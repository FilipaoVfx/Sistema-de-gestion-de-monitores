# Sistema de Gestión de Monitores y Salas de Cómputo (SGMSC)

## Descripción del Proyecto
Una institución educativa requiere desarrollar una base de datos para gestionar la asignación de estudiantes monitores a las salas de cómputo disponibles en el campus. Las salas de cómputo son espacios equipados con computadores que pueden ser utilizados por estudiantes y docentes en horarios determinados. Para garantizar el correcto uso de estos espacios, cada sala debe contar con un monitor responsable durante los horarios de atención. 

El sistema debe permitir almacenar información sobre las salas de cómputo, los usuarios que desempeñan el rol de monitores o admin, los horarios de funcionamiento de las salas, y las asignaciones de monitores a dichos horarios. Además, los monitores pueden necesitar realizar cambios de turno en determinados momentos. Por esta razón, el sistema debe permitir que un monitor registre una solicitud de cambio de turno, indicando quién será el monitor que realizará el reemplazo en ese horario. Estas solicitudes deben quedar registradas en la base de datos para su control y seguimiento.

## Problema que Resuelve
La institución necesita controlar el correcto uso de las salas de cómputo garantizando que cada espacio cuente con un monitor responsable durante sus horarios de atención. Además, se carece de un registro y seguimiento formal cuando los monitores necesitan realizar cambios de turno y buscar reemplazos.

## Usuarios del Sistema
* **Administradores (Admin):** Encargados de la gestión global y supervisión.
* **Estudiantes (Monitores):** Encargados de la custodia y reporte de las salas.

> **Nota:** Aunque estudiantes y docentes usan las salas, los usuarios que interactúan con este sistema en particular son los administradores y los monitores.

## Funcionalidades Principales
* Almacenamiento de información de salas de cómputo.
* Registro de información básica de usuarios (nombre, cédula y rol etc).
* Gestión de horarios de funcionamiento y uso de cada sala.
* Asignación de monitores responsables a horarios específicos en las salas.
* Registro y control de solicitudes de cambio de turno entre monitores.
* **Interfaz de Lenguaje Natural:** Chat interactivo que permite consultar y gestionar la base de datos sin necesidad de usar comandos SQL complejos.

## Innovaciones de Inteligencia Artificial & AI Engineering
Este proyecto ha sido evolucionado de un CRUD tradicional a un **Agente Inteligente Agéntico**, implementando tecnologías de vanguardia en el área de IA:

### Arquitectura RAG (Retrieval-Augmented Generation)
El sistema utiliza RAG para fundamentar las respuestas de la IA directamente en los datos de la base de datos relacional. Esto garantiza que la información proporcionada sea veraz, evitando "alucinaciones" y permitiendo consultas complejas sobre el estado de las salas en tiempo real.

### Implementación de Model Context Protocol (MCP)
Hemos dotado al asistente de capacidades de acción mediante herramientas (**Tools**) de ejecución autónoma:
* **Generación de Reportes Analíticos:** Capacidad de entender peticiones de datos y generar automáticamente archivos **Excel (.xlsx)** descargables mediante procesamiento con **Pandas**.
* **Detección Algorítmica de Conflictos:** Verificación matemática de solapamientos de horarios (Overlaps) antes de confirmar cualquier asignación.
* **Búsqueda Difusa (Fuzzy Matching):** Implementación de algoritmos de similitud de texto para corregir automáticamente errores ortográficos del usuario al buscar nombres o salas.

### Seguridad Proactiva y Auditoría
El sistema cuenta con un robusto motor de seguridad:
* **Filtro de Inyección SQL:** Análisis y validación de cada consulta generada por el LLM.
* **Sistema de Alerta de Seguridad:** En caso de detectar intentos de ejecución de comandos destructivos (`DELETE`, `DROP`, `TRUNCATE`), el sistema bloquea la acción y dispara una **alerta por correo electrónico (SMTP)** automática al jefe del departamento con el informe del incidente.

### Memoria Contextual
Implementación de una memoria a corto plazo que permite al chat mantener el hilo de la conversación, facilitando preguntas de seguimiento y una experiencia de usuario fluida.

## Manejo de Restricciones
En la base de datos, cada asesor registrado tendrá el horario del semestre. Esto con el fin de hacer una comparación de horarios de monitoría y horarios de disponibilidad del monitor; de la misma manera se harán las validaciones para las solicitudes de cambio.

## Stack Tecnológico
* **Backend:** Python & Django.
* **Base de Datos:** PostgreSQL + pgvector [Documentacion pgvector](https://github.com/pgvector/pgvector)
* **IA Orchestration:** Google Gemini API & MCP Framework.
* **Data Processing:** Pandas, Openpyxl & RapidFuzz.
* **Seguridad:** SMTPLib & Custom SQL Validators.

## Desarrolladores del Proyecto
* **Juan Andres Muñoz Zapata**
* **Enmanuel Velasquez Romero**
* **Juan Andres Rojas Saavedra**
