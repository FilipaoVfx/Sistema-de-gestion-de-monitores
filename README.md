# Sistema de Gestión de Monitores y Salas de Cómputo (SGMSC)

Plataforma web para administrar las salas de cómputo de una institución educativa: asignación de **monitores** a horarios específicos, control de **turnos** semestrales y gestión de **solicitudes de cambio** entre monitores con un flujo de **swap mixto** moderado por un administrador.

---

## Tabla de contenidos

- [Resumen](#resumen)
- [Stack tecnológico](#stack-tecnológico)
- [Arquitectura general](#arquitectura-general)
- [Modelo de datos](#modelo-de-datos)
- [Roles y permisos](#roles-y-permisos)
- [Funcionalidades por módulo](#funcionalidades-por-módulo)
- [Flujos del sistema](#flujos-del-sistema)
  - [Autenticación JWT](#flujo-autenticación-jwt)
  - [Creación de monitor](#flujo-creación-de-monitor)
  - [Asignación bulk de turnos](#flujo-asignación-bulk-de-turnos)
  - [Solicitud de cambio (swap mixto)](#flujo-solicitud-de-cambio-swap-mixto)
- [Casos de uso](#casos-de-uso)
- [Endpoints REST](#endpoints-rest)
- [Setup local](#setup-local)
- [Despliegue](#despliegue)
- [Seed demo](#seed-demo)
- [Desarrolladores](#desarrolladores)

---

## Resumen

Una institución educativa necesita garantizar que **cada sala de cómputo** tenga un **monitor responsable** durante sus horarios de atención, y que los cambios de turno entre monitores queden registrados con trazabilidad completa.

**El sistema permite:**

1. Administrar **salas** de cómputo (código, nombre, capacidad).
2. Administrar **horarios** por sala (día de la semana + bloque horario).
3. Administrar **semestres** académicos (año + período + activo).
4. Asignar **monitores** (usuarios con rol `monitor`) a horarios específicos dentro de un semestre.
5. Registrar **solicitudes de cambio** de turno con un flujo asistido por el administrador:
   - El monitor solicita cambio
   - El admin propone **2 o más opciones de swap** con otros monitores
   - El monitor solicitante elige cuál opción aceptar
   - El sistema ejecuta el swap atómico (intercambia ambos turnos)
6. Visualizar el cronograma semanal con avatares de monitores por bloque.
7. Autenticación segura con **JWT** (access + refresh con rotación y blacklist).
8. Separación estricta de permisos por rol (`admin` vs `monitor`).

---

## Stack tecnológico

| Capa | Tecnología | Notas |
|---|---|---|
| **Frontend** | React 18 + TypeScript + Vite + Tailwind CSS | SPA con grilla semanal personalizada |
| **Routing** | React Router v6 | Rutas protegidas por rol |
| **HTTP** | Axios con interceptores JWT | Refresh automático en 401 |
| **Backend** | Django 6 + Django REST Framework 3.16 | API JSON pura `/api/*` |
| **Auth** | `djangorestframework-simplejwt` 5.5.1 | Access 1h + Refresh 7d con rotación y blacklist |
| **DB** | PostgreSQL (Supabase) | Pooler en producción para IPv4 |
| **Hosting Frontend** | Vercel | Deploy automático desde `fork/main` |
| **Hosting Backend** | Render | Deploy automático desde `fork/feature/drf-api` |
| **Static Files** | WhiteNoise | Sirve estáticos comprimidos desde Django |
| **CORS** | `django-cors-headers` con regex de `*.vercel.app` | Acepta URLs preview |
| **AI / RAG** | Google Gemini API + MCP Framework + pgvector | Chat de consulta sobre la BD |
| **Data tooling** | Pandas + Openpyxl | Generación de reportes XLSX |

---

## Arquitectura general

```mermaid
graph TB
    subgraph "Cliente"
        BR[Navegador del Usuario<br/>admin / monitor]
    end

    subgraph "Vercel (Frontend)"
        SPA[React SPA<br/>fork/main]
        PROXY["vercel.json proxy<br/>/_api/* → Render"]
    end

    subgraph "Render (Backend)"
        DJ[Django + DRF<br/>fork/feature/drf-api]
        GUN[Gunicorn worker]
        WN[WhiteNoise<br/>static files]
    end

    subgraph "Supabase"
        PG[(PostgreSQL<br/>+ pgvector)]
        POOL[Session Pooler<br/>IPv4]
    end

    subgraph "Servicios externos"
        GEM[Google Gemini API]
        SMTP[Gmail SMTP<br/>opcional]
    end

    BR -->|HTTPS| SPA
    SPA -->|JWT Bearer<br/>requests| PROXY
    PROXY -->|reverse proxy| DJ
    DJ --> GUN
    DJ --> WN
    DJ -->|psycopg2| POOL
    POOL --> PG
    DJ -.->|chat IA| GEM
    DJ -.->|emails| SMTP

    style SPA fill:#3178c6,color:#fff
    style DJ fill:#0c4b33,color:#fff
    style PG fill:#336791,color:#fff
    style GEM fill:#4285f4,color:#fff
```

**Flujo de un request típico:**
1. Usuario en navegador → request a `https://sgmsc-frontend.vercel.app/_api/salas/`
2. Vercel intercepta `/_api/*` y hace reverse proxy a `https://sistema-de-gestion-de-monitores.onrender.com/*`
3. Django valida el JWT con `Authorization: Bearer <access>`, ejecuta la vista, consulta Postgres
4. Respuesta JSON viaja de vuelta por el proxy hasta el SPA
5. **No hay CORS preflight** porque la SPA pega al mismo origen (Vercel)

---

## Modelo de datos

```mermaid
erDiagram
    USUARIO ||--o{ ASIGNACION : "tiene"
    USUARIO ||--o{ SOLICITUD_CAMBIO : "solicita"
    USUARIO ||--o{ SOLICITUD_CAMBIO : "reemplaza"
    USUARIO ||--o{ SOLICITUD_CAMBIO : "responde (admin)"

    SALA ||--o{ HORARIO : "define"
    HORARIO ||--o{ ASIGNACION : "ocupa"
    SEMESTRE ||--o{ ASIGNACION : "vigente_en"

    ASIGNACION ||--o{ SOLICITUD_CAMBIO : "objeto_de"
    ASIGNACION ||--o{ OPCION_CAMBIO : "propuesta_como_swap"
    SOLICITUD_CAMBIO ||--o{ OPCION_CAMBIO : "tiene_opciones"

    USUARIO {
        int id PK
        string email UK "USERNAME_FIELD"
        string username UK
        string cedula UK
        string first_name
        string last_name
        string telefono
        string rol "admin | monitor"
        string password "PBKDF2"
        bool is_active
    }

    SALA {
        int id_sala PK
        string codigo UK "LAB-01..."
        string nombre
        int capacidad
    }

    HORARIO {
        int id_horario PK
        int sala FK
        int dia_semana "1=Lun..6=Sab"
        time hora_inicio
        time hora_fin
    }

    SEMESTRE {
        int id_semestre PK
        int anio
        int periodo "1 | 2"
        bool activo
    }

    ASIGNACION {
        int id_asignacion PK
        int monitor FK
        int horario FK
        int semestre FK
        datetime fecha_creacion
    }

    SOLICITUD_CAMBIO {
        int id_cambio PK
        int asignacion FK
        int solicitante FK "monitor"
        int monitor_reemplazo FK "nullable, se llena al APROBAR"
        int respondido_por FK "admin"
        string tipo "cambio_turno"
        text motivo
        string estado "pendiente | con_propuestas | aprobada | rechazada"
        text respuesta
        datetime fecha_creacion
        datetime fecha_respuesta
    }

    OPCION_CAMBIO {
        int id_opcion PK
        int solicitud FK
        int asignacion_swap FK "asignacion de OTRO monitor"
        int orden
        bool seleccionada
        datetime fecha_creacion
    }
```

### Constraints clave

| Tabla | Constraint | Función |
|---|---|---|
| `ASIGNACION` | `unique(monitor, horario, semestre)` | No duplica el mismo turno |
| `ASIGNACION` | `clean()` valida no-cruce horario | Un monitor no puede tener 2 turnos solapados en el mismo semestre |
| `SOLICITUD_CAMBIO` | `unique(asignacion) WHERE estado='pendiente'` | Una solicitud pendiente a la vez por asignación |
| `OPCION_CAMBIO` | `unique(solicitud, asignacion_swap)` | No se repite la misma opción |
| `OPCION_CAMBIO` | `unique(solicitud) WHERE seleccionada=true` | Solo una opción ganadora |

---

## Roles y permisos

```mermaid
flowchart LR
    subgraph "ADMIN"
        A1[Salas: CRUD]
        A2[Monitores: ver, crear, listar]
        A3[Horarios: CRUD]
        A4[Asignaciones: CRUD bulk + delete]
        A5[Solicitudes: ver todas, proponer, rechazar]
        A6[Semestres: ver todos]
    end
    subgraph "MONITOR"
        M1[Ver SUS asignaciones]
        M2[Ver SUS solicitudes]
        M3[Crear solicitud cambio]
        M4[Elegir opción de swap]
        M5[Ver dashboard personal]
    end

    style A1 fill:#16a34a,color:#fff
    style A2 fill:#16a34a,color:#fff
    style A3 fill:#16a34a,color:#fff
    style A4 fill:#16a34a,color:#fff
    style A5 fill:#16a34a,color:#fff
    style A6 fill:#16a34a,color:#fff
    style M1 fill:#2563eb,color:#fff
    style M2 fill:#2563eb,color:#fff
    style M3 fill:#2563eb,color:#fff
    style M4 fill:#2563eb,color:#fff
    style M5 fill:#2563eb,color:#fff
```

### Restricciones de acceso (frontend + backend)

| Recurso | Admin | Monitor |
|---|---|---|
| `/api/auth/login` | ✓ | ✓ |
| `/api/auth/me` | ✓ | ✓ |
| `/api/salas/` (GET) | ✓ | ✓ (read-only) |
| `/api/salas/` (POST/PATCH/DELETE) | ✓ | ✗ |
| `/api/usuarios/` (GET all) | ✓ | ✗ (solo a sí mismo) |
| `/api/usuarios/monitores/` (POST) | ✓ | ✗ |
| `/api/horarios/` (GET) | ✓ | ✓ |
| `/api/horarios/` (POST/DELETE) | ✓ | ✗ |
| `/api/asignaciones/` (GET) | ✓ todas | ✓ solo las suyas |
| `/api/asignaciones/bulk/` | ✓ | ✗ |
| `/api/asignaciones/{id}/` (DELETE) | ✓ | ✗ |
| `/api/cambios/` (GET) | ✓ todas | ✓ solo las suyas |
| `/api/cambios/` (POST crear) | ✗ | ✓ |
| `/api/cambios/{id}/proponer/` | ✓ | ✗ |
| `/api/cambios/{id}/elegir/` | ✗ | ✓ (solo el solicitante) |
| `/api/cambios/{id}/rechazar/` | ✓ | ✗ |
| `/api/cambios/{id}/candidatos/` | ✓ | ✗ |

**Frontend:**
- Sidebar oculta Salas / Monitores / Horarios al rol `monitor`
- `<AdminRoute>` redirige a `/` si un monitor intenta entrar por URL directa a una vista admin

**Backend:**
- Cada `ViewSet.get_queryset()` filtra por `request.user` si es monitor
- Cada `action` admin valida explícitamente `request.user.rol == Usuario.ADMIN`

---

## Funcionalidades por módulo

### Frontend (React SPA — `frontend/`)

```
frontend/src/
├── api/                    # Clientes HTTP por dominio (axios)
│   ├── client.ts           # Base axios + JWT interceptors
│   ├── auth.api.ts         # login / logout / me
│   ├── usuarios.api.ts     # legacy
│   ├── monitores.api.ts    # crear monitor + lista
│   ├── salas.api.ts        # CRUD salas
│   ├── horarios.api.ts     # CRUD horarios
│   ├── semestres.api.ts    # listar semestres
│   ├── asignaciones.api.ts # CRUD + bulk
│   ├── cambios.api.ts      # crear, proponer, elegir, rechazar, candidatos
│   └── dashboard.api.ts    # agrega KPIs de múltiples endpoints
├── context/
│   └── AuthContext.tsx     # estado global de usuario + login/logout
├── components/
│   ├── PendingBackend.tsx
│   ├── WeeklyScheduleGrid.tsx  # grilla días×bloques con avatares
│   ├── layout/
│   │   ├── AppLayout.tsx
│   │   ├── Sidebar.tsx         # filtra nav items por rol
│   │   └── Topbar.tsx
│   └── ui/                     # Card, Button, Modal, Badge, Spinner,
│                               # EmptyState, ErrorMessage, Toast, UserAvatar
├── pages/
│   ├── LoginPage.tsx
│   ├── DashboardPage.tsx    # adaptativo (admin vs monitor)
│   ├── SalasPage.tsx        # CRUD admin
│   ├── MonitoresPage.tsx    # crear + listar (admin)
│   ├── HorariosPage.tsx     # CRUD + grilla (admin)
│   ├── AsignacionesPage.tsx # bulk + cronograma con grilla
│   └── SolicitudesCambioPage.tsx  # crear / proponer / elegir / rechazar
├── utils/
│   ├── formatDate.ts
│   ├── scheduleMapper.ts
│   ├── statusMapper.ts
│   └── userAvatar.ts        # paleta de 12 colores por userId
├── App.tsx                  # rutas + ProtectedRoute + AdminRoute
└── main.tsx
```

### Backend (Django apps — root)

```
sgmsc/                  # Django project root
├── settings.py         # DRF + JWT + CORS + Static + DB
├── urls.py             # /api/{usuarios,salas,horarios,semestres,asignaciones,cambios}/
└── wsgi.py
usuarios/               # Custom User + auth + crear monitor
├── models.py           # Usuario(AbstractUser) con cedula, rol, telefono
├── views.py            # login_view, logout_view, me_view, CrearMonitorView, UsuarioViewSet
├── serializers.py
├── urls.py             # /auth/login/, /auth/refresh/, /auth/me/, /usuarios/, /usuarios/monitores/
└── management/commands/
    ├── seed_demo.py        # carga demo idempotente
    └── create_admin.py     # crear/actualizar admin desde CLI (build hook)
salas/                  # Sala CRUD
horarios/               # Horario CRUD
semestres/              # Semestre CRUD
asignaciones/           # Asignacion + bulk_create
├── models.py
├── views.py            # AsignacionViewSet + action bulk_create
├── serializers.py
└── services.py         # crear_asignaciones()
cambios/                # SolicitudCambio + OpcionCambio + flujo swap
├── models.py           # SolicitudCambio (con estado con_propuestas) + OpcionCambio
├── views.py            # ViewSet con actions: proponer, elegir, rechazar, candidatos
├── serializers.py
└── services.py         # proponer_opciones(), elegir_opcion() swap atómico
AI_implementation/      # RAG + MCP Tools + Gemini chat
build.sh                # script de deploy Render: migrate + seed_demo + create_admin
```

---

## Flujos del sistema

### Flujo: Autenticación JWT

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant F as Frontend (React)
    participant LS as localStorage
    participant V as Vercel proxy
    participant B as Backend (Django)
    participant DB as Postgres

    Note over U,DB: Login inicial
    U->>F: Email + Password
    F->>V: POST /_api/api/auth/login/
    V->>B: POST /api/auth/login/
    B->>DB: authenticate(email, password)
    DB-->>B: User
    B->>B: RefreshToken.for_user(user)<br/>+ claim rol
    B-->>V: { access, refresh, user }
    V-->>F: { access, refresh, user }
    F->>LS: setItem(auth_access, auth_refresh)
    F->>F: setUser(user)
    F->>U: Redirect a /

    Note over U,DB: Request autenticado
    U->>F: Click "Asignaciones"
    F->>F: api.get('/api/asignaciones/')
    F->>F: interceptor: Authorization: Bearer <access>
    F->>V: GET /_api/api/asignaciones/
    V->>B: GET /api/asignaciones/ (JWT)
    B->>B: JWTAuthentication valida access
    B->>DB: SELECT asignaciones
    DB-->>B: rows
    B-->>F: 200 [...]

    Note over U,DB: Access expira (1h después)
    F->>V: GET /_api/api/salas/ (access expirado)
    V->>B: 401 Unauthorized
    B-->>F: 401
    F->>F: interceptor 401 → llama doRefresh()
    F->>V: POST /_api/api/auth/refresh/<br/>{ refresh }
    V->>B: POST /api/auth/refresh/
    B->>B: ROTATE_REFRESH_TOKENS → new access + refresh<br/>(viejo refresh queda blacklisted)
    B-->>F: { access, refresh }
    F->>LS: actualiza tokens
    F->>F: re-ejecuta request original con new access
    F->>V: GET /_api/api/salas/ (retry)
    V->>B: 200 OK
    B-->>F: data
```

**Características:**
- Access corto (1h) limita ventana de ataque si se filtra
- Refresh largo (7d) evita login frecuente
- `ROTATE_REFRESH_TOKENS=True`: cada refresh emite uno nuevo, el viejo se blacklistea
- Logout manda el refresh al backend para blacklistearlo

---

### Flujo: Creación de monitor

```mermaid
sequenceDiagram
    autonumber
    actor A as Admin
    participant F as Frontend
    participant B as Backend
    participant DB as Postgres
    participant SMTP as SMTP (opcional)

    A->>F: Form: email, nombre, apellido, cédula, teléfono
    F->>B: POST /api/usuarios/monitores/<br/>(Authorization: Bearer admin_access)
    B->>B: Valida request.user.rol == ADMIN
    B->>B: Valida unique(email), unique(cedula)
    B->>B: _generate_temp_password() (10 chars random)

    rect rgb(240, 248, 255)
        Note over B,DB: Transacción atómica
        B->>DB: create_user(email, cedula, rol=monitor, password=None)
        B->>DB: user.set_password(temp_pass) + save
    end

    alt SMTP configurado
        B->>SMTP: send_mail con credenciales
        Note right of B: fail_silently=True
    else SMTP no configurado
        B->>B: usa dummy backend (no envía)
    end

    B-->>F: 201 { ...user, temporary_password: "aB3xK9qZf2" }
    F->>A: Modal con email + password copiables
    A->>A: Copia y envía al monitor por canal seguro<br/>(WhatsApp, Slack, etc.)
```

**Por qué no usa solo email:**
El sistema fue diseñado con dominios ficticios `@sgmsc.edu.ec` para el seed; el envío SMTP es opcional. La password queda visible UNA vez al admin que la entrega al monitor manualmente.

---

### Flujo: Asignación bulk de turnos

```mermaid
sequenceDiagram
    autonumber
    actor A as Admin
    participant F as Frontend
    participant B as Backend
    participant DB as Postgres

    A->>F: Selecciona monitor + semestre + sala
    F->>B: GET /api/horarios/?sala=<id>
    B->>DB: SELECT horarios WHERE sala=<id>
    DB-->>B: [...]
    B-->>F: lista de horarios
    F->>A: Checkboxes de horarios disponibles
    A->>F: Marca múltiples horarios

    F->>B: POST /api/asignaciones/bulk/<br/>{ monitor, semestre, sala, horarios: ["h:5","h:8",...] }
    B->>B: Valida admin

    rect rgb(240, 248, 255)
        Note over B,DB: Transacción atómica
        loop por cada horario
            B->>B: Asignacion(monitor, horario, semestre)
            B->>B: full_clean() → valida no-cruce
            alt cruce detectado
                B->>B: ValidationError
            else OK
                B->>DB: INSERT asignacion
            end
        end
    end
    B-->>F: { creadas: N }
    F->>A: Toast "N asignaciones creadas"
```

---

### Flujo: Solicitud de cambio (swap mixto)

Este es el flujo más complejo del sistema. Diseñado para que los monitores **no tengan que ver la lista de otros monitores** (privacidad) y el admin coordine las opciones disponibles.

```mermaid
stateDiagram-v2
    [*] --> pendiente
    pendiente --> con_propuestas : admin propone opciones
    pendiente --> rechazada : admin rechaza
    con_propuestas --> aprobada : monitor elige opcion
    con_propuestas --> rechazada : admin rechaza
    aprobada --> [*]
    rechazada --> [*]
```

| Transición | Endpoint | Quién |
|---|---|---|
| `[*] → pendiente` | `POST /api/cambios/` | Monitor (crea solicitud) |
| `pendiente → con_propuestas` | `POST /api/cambios/{id}/proponer/` | Admin (al menos 2 opciones) |
| `pendiente → rechazada` | `POST /api/cambios/{id}/rechazar/` | Admin |
| `con_propuestas → aprobada` | `POST /api/cambios/{id}/elegir/` | Monitor solicitante (swap ejecutado) |
| `con_propuestas → rechazada` | `POST /api/cambios/{id}/rechazar/` | Admin |

**Secuencia completa del swap:**

```mermaid
sequenceDiagram
    autonumber
    actor M as Monitor_A_solicitante
    actor AD as Admin
    actor B_user as Monitor_B_reemplazo
    participant F as Frontend
    participant BE as Backend
    participant DB as Postgres

    rect rgb(250, 245, 230)
        Note over M,DB: PASO 1 — Monitor A solicita cambio
        M->>F: "Quiero cambiar mi turno LAB-01 lun 8-10"
        F->>BE: POST /api/cambios/<br/>{ asignacion: 5, motivo: "Tengo clase nueva" }
        BE->>BE: Valida solicitante == asignacion.monitor
        BE->>DB: INSERT SolicitudCambio<br/>estado=pendiente
        BE-->>F: 201 { id_cambio, estado: pendiente }
        F->>M: Toast "Solicitud enviada"
    end

    rect rgb(230, 245, 250)
        Note over AD,DB: PASO 2 — Admin revisa y propone opciones
        AD->>F: Abre Solicitudes
        F->>BE: GET /api/cambios/?estado=pendiente
        BE-->>F: [solicitud]
        AD->>F: Click "Proponer opciones"
        F->>BE: GET /api/cambios/{id}/candidatos/
        BE->>DB: SELECT asignaciones del mismo semestre<br/>EXCLUDE solicitante<br/>EXCLUDE turnos en solicitudes activas
        DB-->>BE: candidatos
        BE-->>F: lista agrupada por monitor
        F->>AD: Checkboxes de turnos de OTROS monitores
        AD->>F: Marca 2 opciones:<br/>- Monitor B en LAB-02 mar 10-12<br/>- Monitor C en LAB-03 jue 14-16
        F->>BE: POST /api/cambios/{id}/proponer/<br/>{ opciones: [12, 19] }

        rect rgb(240, 240, 240)
            Note over BE,DB: Transacción atómica
            BE->>BE: Valida ≥ 2 opciones, no duplicadas
            loop por cada opción
                BE->>DB: INSERT OpcionCambio<br/>(solicitud, asignacion_swap, orden)
            end
            BE->>DB: UPDATE solicitud SET estado=con_propuestas
        end
        BE-->>F: 200 { ...solicitud, opciones[] }
    end

    rect rgb(230, 250, 240)
        Note over M,DB: PASO 3 — Monitor A elige una opción
        M->>F: Abre Solicitudes (ve "Elige opción")
        F->>BE: GET /api/cambios/ (filtra suyas)
        BE-->>F: [solicitud con opciones]
        M->>F: Click "Elegir opción"
        F->>M: Modal con 2 radio cards<br/>(avatares de B y C)
        M->>F: Elige Opción 1: swap con Monitor B
        F->>BE: POST /api/cambios/{id}/elegir/<br/>{ opcion: 33 }

        rect rgb(240, 240, 240)
            Note over BE,DB: Swap atómico
            BE->>BE: Valida solicitante actual == request.user
            BE->>BE: Valida no-conflicto de horario para A en horario de B
            BE->>BE: Valida no-conflicto de horario para B en horario de A
            BE->>DB: UPDATE asignacion_A SET monitor=B
            BE->>DB: UPDATE asignacion_B SET monitor=A
            BE->>DB: UPDATE opcion SET seleccionada=true
            BE->>DB: UPDATE solicitud SET<br/>estado=aprobada, fecha_respuesta=now()<br/>monitor_reemplazo=B
        end
        BE-->>F: 200 { ...solicitud aprobada }
        F->>M: Toast "Swap ejecutado"
    end

    Note over M,B_user: Resultado final
    Note over M: A ahora tiene LAB-02 mar 10-12
    Note over B_user: B ahora tiene LAB-01 lun 8-10
```

**Por qué este diseño:**
- **Privacidad**: el monitor solicitante no ve la agenda de otros
- **Control**: el admin filtra qué opciones son viables (mismo semestre, sin conflictos previos)
- **Decisión final del solicitante**: él elige cuál swap le funciona
- **Atomicidad**: si algo falla, ninguna asignación cambia (transaction.atomic)
- **Trazabilidad**: `OpcionCambio.seleccionada=true` queda como evidencia histórica de qué opción se aceptó

---

## Casos de uso

```mermaid
flowchart TD
    Start([Inicio]) --> Login{Login}
    Login -->|Admin| AdminDash[Dashboard Admin<br/>KPIs globales]
    Login -->|Monitor| MonitorDash[Dashboard Monitor<br/>Mis turnos]

    %% Admin paths
    AdminDash --> A_Salas[Gestionar Salas]
    AdminDash --> A_Mon[Gestionar Monitores]
    AdminDash --> A_Hor[Gestionar Horarios]
    AdminDash --> A_Asig[Gestionar Asignaciones]
    AdminDash --> A_Sol[Revisar Solicitudes]

    A_Salas --> A_SalasCRUD[Crear / editar / eliminar salas]
    A_Mon --> A_MonCRUD[Crear monitor<br/>password temporal]
    A_Hor --> A_HorCRUD[Crear / eliminar horarios<br/>por sala+día+bloque]
    A_Asig --> A_AsigCreate[Bulk: monitor+semestre+sala<br/>+ N horarios]
    A_Asig --> A_AsigDelete[Click celda grilla<br/>→ liberar monitor]
    A_Sol --> A_SolPropose[Proponer 2+ opciones de swap]
    A_Sol --> A_SolReject[Rechazar solicitud]

    %% Monitor paths
    MonitorDash --> M_VerTurnos[Ver mi cronograma<br/>grilla semanal]
    MonitorDash --> M_Solicitar[Solicitar cambio de turno]
    MonitorDash --> M_Elegir[Elegir opción de swap]

    M_Solicitar -->|crea| A_Sol
    A_SolPropose -->|notifica| M_Elegir
    M_Elegir -->|swap ejecutado| End_Swap([Asignaciones intercambiadas])

    style AdminDash fill:#16a34a,color:#fff
    style MonitorDash fill:#2563eb,color:#fff
    style End_Swap fill:#fbbf24
```

---

## Endpoints REST

Todos bajo el prefijo `/api/`.

### Autenticación (`/api/auth/`)

| Método | Path | Body | Respuesta | Permisos |
|---|---|---|---|---|
| POST | `/auth/login/` | `{ email, password }` | `{ access, refresh, user }` | público |
| POST | `/auth/refresh/` | `{ refresh }` | `{ access, refresh }` | público (requiere refresh válido) |
| POST | `/auth/logout/` | `{ refresh }` (opcional) | 204 | autenticado |
| GET | `/auth/me/` | — | `user` | autenticado |

### Usuarios (`/api/usuarios/`)

| Método | Path | Permisos | Notas |
|---|---|---|---|
| GET | `/usuarios/` | admin: todos · monitor: solo a sí mismo | — |
| GET | `/usuarios/{id}/` | mismo filtro | — |
| POST | `/usuarios/monitores/` | admin | Crea monitor + genera password temporal en la response |

### Salas (`/api/salas/`)

| Método | Path | Permisos |
|---|---|---|
| GET | `/salas/` | autenticado |
| POST | `/salas/` | admin |
| GET/PATCH/DELETE | `/salas/{id}/` | admin (mutar) |

### Horarios (`/api/horarios/`)

| Método | Path | Notas |
|---|---|---|
| GET | `/horarios/?sala=<id>` | filtrable por sala |
| POST | `/horarios/` | admin |
| DELETE | `/horarios/{id}/` | admin |

### Asignaciones (`/api/asignaciones/`)

| Método | Path | Body | Permisos |
|---|---|---|---|
| GET | `/asignaciones/?semestre=&sala=&monitor=` | — | admin: todas · monitor: solo las suyas |
| POST | `/asignaciones/bulk/` | `{ monitor, semestre, sala, horarios: ["h:<id>", ...] }` | admin |
| DELETE | `/asignaciones/{id}/` | — | admin |

### Cambios (`/api/cambios/`)

| Método | Path | Body | Permisos |
|---|---|---|---|
| GET | `/cambios/?estado=` | — | admin: todas · monitor: solo las suyas |
| POST | `/cambios/` | `{ asignacion, motivo }` | monitor (debe ser dueño de la asignación) |
| GET | `/cambios/{id}/candidatos/` | — | admin |
| POST | `/cambios/{id}/proponer/` | `{ opciones: [asig_id,...], respuesta }` | admin (≥ 2 opciones) |
| POST | `/cambios/{id}/elegir/` | `{ opcion: id_opcion }` | monitor solicitante |
| POST | `/cambios/{id}/rechazar/` | `{ respuesta }` (opcional) | admin |

---

## Setup local

### Backend

```bash
# 1. Clonar y entrar a la rama del API
git clone <repo>
cd SIstema-de-gestion-de-monitores
git checkout feature/drf-api

# 2. Virtualenv
python -m venv venv
source venv/bin/activate          # Linux/macOS
venv\Scripts\activate              # Windows

# 3. Dependencias
pip install -r requirements.txt

# 4. .env (raíz del proyecto)
cat > .env <<EOF
DJANGO_SECRET_KEY=tu-secret-key-aqui
DEBUG=True
DATABASE_URL=postgres://user:pass@localhost:5432/sgmsc
# (alternativamente DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)
EOF

# 5. Migraciones + seed
python manage.py migrate
python manage.py seed_demo

# 6. Run
python manage.py runserver
# API en http://localhost:8000/api/
```

### Frontend

```bash
cd frontend
npm install

# .env.local — apuntar al backend local
echo "VITE_API_URL=http://localhost:8000" > .env.local

npm run dev
# SPA en http://localhost:5173
```

### Credenciales del seed

| Rol | Email | Password |
|---|---|---|
| Admin | `admin@sgmsc.edu.ec` | `Admin@2026` |
| Monitor (cualquiera) | `juan.rodriguez@sgmsc.edu.ec`, `maria.garcia@...`, ... | `Monitor123` |

---

## Despliegue

```mermaid
flowchart LR
    Dev[Developer] -->|push fork/main| GH1[GitHub fork/main]
    Dev -->|push fork/feature-drf-api| GH2[GitHub fork/feature/drf-api]
    GH1 -->|webhook| V[Vercel]
    GH2 -->|webhook| R[Render]
    V -->|build & deploy| SPA[sgmsc-frontend.vercel.app]
    R -->|build.sh| BE[sistema-de-gestion-de-monitores.onrender.com]
    BE -->|migrate + seed_demo<br/>+ create_admin| SUP[(Supabase Postgres)]

    style V fill:#000,color:#fff
    style R fill:#46e3b7,color:#000
    style GH1 fill:#24292e,color:#fff
    style GH2 fill:#24292e,color:#fff
```

### Render (Backend) — `feature/drf-api`

**Build Command:** `./build.sh`

```bash
pip install --upgrade pip
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py seed_demo

# Crea/actualiza admin extra si las env vars están definidas
if [ -n "$EXTRA_ADMIN_EMAIL" ] && [ -n "$EXTRA_ADMIN_PASSWORD" ]; then
  python manage.py create_admin --email "$EXTRA_ADMIN_EMAIL" --password "$EXTRA_ADMIN_PASSWORD"
fi
```

**Env vars en Render:**
| Variable | Valor |
|---|---|
| `DATABASE_URL` | `postgresql://...@pooler.supabase.com:6543/postgres` (Session Pooler) |
| `DJANGO_SECRET_KEY` | secret aleatorio |
| `DEBUG` | `False` |
| `CORS_ALLOWED_ORIGINS` | (opcional) lista coma-separada |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | (opcional, App Password de Gmail) |
| `EXTRA_ADMIN_EMAIL`, `EXTRA_ADMIN_PASSWORD` | (opcional, crea admin extra) |

### Vercel (Frontend) — `main`

**Root Directory:** `frontend`
**Build Command:** `npm run build`
**Output:** `dist`

`vercel.json` define:
- Proxy `/_api/*` → `https://sistema-de-gestion-de-monitores.onrender.com/*` (evita CORS)
- SPA fallback: `/(.*)` → `/index.html`
- Headers de seguridad (`X-Content-Type-Options`, `Referrer-Policy`)

---

## Seed demo

`python manage.py seed_demo` (idempotente):

| Entidad | Cantidad | Detalle |
|---|---|---|
| Admin | 1 | `admin@sgmsc.edu.ec` / `Admin@2026` |
| Monitores | 8 | `monitor_juan`, `monitor_maria`, ... — `Monitor123` |
| Salas | 4 | `LAB-01` a `LAB-04` |
| Semestres | 3 | `2025-1` (activo), `2025-2`, `2026-1` |
| Horarios | 35 | Distribuidos por sala/día/bloque |
| Asignaciones | 15 | En el semestre 2025-1 |

**Comportamiento defensivo:**
Si las asignaciones originales fueron modificadas por un swap previo, el seed:
1. **Salta** asignaciones cuyo horario ya está tomado por otro monitor
2. **Salta** asignaciones que causarían conflicto de horario para el monitor
3. Loggea cada salto sin fallar el build

---

## Servicios externos

| Servicio | Uso | Documentación |
|---|---|---|
| **Supabase** | Base de datos Postgres + pgvector | https://supabase.com/docs |
| **Render** | Hosting del backend Django/Gunicorn | https://render.com/docs |
| **Vercel** | Hosting del SPA + proxy reverso | https://vercel.com/docs |
| **Google Gemini** | LLM para el chat IA | https://ai.google.dev |
| **Gmail SMTP** | (opcional) envío de credenciales | https://support.google.com/accounts/answer/185833 |

---

## Innovaciones de IA

### Arquitectura RAG (Retrieval-Augmented Generation)
El sistema utiliza RAG para fundamentar las respuestas de la IA directamente en los datos de la base de datos relacional, evitando "alucinaciones".

### Model Context Protocol (MCP) Tools
- **Reportes XLSX**: `Pandas` genera archivos descargables automáticamente
- **Detección de conflictos**: validación matemática de solapamientos de horarios
- **Fuzzy matching (`RapidFuzz`)**: corrige errores ortográficos en búsquedas

### Seguridad proactiva
- Filtro de inyección SQL para queries generadas por el LLM
- Alerta SMTP al jefe de departamento si se detectan comandos destructivos
- Memoria contextual por usuario (`session_id = username`)

---

## Desarrolladores

- **Juan Andrés Muñoz Zapata**
- **Enmanuel Velásquez Romero**
- **Juan Andrés Rojas Saavedra**
