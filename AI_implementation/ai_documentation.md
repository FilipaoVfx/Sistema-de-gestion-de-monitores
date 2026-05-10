# Documentación Completa: Módulos y Procesos de AI_implementation

## Tabla de Contenidos
1. [mcp_server.py](#1-mcp_serverpython)
2. [prompts.py](#2-promptspy)
3. [ai_orchestrator.py](#3-ai_orchestratorpy)
4. [Flujo General](#4-flujo-general-de-ejecución)

---

## 1. mcp_server.py

### Descripción General
`mcp_server.py` es un servidor **Model Context Protocol (MCP)** que expone un kit de tools vía stdio. Su función es actuar como intermediario seguro entre el modelo Gemini y la base de datos PostgreSQL, y además generar reportes Excel y validaciones auxiliares.

**Propósito:**
- Ejecutar consultas SQL solo de lectura (SELECT) de forma segura
- Validar que NO se intenten operaciones peligrosas (INSERT, UPDATE, DELETE, etc.)
- Proporcionar resultados JSON para que el orquestador pueda encadenar tools
- Generar archivos Excel en `media/reports/`
- Verificar conflictos de horario y hacer búsquedas difusas
- Mantener aislado el acceso directo a la base de datos

---

### Función 1: `_build_database_url_from_parts()`

**Firma:**
```python
def _build_database_url_from_parts() -> str | None:
```

**Parámetros:** Ninguno (obtiene variables del archivo `.env`)

**Obtiene del entorno:**
- `DB_NAME`: Nombre de la base de datos
- `DB_USER`: Usuario de PostgreSQL
- `DB_PASSWORD`: Contraseña de PostgreSQL
- `DB_HOST`: Host/IP del servidor
- `DB_PORT`: Puerto de conexión

**Retorna:**
- `str`: URL completa formato `postgresql://user:password@host:port/dbname`
- `None`: Si falta alguna variable

**Lógica:**
1. Lee las 5 variables de entorno
2. Si alguna falta, retorna `None`
3. URL-encoda usuario y contraseña con `quote_plus()` - CRÍTICO para caracteres especiales (@, :, /, %)
4. Construye URL PostgreSQL estándar

**Importancia:** Sin URL-encoding, contraseñas con caracteres especiales rompen la conexión.

---

### Función 2: `consultar_base_datos(sql_query: str) -> str`

**Firma:**
```python
@mcp.tool()
def consultar_base_datos(sql_query: str) -> str:
```

**Parámetro:**
- `sql_query` (str): La consulta SQL generada por Gemini

**Retorna:**
- `str`: JSON con `columns`, `rows` y `row_count`, o un JSON de error

**Lógica Interna:**

1. **Validación de Configuración (líneas 57-60):**
   - Verifica que `DATABASE_URL` existe
   - Si no, devuelve error de configuración

2. **Validación de Seguridad (líneas 63-65):**
   - Busca palabras prohibidas: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`
   - Si encuentra alguna, rechaza con mensaje de error
   - CRÍTICO: Primera línea de defensa contra manipulaciones

3. **Conexión a PostgreSQL (línea 70):**
   - Usa `psycopg2.connect(DATABASE_URL)`

4. **Ejecución de Consulta (líneas 74-80):**
   - Ejecuta SQL
   - Obtiene resultados
   - Extrae nombres de columnas para contexto del LLM

5. **Formateo de Respuesta (líneas 85-90):**
    - Devuelve un objeto JSON con:
      - `columns`
      - `rows`
      - `row_count`

6. **Manejo de Errores:**
    - Error SQL: Captura y devuelve para que Gemini corrija
    - Error Inesperado: Devuelve mensaje
    - Finally: Siempre cierra conexión

---

### Función 3: `generate_excel_report(data_json: str, report_name: str = "reporte")`

**Propósito:** Generar un archivo `.xlsx` a partir de filas JSON.

**Puntos clave:**
- Espera un JSON con `rows` o una lista de diccionarios
- Guarda el archivo en `media/reports/`
- Ajusta el ancho de columnas con `openpyxl`
- Retorna una URL web absoluta en localhost en formato Markdown clicable

**Retorno típico:**
`Archivo generado con éxito. Aquí tienes el enlace: [Descargar Informe Excel](http://localhost:8000/media/reports/archivo.xlsx)`

---

### Función 4: `verificar_conflicto_horario(...)`

**Propósito:** Validar cruces de horario antes de confirmar asignaciones.

**Notas:**
- Usa ORM de Django con `sync_to_async`
- Devuelve texto de conflicto o confirmación de sala libre

---

### Función 5: `busqueda_difusa_nombres(entidad, termino_busqueda)`

**Propósito:** Buscar coincidencias aproximadas de monitores o salas.

**Notas:**
- Soporta `entidad = "monitor"` o `"sala"`
- Usa `difflib` para aproximación
- Devuelve posibles coincidencias con el ID sugerido

---

## 2. prompts.py

### Descripción General
`prompts.py` contiene el **system prompt** que define comportamiento y límites del modelo Gemini.

---

### SYSTEM_PROMPT_MONITORES

**Propósito:** Contexto completo para que LLM genere SQL correcto y respuestas coherentes.

**Estructura:**

#### Parte 1: Rol (líneas 3-5)
- Identifica al asistente como exclusivo del Administrador del Sistema

#### Parte 2: Reglas Críticas (líneas 7-10)
1. **SOLO SELECT** - Sin INSERT/UPDATE/DELETE
2. **NUNCA inventes tablas** - Solo esquema documentado
3. **Ignora tablas Django** - auth_*, django_*

#### Parte 3: Esquema de Base de Datos (líneas 12-57)

Define 6 tablas:

**1. Tabla `usuarios_usuario`**
- Propósito: Todos los usuarios del sistema
- Columnas: id, username, first_name, last_name, cedula, rol, telefono, email, is_active

**2. Tabla `sala`**
- Propósito: Laboratorios y aulas
- Columnas: id_sala, codigo, nombre, capacidad

**3. Tabla `semestre`**
- Propósito: Períodos académicos
- Columnas: id_semestre, anio, periodo, activo

**4. Tabla `horarios_horario`**
- Propósito: Bloques de tiempo en salas
- Columnas: id_horario, dia_semana, hora_inicio, hora_fin, sala_id (FK)

**5. Tabla `asignaciones_asignacion`**
- Propósito: Monitores asignados a horarios
- Columnas: id_asignacion, fecha_creacion, horario_id, monitor_id, semestre_id

**6. Tabla `ai_memory`**
- Propósito: Conversaciones previas (memoria semántica)
- Columnas: id, session, user_query, ai_response, embeddings (pgvector), created_at

#### Parte 4: JOINs Recomendados (líneas 60-67)
Ejemplos de cómo conectar tablas para preguntas complejas.

#### Parte 5: Reglas de Oro (líneas 71-75)
1. **Usar PKs:** Si tienes el ID, úsalo en lugar de nombres
2. **Autonomía:** Si consulta devuelve vacío, reintentar
3. **No mostrar SQL:** Respuestas naturales
4. **ILIKE:** Para búsquedas case-insensitive

---

## 3. ai_orchestrator.py

### Descripción General
Orquestador central que coordina TODO el flujo de generación de respuestas.
Ahora también detecta intención destructiva antes de planificar SQL y puede encadenar tools MCP según la necesidad del usuario.

---

### Función: `_recuperar_memoria_corto_plazo_sync(session_id: str) -> str`

**Propósito:** Recuperar conversaciones de los últimos 5 minutos para contexto temporal.

**Parámetro:** `session_id` - Username del administrador

**Retorna:** String formateado con últimos 5 min, o vacío si error

**Lógica:**
1. Conecta a BD
2. Consulta `chat_history`:
   - Filtra por `session_id` (admin actual)
   - Filtra por `created_at >= ahora - 5 minutos`
3. Ordena cronológicamente
4. Formatea: `"Usuario: pregunta\nAsistente: respuesta\n"`
5. Si hay error, retorna vacío (best-effort)

**Cuándo se usa:** Antes de generar SQL para contexto reciente en el prompt.

---

### Función: `_guardar_en_historial_sync(session_id, user_message, ai_response)`

**Propósito:** Persistir cada interacción en la base de datos.

**Parámetros:**
- `session_id`: Username del admin
- `user_message`: Pregunta del usuario
- `ai_response`: Respuesta del asistente

**Lógica:**
1. Conecta a BD
2. INSERT en `chat_history` con `timezone.now()`
3. Commit
4. Cierra conexión
5. Si falla, simplemente devuelve (no rompe el chat)

---

### Función: `buscar_memoria_relevante(query_texto: str, session_id: str) -> str`

**Propósito:** Buscar conversaciones previas semánticamente similares (pgvector).

**Parámetros:**
- `query_texto`: Pregunta actual del usuario
- `session_id`: Username del admin

**Lógica:**
1. Genera embedding de la pregunta
2. Busca en `ai_memory` vectores similares usando pgvector
3. Retorna respuestas previas temáticamente relacionadas
4. Best-effort: Si pgvector no existe, retorna vacío

**Diferencia con memoria corto plazo:**
- **Corto plazo:** Contexto temporal muy reciente (últimos 5 minutos)
- **Semántica:** Conversaciones antiguas pero temáticamente similar

---

### Función: `guardar_en_memoria(user_message, ai_response, session_id)`

**Propósito:** Guardar embeddings para búsqueda semántica futura.

**Lógica:**
1. Genera embedding de `user_message`
2. Genera embedding de `ai_response`
3. INSERT en `ai_memory` con timestamp
4. Best-effort: Si pgvector no disponible, falla silenciosamente

---

### Función Principal: `async def get_ai_response(user_message: str, session_id: str = "default") -> str`

**Propósito:** Orquesta TODO el proceso de generación de respuesta.

**Flujo de 10 Pasos:**

**PASO 1: Recuperar Memoria Corto Plazo**
- Usa `sync_to_async` para ejecutar función sincrónica en contexto async
- Obtiene últimos 5 minutos de `chat_history`

**PASO 2: Recuperar Memoria Semántica**
- Llama `buscar_memoria_relevante()`
- Busca conversaciones temáticamente similares

**PASO 3: Construir Prompt Enriquecido**
- Inyecta memoria en tags XML:
```
<MEMORIA RECIENTE (Últimos 5 minutos - PRIORIDAD MÁXIMA)>
Usuario: pregunta anterior
Asistente: respuesta anterior
</MEMORIA RECIENTE>

<PREGUNTA ACTUAL>
Nueva pregunta del usuario
</PREGUNTA ACTUAL>
```

**PASO 4: Generar plan con Gemini**
- Envía prompt + memoria a Gemini
- El modelo responde con JSON estructurado
- Puede devolver SQL o una tool MCP a ejecutar

**PASO 5: Validar intención y SQL**
- Si el mensaje ya expresa intención destructiva, se bloquea y se envía alerta por correo
- Si hay SQL, se valida que sea SELECT y que no sea peligrosa

**PASO 6: Ejecutar tool MCP**
- Inicia proceso `mcp_server.py`
- Puede llamar `consultar_base_datos`, `generate_excel_report`, `verificar_conflicto_horario` o `busqueda_difusa_nombres`
- Recibe JSON o URL del recurso generado

**PASO 7: Construir Prompt para Respuesta Final**
- Prepara nuevo prompt para redacción natural
- Inyecta NUEVAMENTE la memoria
- Incluye resultados de tools y, si aplica, el enlace del Excel

**PASO 8: Llamar a Gemini para Redactar**
- Envía prompt con contexto completo
- Gemini redacta respuesta natural y coherente

**PASO 9: Guardar Interacción**
- INSERT en `chat_history` (memoria corto plazo)
- INSERT en `ai_memory` (memoria semántica con embeddings)

**PASO 10: Devolver Respuesta**
- Devuelve string al usuario

---

### Conceptos Clave

#### Async/Await y sync_to_async
- `get_ai_response` es **async** (Django 4.1+ soporta async views)
- Consultas a BD con `psycopg2` son **síncronas** (bloquean el hilo)
- `sync_to_async` convierte función sincrónica en awaitable seguro
- Previene: `RuntimeError: no running event loop`

#### Inyección de Memoria en 2 Puntos
1. **Planner Prompt (PASO 4):** Gemini usa memoria para generar SQL correcta
2. **Final Prompt (PASO 7):** Gemini usa memoria para redactar respuesta coherente

Esto asegura que el contexto se utiliza en AMBAS fases del razonamiento.

#### Best-Effort Philosophy
- Si `chat_history` no existe → devuelve vacío, chat sigue funcionando
- Si `pgvector` no instalado → memoria semántica falla silenciosamente
- Prioridad: el chat NUNCA se rompe por falta de memoria

#### Alertas y seguridad
- Si el usuario intenta borrar o modificar datos, se bloquea antes de generar SQL
- Se envía correo al jefe de departamento con el intento registrado

#### Media en desarrollo
- `sgmsc/urls.py` expone `MEDIA_URL` cuando `DEBUG=True`
- Esto permite descargar reportes desde `http://localhost:8000/media/...`

---

## 4. Flujo General de Ejecución

### Diagrama Completo

```
1. Usuario escribe en chat widget
    ↓
2. POST a /administrador/chat-api/ con mensaje
    ↓
3. Vista Django: chat_api_view(request)
    ↓
4. Llama: get_ai_response(user_msg, session_id=request.user.username)
    ↓
5. Paso 1: Recupera memoria 5 min
    ├─ SELECT FROM chat_history WHERE session_id=? AND created_at >= ahora-5min
    └─ Retorna: "Usuario: ¿X?\nAsistente: Y\n..."
    ↓
6. Paso 2: Recupera memoria semántica (pgvector)
    ├─ Genera embedding
    └─ Busca similares en ai_memory
    ↓
7. Paso 3: Construye prompt con memoria inyectada
    ├─ <MEMORIA RECIENTE>...</MEMORIA RECIENTE>
    └─ <PREGUNTA ACTUAL>Nueva pregunta</PREGUNTA ACTUAL>
    ↓
8. Paso 4: Llamando a Gemini para SQL
    ├─ Envía: System prompt + Memoria + Pregunta
    └─ Recibe: {"sql_query": "SELECT ..."}
    ↓
9. Paso 5: Valida SQL (¿SELECT? ¿Sintaxis?)
    ↓
10. Paso 6: Ejecuta SQL vía MCP
    ├─ Inicia: mcp_server.py (stdio)
    ├─ Llama: consultar_base_datos / generate_excel_report / otras tools segun el JSON
    ├─ mcp_server valida seguridad
    ├─ Conecta a PostgreSQL
    ├─ Ejecuta consulta
    ├─ Formatea: "Columnas: ...\nResultados: ..."
    └─ Devuelve al orchestrator
    ↓
11. Paso 7: Construye prompt para respuesta natural
    ├─ Inyecta NUEVAMENTE memoria
    ├─ Incluye SQL ejecutada
    └─ Incluye resultados de BD
    ↓
12. Paso 8: Gemini redacta respuesta
    ├─ Lee todo el contexto
    └─ Escribe respuesta coherente
    ↓
13. Paso 9: Guarda interacción
    ├─ INSERT en chat_history
    └─ INSERT en ai_memory (con embeddings)
    ↓
14. Paso 10: Devuelve respuesta
    ↓
15. JSON Response: {"response": "..."}
    ↓
16. JavaScript del widget
    ├─ Añade mensaje del bot al DOM
    ├─ Desactiva indicador "escribiendo..."
    ├─ Scroll al fondo
    └─ Usuario ve respuesta en tiempo real
```

### Interacciones Entre Módulos

```
prompts.py (System Prompt)
    ↓
    └─→ SYSTEM_PROMPT_MONITORES define esquema, reglas, JOINs
        
ai_orchestrator.py
    ├─ Importa: from .prompts import SYSTEM_PROMPT_MONITORES
    ├─ Recupera memoria (corto y largo plazo)
    ├─ Inyecta en prompt
    └─ Llama a mcp_server.py via MCP
        
mcp_server.py
    ├─ Recibe SQL generado por Gemini
    ├─ Valida seguridad (¿es SELECT?)
    ├─ Conecta a PostgreSQL
    ├─ Ejecuta SQL
    └─ Devuelve resultados formateados
        
Vista Django (usuarios/views.py)
    ├─ Llama: get_ai_response(user_msg, session_id=username)
    ├─ Recibe respuesta formateada
    └─ Devuelve JSON al frontend
```

---

## Resumen de Responsabilidades

| Módulo | Responsabilidad Principal |
|--------|--------------------------|
| `mcp_server.py` | Ejecutar SQL de forma segura, validar operaciones, formatear resultados |
| `prompts.py` | Definir comportamiento del LLM, esquema BD, reglas y límites |
| `ai_orchestrator.py` | Orquestar flujo completo: memoria → SQL → respuesta |

---

## Conclusión

Este sistema implementa un asistente de IA seguro, eficiente y contextual:

✅ **Seguridad:** SQL validado en dos niveles (intención + MCP), operaciones de solo lectura, sin acceso directo a BD

✅ **Contexto:** Memoria corto plazo (5 min) para conversación inmediata + memoria semántica (pgvector) para contexto histórico

✅ **Tools:** Router MCP para consultas, Excel, conflictos de horario y búsqueda difusa

✅ **Confiabilidad:** Best-effort error handling, chat nunca se rompe si falla una parte

✅ **Escalabilidad:** Aislamiento completo por sesión (session_id = username del admin)

✅ **Eficiencia:** Inyección de memoria en 2 puntos del razonamiento (SQL generation + response generation)
