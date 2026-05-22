# Análisis de Revisión del Sistema

> **Proyecto:** Sistema de Gestión de Monitores (SGMS)
> **Fecha:** 22/05/2026

---

## Resumen Ejecutivo

El proyecto es una aplicación **Django 6.0 + React (Vite + TypeScript)** para gestionar monitores de salas de cómputo. El backend está mayormente completo para flujos renderizados del lado del servidor (asignaciones, cambios, usuarios, salas), pero el **frontend SPA no puede funcionar plenamente** debido a que los endpoints REST API que espera no existen o están incompletos.

---

## 1. Estado por Módulo

### 1.1 `sgmsc/` — Configuración del Proyecto

| Aspecto | Estado |
|---------|--------|
| Settings | ✅ Completo |
| URL routing | ⚠️ `horarios` y `semestres` no están incluidos |
| Deployment (Render) | ✅ Configurado |

### 1.2 `usuarios/` — Autenticación y Usuarios

| Aspecto | Estado |
|---------|--------|
| Modelo `Usuario` | ✅ Completo |
| Login/Logout | ✅ Completo |
| Password Reset | ✅ Completo (con mitigación de Host Header Injection) |
| Crear monitores (admin) | ✅ Completo |
| Dashboard Admin | ✅ Completo (server-rendered) |
| Dashboard Monitor | ✅ Completo (server-rendered) |
| AI Chat API | ✅ Completo |
| `services.py` | ❌ **VACÍO** |
| `tests.py` | ❌ **Placeholder** |

### 1.3 `salas/` — Gestión de Salas

| Aspecto | Estado |
|---------|--------|
| Modelo `Sala` | ✅ Completo |
| Servicios CRUD | ✅ Completo |
| API REST JSON | ✅ Implementada |
| Tests | ❌ **Placeholder** |
| **Autenticación** | ❌ **CRÍTICO: Sin protección** |

### 1.4 `horarios/` — Bloques de Horario

| Aspecto | Estado |
|---------|--------|
| Modelo `Horario` (con exclusión de overlap) | ✅ Completo |
| `views.py` | ❌ **Placeholder vacío** |
| `services.py` | ❌ **VACÍO** |
| `urls.py` | ❌ **VACÍO** |
| `tests.py` | ❌ **Placeholder** |
| API endpoints | ❌ **NO EXISTEN** |

### 1.5 `semestres/` — Semestres Académicos

| Aspecto | Estado |
|---------|--------|
| Modelo `Semestre` (con constraints) | ✅ Completo |
| `views.py` | ❌ **Placeholder vacío** |
| `services.py` | ❌ **VACÍO** |
| `urls.py` | ❌ **VACÍO** |
| `tests.py` | ❌ **Placeholder** |
| API endpoints | ❌ **NO EXISTEN** |

### 1.6 `asignaciones/` — Asignaciones Monitor-Sala

| Aspecto | Estado |
|---------|--------|
| Modelo `Asignacion` | ✅ Completo |
| Bulk creation atómica | ✅ Completo |
| Vista grid server-rendered | ✅ Completo |
| Tests (`services.py`) | ✅ 4 casos |
| API REST para frontend | ❌ **NO EXISTEN** |
| N+1 queries en grid | ⚠️ Potencial mejora |

### 1.7 `cambios/` — Solicitudes de Cambio de Turno

| Aspecto | Estado |
|---------|--------|
| Modelo `SolicitudCambio` | ✅ Completo |
| Flujo crear/aprobar/rechazar | ✅ Completo |
| Vistas CRUD | ✅ Completo |
| Tests | ✅ 8 casos |
| Admin personalizado | ✅ Completo |

### 1.8 `AI_implementation/` — Asistente IA

| Aspecto | Estado |
|---------|--------|
| Orquestador Gemini | ✅ Completo (642 líneas) |
| Servidor MCP con 4 tools | ✅ Completo |
| Memoria corto plazo + semántica | ✅ Completo |
| Detección de SQL injection | ✅ Implementado |
| Alertas por email | ✅ Implementado |
| Generación de reportes Excel | ✅ Implementado |

### 1.9 `frontend/` — React SPA

