# Revision de flujos y funciones del sistema

## Alcance revisado
- [README.md](README.md)
- [sgmsc/urls.py](sgmsc/urls.py)
- [sgmsc/settings.py](sgmsc/settings.py)
- [usuarios/urls.py](usuarios/urls.py)
- [usuarios/views.py](usuarios/views.py)
- [usuarios/models.py](usuarios/models.py)
- [usuarios/forms.py](usuarios/forms.py)
- [asignaciones/urls.py](asignaciones/urls.py)
- [asignaciones/views.py](asignaciones/views.py)
- [asignaciones/services.py](asignaciones/services.py)
- [asignaciones/models.py](asignaciones/models.py)
- [asignaciones/forms.py](asignaciones/forms.py)
- [cambios/urls.py](cambios/urls.py)
- [cambios/views.py](cambios/views.py)
- [cambios/services.py](cambios/services.py)
- [cambios/models.py](cambios/models.py)
- [cambios/forms.py](cambios/forms.py)
- [salas/urls.py](salas/urls.py)
- [salas/views.py](salas/views.py)
- [salas/services.py](salas/services.py)
- [salas/models.py](salas/models.py)
- [horarios/models.py](horarios/models.py)
- [semestres/models.py](semestres/models.py)
- [AI_implementation/ai_orchestrator.py](AI_implementation/ai_orchestrator.py)
- [AI_implementation/mcp_server.py](AI_implementation/mcp_server.py)

## Flujos actuales identificados

### Autenticacion y roles
- Login con email y password, luego router por rol (admin o monitor).
- Dashboard separado para admin y monitor.
- Creacion de monitor desde admin con email de activacion y reset de password.
- Reset de password via flujo estandar de Django.
- Endpoint de chat IA solo para admin (requiere sesion y CSRF).

Archivos clave: [usuarios/views.py](usuarios/views.py), [usuarios/urls.py](usuarios/urls.py), [usuarios/models.py](usuarios/models.py)

### Asignaciones de monitores
- Admin crea asignaciones en una grilla por sala y semestre.
- Se validan conflictos por sala y por monitor (overlaps).
- Se crean horarios faltantes si el bloque no existe aun en la sala.
- La operacion es atomica con validaciones en servicio y modelo.

Archivos clave: [asignaciones/views.py](asignaciones/views.py), [asignaciones/services.py](asignaciones/services.py), [asignaciones/models.py](asignaciones/models.py), [horarios/models.py](horarios/models.py), [semestres/models.py](semestres/models.py)

### Solicitudes de cambio de turno
- Monitor crea solicitud para una de sus asignaciones.
- Admin lista, revisa detalle y aprueba o rechaza.
- Al aprobar, la asignacion cambia de monitor y queda registro en la solicitud.
- Se valida que el reemplazo no tenga conflicto horario.

Archivos clave: [cambios/views.py](cambios/views.py), [cambios/services.py](cambios/services.py), [cambios/models.py](cambios/models.py), [cambios/forms.py](cambios/forms.py)

### Salas (API)
- Endpoints para listar, crear, actualizar y eliminar salas.
- Validaciones de negocio en services (codigo unico, capacidad, etc).

Archivos clave: [salas/urls.py](salas/urls.py), [salas/views.py](salas/views.py), [salas/services.py](salas/services.py)

### IA (RAG + MCP)
- Orquestador Gemini genera SQL de lectura y llama tools MCP.
- Guardado de historial y memoria semantica en Postgres.
- MCP expone tools para consulta, reporte Excel, validacion de conflicto y busqueda difusa.

Archivos clave: [AI_implementation/ai_orchestrator.py](AI_implementation/ai_orchestrator.py), [AI_implementation/mcp_server.py](AI_implementation/mcp_server.py)

## Funciones incompletas o flujos faltantes