| Aspecto | Estado |
|---------|--------|
| Login | ✅ Completo |
| Dashboard | ⚠️ Sin datos reales del backend |
| Salas CRUD | ✅ Completo (consume API de salas) |
| Monitores CRUD | ⚠️ API backend no existe |
| Horarios CRUD | ❌ API backend no existe |
| Asignaciones CRUD | ⚠️ API backend no existe |
| Solicitudes de Cambio | ⚠️ API backend no existe |
| Types/Interfaces | ❌ **No coinciden con modelos reales** |

---

## 2. Problemas Críticos de Seguridad

| # | Problema | Archivo | Gravedad |
|---|----------|---------|----------|
| 1 | **Sin autenticación en vistas de salas** | `salas/views.py` | 🔴 CRÍTICO |
| 2 | **Frontend usa Token Auth pero backend no lo implementa** | `frontend/src/api/client.ts` + backend | 🔴 CRÍTICO |
| 3 | `SECRET_KEY` hardcodeada como fallback inseguro | `sgmsc/settings.py:19` | 🟡 ALTO |
| 4 | **URL de producción no coincide** (frontend apunta a URL incorrecta) | `frontend/src/api/client.ts:16` | 🟡 ALTO |
| 5 | SQL arbitrario vía IA (con validación parcial) | `AI_implementation/mcp_server.py` | 🟡 MEDIO |
| 6 | Token en localStorage (vulnerable a XSS) | `frontend/src/context/AuthContext.tsx` | 🟡 MEDIO |
| 7 | `csrf_exempt` en endpoints de salas sin autenticación | `salas/views.py` | 🟡 MEDIO |

---

## 3. Funcionalidades Incompletas

### 3.1 Backend — Código faltante

| Archivo | Problema |
|---------|----------|
| `horarios/views.py` | Solo tiene `from django.shortcuts import render` |
| `horarios/services.py` | Archivo completamente vacío |
| `horarios/urls.py` | Archivo completamente vacío |
| `semestres/views.py` | Solo tiene `from django.shortcuts import render` |
| `semestres/services.py` | Archivo completamente vacío |
| `semestres/urls.py` | Archivo completamente vacío |
| `usuarios/services.py` | Archivo completamente vacío |
| `sgmsc/urls.py` | Faltan includes de `horarios/` y `semestres/` |

### 3.2 Backend — Tests faltantes

| Archivo | Problema |
|---------|----------|
| `usuarios/tests.py` | Solo `# Create your tests here.` |
| `salas/tests.py` | Solo `# Create your tests here.` |
| `horarios/tests.py` | Solo `# Create your tests here.` |
| `semestres/tests.py` | Solo `# Create your tests here.` |

### 3.3 Frontend — APIs que no existen en backend

| Frontend llama a... | Estado en backend |
|--------------------|-------------------|
| `/api/horarios/` | ❌ No existe |
| `/api/semestres/` | ❌ No existe |
| `/api/asignaciones/` | ❌ No existe (solo existe ruta server-rendered) |
| `/api/usuarios/` (monitores) | ❌ No existe (solo vistas server-rendered) |
| `/api/dashboard/` | ❌ No existe |
| `/api/solicitudes-cambio/` | ❌ No existe (solo vistas server-rendered) |

### 3.4 Frontend — Types desalineados con backend

| Archivo TypeScript | Campo incorrecto | Modelo real |
|--------------------|-------------------|-------------|
| `sala.types.ts` | `descripcion`, `activa`, `monitor_actual` | No existen en `Sala` |
| `asignacion.types.ts` | `fecha_inicio`, `fecha_fin`, `notas` | No existen en `Asignacion` |
| `monitor.types.ts` | `activo`, `fecha_registro` | No existen en `Usuario` |
| `horario.types.ts` | `materia`, `grupo`, `docente` | No existen en `Horario` |
| `cambio.types.ts` | `motivo_rechazo`, `fecha_respuesta` | No existen en `SolicitudCambio` |

---

## 4. Bugs Encontrados

| # | Bug | Archivo | Línea |
|---|-----|---------|-------|
| 1 | URL de Render incorrecta en frontend | `frontend/src/api/client.ts` | 16 |
| 2 | `logout()` sin `await` en Sidebar | `frontend/src/components/layout/Sidebar.tsx` | 66 |
| 3 | `save()` con parámetro `validate` no estándar rompe compatibilidad | `horarios/models.py`, `asignaciones/models.py`, `cambios/models.py` | Varias |
| 4 | `Horario.DIAS` accedido como atributo de clase frágil | `asignaciones/views.py` | 106 |
| 5 | `select_for_update()` innecesario y sin uso del resultado | `asignaciones/services.py` | 175 |
| 6 | Validación redundante de `clean_horarios` vs `clean` | `asignaciones/forms.py` | 105-108 |
| 7 | `self.monitor` puede ser `None` en `cambios/forms.py` | `cambios/forms.py` | 46 |
| 8 | Conexiones directas a DB en AI module (no usa pool/ORM) | `AI_implementation/ai_orchestrator.py` | Varias |
| 9 | `as` assertion sin validación runtime en frontend | `frontend/src/pages/SolicitudesCambioPage.tsx` | 103 |
| 10 | DashboardPage asume estructura de datos incorrecta | `frontend/src/pages/DashboardPage.tsx` | - |

---

## 5. Mejoras Potenciales

### 5.1 Backend

| # | Mejora | Prioridad |
|---|--------|-----------|
| 1 | **Implementar REST API con DRF** para todos los módulos | Alta |
| 2 | **Agregar autenticación** a `salas/views.py` | Alta |
| 3 | **Implementar CRUD de horarios** (views, services, urls) | Alta |
| 4 | **Implementar CRUD de semestres** (views, services, urls) | Alta |
| 5 | **Agregar `django-cors-headers`** para producción con Vercel | Alta |
| 6 | **Unificar conexiones DB en AI module** (usar Django ORM) | Media |
| 7 | **Centralizar manejo de auth** (sesión vs token, elegir uno) | Media |
| 8 | **Agregar rate limiting** al AI Chat API | Media |
| 9 | **Usar tareas asíncronas (Celery)** para generación de reportes Excel y envío de emails | Media |
| 10 | **Separar `ai_orchestrator.py`** en módulos más pequeños | Baja |
| 11 | **Agregar logging estructurado** a todos los módulos | Baja |
| 12 | **Completar tests unitarios** para módulos faltantes | Alta |
| 13 | **Optimizar N+1 queries** en grid de asignaciones | Media |

### 5.2 Frontend

| # | Mejora | Prioridad |
|---|--------|-----------|
| 1 | **Alinear TypeScript types** con los modelos reales del backend | Alta |
| 2 | **Corregir URL de producción** en `client.ts` | Alta |
| 3 | **Agregar `await` a `logout()`** | Alta |
| 4 | **Agregar estados de loading/error** consistentes en todas las páginas | Media |
| 5 | **Agregar validación de formularios** client-side | Media |
| 6 | **Usar variables de entorno** para URLs de API | Media |
| 7 | **Manejar errores de red** globalmente | Baja |
| 8 | **Implementar paginación** en listas grandes | Baja |

### 5.3 Arquitectura

| # | Mejora | Prioridad |
|---|--------|-----------|
| 1 | **Adoptar Django REST Framework** para toda la API | Alta |
| 2 | **Definir estrategia de autenticación unificada** (JWT recomendado) | Alta |
| 3 | **Agregar documentación de API** (Swagger/DRF Browsable API) | Media |
| 4 | **Implementar CI/CD** con GitHub Actions | Media |
| 5 | **Configurar entorno de staging** para pruebas | Baja |

---

## 6. Flujos Completos vs Incompletos

```
Autenticación (Login/Logout/Password Reset)     ████████████ 100%
Dashboard Admin (server-rendered)                ████████████ 100%
Dashboard Monitor (server-rendered)              ████████████ 100%
Crear Monitores (admin)                          ████████████ 100%
AI Chat                                          ████████████ 100%
Salas CRUD (backend API)                         ████████████ 100%
Cambios de Turno (full stack)                    ████████████ 100%
Asignaciones (server-rendered)                   ████████████ 100%
────────────────────────────────────────────────────────────
Salas (frontend CRUD)                            ██████████░░  80%
────────────────────────────────────────────────────────────
Horarios (backend model only)                    ██░░░░░░░░░░  20%
Semestres (backend model only)                   ██░░░░░░░░░░  20%
Horarios (frontend)                              ██████░░░░░░  60%
────────────────────────────────────────────────────────────
Dashboard API endpoint                           ░░░░░░░░░░░░   0%
Monitores API endpoint                           ░░░░░░░░░░░░   0%
Asignaciones API endpoint                        ░░░░░░░░░░░░   0%
Solicitudes Cambio API endpoint                  ░░░░░░░░░░░░   0%
Semestres API endpoint                           ░░░░░░░░░░░░   0%
Horarios API endpoint                            ░░░░░░░░░░░░   0%
Frontend Types alineados                         ░░░░░░░░░░░░   0%
Tests (horarios, semestres, salas, usuarios)      ░░░░░░░░░░░░   0%
```