1) Modulos de horarios y semestres sin flujo operativo
- [horarios/urls.py](horarios/urls.py), [horarios/views.py](horarios/views.py) y [horarios/services.py](horarios/services.py) estan vacios.
- [semestres/urls.py](semestres/urls.py), [semestres/views.py](semestres/views.py) y [semestres/services.py](semestres/services.py) estan vacios.
- No hay rutas para estos modulos en [sgmsc/urls.py](sgmsc/urls.py).

2) Funciones definidas pero no expuestas en rutas
- En [salas/views.py](salas/views.py) existen funciones listar_salas, crear_sala y obtener_sala, pero no se usan en [salas/urls.py](salas/urls.py).

3) Persistencia de memoria IA sin migraciones visibles
- El orquestador usa tablas `chat_history` y `ai_memory` en [AI_implementation/ai_orchestrator.py](AI_implementation/ai_orchestrator.py), pero no hay un app Django o migraciones en el repo que creen esas tablas. Si no se crean manualmente, el chat fallara o quedara sin historial.

4) Mismatch de requisitos vs implementacion
- El documento de requisitos indica MySQL/XAMPP, pero el proyecto usa PostgreSQL + pgvector en [sgmsc/settings.py](sgmsc/settings.py) y en el orquestador IA. Esto puede ser una inconsistencia de alcance o de documentacion.

## Mejoras recomendadas (priorizadas)

### Seguridad y acceso
- Proteger los endpoints de [salas/views.py](salas/views.py) con autenticacion/rol (admin) y evitar `csrf_exempt` si no es estrictamente necesario.
- Manejar JSON invalido en el endpoint POST de `salas` para evitar errores 500.
- En [AI_implementation/ai_orchestrator.py](AI_implementation/ai_orchestrator.py), la deteccion de intentos destructivos usa palabras muy amplias (ej. "CREAR"); eso puede bloquear solicitudes legitimas como "crear reporte". Ajustar la heuristica para evitar falsos positivos (por ejemplo, detectar solo comandos SQL o verbos con objetos de base de datos).
- En [AI_implementation/mcp_server.py](AI_implementation/mcp_server.py), reforzar validacion para permitir solo una sentencia SELECT/WITH y rechazar multiples sentencias separadas por `;`.

### Completitud funcional
- Implementar CRUD basico para horarios y semestres (listas, creacion, edicion) y agregar rutas en [sgmsc/urls.py](sgmsc/urls.py).
- Definir un flujo claro para "semestre activo" y reflejarlo en vistas de asignaciones y cambios.
- Decidir si las funciones listar/crear/obtener sala se usan como endpoints o se eliminan para evitar duplicidad.

### Confiabilidad y operaciones
- En [horarios/models.py](horarios/models.py) se usa `ExclusionConstraint` con `timerange`, lo que requiere extension `btree_gist` en Postgres; asegurar migracion o paso de setup que la active.
- En [cambios/services.py](cambios/services.py) considerar `select_for_update` en la asignacion al aprobar para evitar carreras si dos admins responden a la misma solicitud en paralelo.
- Agregar tests automatizados para:
  - Conflictos de asignacion y overlaps.
  - Flujo de aprobacion/rechazo de cambios.
  - Endpoints de salas y permisos.

### Mantenibilidad
- Consolidar manejo de errores en servicios (mensajes consistentes, sin exponer excepciones internas en respuestas JSON).
- Documentar en README la dependencia real de Postgres/pgvector para evitar confusion con los requisitos funcionales y RNF.

## Resumen ejecutivo
- Los flujos principales (login, asignaciones, solicitudes de cambio, salas y chat IA) estan implementados.
- Hay modulos clave (horarios y semestres) sin rutas ni vistas, y funciones sueltas en salas no expuestas.
- Se recomienda cerrar los gaps de seguridad (auth/CSRF) y de infraestructura (tablas de memoria IA y extension Postgres), y alinear la documentacion de requisitos con la implementacion actual.