---

## 7. Conclusión

El sistema tiene una **base sólida** con módulos bien implementados como autenticación, cambios de turno, asignaciones, y el asistente IA. Sin embargo, **el frontend React no puede funcionar** porque:

1. **No hay APIs REST** — el backend usa vistas server-rendered, pero el frontend espera endpoints `/api/*`
2. **`horarios` y `semestres`** tienen los modelos pero ningún API, vista o URL implementada
3. **`salas` no tiene autenticación** — cualquier persona puede crear/editar/eliminar salas
4. **Los types de TypeScript** no coinciden con los modelos reales

**Recomendación principal:** Implementar Django REST Framework para crear una API unificada que el frontend pueda consumir, agregar autenticación a salas, y completar los módulos de horarios y semestres.



## 8. Mejoras Detectadas por el Usuario

### 8.1 Logo / Favicon — Pantalla de carga

| Aspecto | Detalle |
|---------|---------|
| Estado actual | frontend/index.html:5 referencia <link rel=icon type=image/svg+xml href=/favicon.svg> pero el archivo **no existe**. Al abrir localhost se ve el icono generico de Vite/Django. |
| Archivos afectados | frontend/index.html, frontend/public/favicon.svg (no existe) |
| Propuesta | Crear un SVG con el logo del sistema (SGMSC) y colocarlo como favicon. Tambien agregar meta tag para color de tema y logo en pantalla de carga. |

### 8.2 Mensaje de confirmacion al eliminar

| Aspecto | Detalle |
|---------|---------|
| Estado actual | Se usa confirm() de JS nativo en 3 paginas: SalasPage.tsx:73, HorariosPage.tsx:69, AsignacionesPage.tsx:115. El confirm() nativo se ve basico y no sigue el diseno del sistema. |
| Archivos afectados | frontend/src/pages/SalasPage.tsx, HorariosPage.tsx, AsignacionesPage.tsx |
| Propuesta | Crear un componente ConfirmDialog reutilizable que use el Modal.tsx existente, con titulo personalizable, mensaje, botones de confirmar/cancelar estilizados. Reemplazar todos los confirm() con este componente. |

### 8.3 Monitores — Modificar informacion

| Aspecto | Detalle |
|---------|---------|
| Estado actual | MonitoresPage.tsx solo permite **crear** monitores. No hay boton de editar, no se puede cambiar email, telefono, nombre, apellido. La columna Estado siempre muestra Badge verde > Activo fijo. No hay forma de **desactivar** un monitor. monitores.api.ts no tiene metodo update(). |
| Archivos afectados | frontend/src/pages/MonitoresPage.tsx, frontend/src/api/monitores.api.ts, backend usuarios/views.py (no hay endpoint de actualizacion), usuarios/models.py |
| Propuesta | 1) Agregar boton de editar en cada fila. 2) Agregar endpoint PUT /api/usuarios/{id}/ en backend. 3) Modificar modal de creacion para que sirva tambien como edicion. 4) Agregar campo is_active (AbstractUser ya lo tiene) y mostrar Badge segun estado. 5) Agregar opcion para desactivar/reactivar monitor. |

### 8.4 Filtros visualmente basicos

| Aspecto | Detalle |
|---------|---------|
| Estado actual | Los filtros son <select> simples. HorariosPage.tsx:97-109 tiene un solo select de sala. AsignacionesPage.tsx:149-161 tiene un solo select de semestre. No hay busqueda, ni filtros combinados, ni etiquetas visuales de filtros activos. |
| Archivos afectados | frontend/src/pages/HorariosPage.tsx, AsignacionesPage.tsx, MonitoresPage.tsx, SolicitudesCambioPage.tsx |
| Propuesta | 1) Input de busqueda textual con debounce. 2) Mejorar diseno de selects. 3) Badges/filtros activos que se puedan quitar. 4) Unificar en componente FilterBar reutilizable. 5) Filtro por rango de fechas donde aplique. |

### 8.5 Formularios de ingreso de datos basicos

| Aspecto | Detalle |
|---------|---------|
| Estado actual | Todos los modales usan inputs simples sin validacion visual inline, sin grupos/secciones, sin autocomplete. Ej: MonitoresPage.tsx:142-155 inputs sueltos, SalasPage.tsx:154-183 solo 3 inputs. Sin retroalimentacion visual de errores. |
| Archivos afectados | Todas las paginas con modales de formulario |
| Propuesta | 1) Validacion inline con mensajes de error debajo de cada campo. 2) Agrupar campos en secciones con subtitulos. 3) Tooltips de ayuda. 4) Componente FormField reutilizable con label, input, error state. 5) Indicadores de campo requerido. |

### 8.6 Horarios — Sin opcion de modificar

| Aspecto | Detalle |
|---------|---------|
| Estado actual | HorariosPage.tsx solo tiene boton para **eliminar** (trash, linea 133). Sin boton de editar ni handleEdit(). Sin embargo horarios.api.ts:17 ya tiene update() implementado. El modal de creacion no se reutiliza para edicion. |
| Archivos afectados | frontend/src/pages/HorariosPage.tsx:68-77 (solo delete) |
| Propuesta | 1) Boton de editar (lapiz) en cada fila. 2) Funcion handleEdit() que cargue datos en el modal. 3) Diferenciar modo creacion/edicion en el modal. 4) API update() ya listo. |

### 8.7 Asignaciones — Sin consulta de disponibilidad previa

| Aspecto | Detalle |
|---------|---------|
| Estado actual | AsignacionesPage.tsx:73-86 carga horarios solo por sala, pero **no verifica si el monitor ya tiene asignaciones en esos horarios**. El usuario elige monitor, sala y horarios a ciegas. La validacion de conflicto solo ocurre al confirmar en el backend. |
| Archivos afectados | frontend/src/pages/AsignacionesPage.tsx:73-92, backend asignaciones/services.py |
| Propuesta | 1) Al seleccionar monitor+sala, consultar asignaciones existentes del monitor. 2) Marcar visualmente (gris/deshabilitado) horarios ocupados. 3) Mostrar advertencia si hay conflicto. 4) Endpoint GET /api/asignaciones/check-disponibilidad/ para consulta rapida. |

### 8.8 Perfil de usuario — Sin opcion de modificar

| Aspecto | Detalle |
|---------|---------|
| Estado actual | No existe pagina, modal o ruta para editar perfil propio. Sidebar.tsx:54-63 solo muestra nombre e iniciales. Sin forma de cambiar nombre, apellido, telefono, email o contrasena. Backend tiene password reset pero no endpoint de perfil. |
| Archivos afectados | Sidebar.tsx, Topbar.tsx, usuarios/views.py, usuarios/urls.py |
| Propuesta | 1) Opcion Mi Perfil en sidebar. 2) Modal con formulario para editar nombre, apellido, telefono, email. 3) Seccion para cambiar contrasena. 4) Endpoints GET/PUT /api/auth/perfil/ en backend. 5) Mostrar asignaciones actuales del monitor. |

---

## 9. Priorizacion de Mejoras

| Prioridad | Mejora | Esfuerzo estimado | Impacto |
|-----------|--------|-------------------|---------|
| 🔴 Alta | 8.3 Monitores — editar y desactivar | Medio | Alto |
| 🔴 Alta | 8.6 Horarios — boton de editar | Bajo | Alto |
| 🔴 Alta | 8.8 Perfil de usuario | Medio | Alto |
| 🟡 Media | 8.2 Confirmacion personalizada al eliminar | Bajo | Medio |
| 🟡 Media | 8.7 Asignaciones — disponibilidad previa | Medio | Alto |
| 🟡 Media | 8.5 Formularios mejorados | Medio | Medio |
| 🟢 Baja | 8.1 Logo / Favicon | Bajo | Bajo |
| 🟢 Baja | 8.4 Filtros visuales mejorados | Medio | Medio |
