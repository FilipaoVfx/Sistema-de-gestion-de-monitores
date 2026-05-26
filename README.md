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

### Backend

| Tecnología | Versión |
|---|---|
| Python | 3.12+ |
| Django | 6.0.4 |
| PostgreSQL | 15+ (con extensión pgvector) |
| Gunicorn | 23.0.0 |
| WhiteNoise | 6.8.2 |

### Frontend

| Tecnología | Versión |
|---|---|
| React | 18.3.1 |
| TypeScript | 5.2.2 |
| Vite | 5.3.1 |
| Tailwind CSS | 3.4.4 |
| React Router DOM | 6.24.0 |
| Axios | 1.7.2 |
| Node.js | 18+ |

### IA e Innovación

| Tecnología | Versión |
|---|---|
| Google Gemini API | — |
| MCP (Model Context Protocol) | 1.27.1 |
| Pandas | 3.0.2 |
| OpenPyXL | 3.1.5 |
| RapidFuzz | — |

## Requisitos Previos

Antes de instalar el proyecto, asegúrate de tener instalado:

* **Python** 3.12 o superior
* **Node.js** 18 o superior
* **npm** 9 o superior
* **PostgreSQL** 15 o superior con extensión **pgvector**
* **Git**

## Estructura del Proyecto

```
Sistema-de-gestion-de-monitores/
├── manage.py                    # Punto de entrada de Django
├── requirements.txt             # Dependencias de Python
├── .env.example                 # Plantilla de variables de entorno
├── build.sh                     # Script de build para Render
├── render.yaml                  # Configuración de despliegue en Render
│
├── sgmsc/                       # Configuración principal de Django
│   ├── settings.py              # Configuración del proyecto
│   ├── urls.py                  # Rutas raíz
│   └── wsgi.py / asgi.py        # Puntos de entrada WSGI/ASGI
│
├── usuarios/                    # App: Gestión de usuarios y autenticación
│   ├── models.py                # Modelo Usuario (login, roles)
│   ├── views.py                 # Login, dashboards, chat IA
│   ├── forms.py                 # Formularios de registro
│   └── templates/               # Templates HTML (Django)
│
├── salas/                       # App: Gestión de salas de cómputo
│   ├── models.py                # Modelo Sala
│   └── views.py                 # CRUD de salas
│
├── horarios/                    # App: Gestión de horarios
│   ├── models.py                # Modelo Horario
│   └── views.py                 # CRUD de horarios
│
├── asignaciones/                # App: Asignación monitores ↔ horarios
│   ├── models.py                # Modelo Asignacion
│   ├── services.py              # Lógica de creación atómica
│   └── templates/               # Templates HTML
│
├── cambios/                     # App: Solicitudes de cambio de turno
│   ├── models.py                # Modelo SolicitudCambio
│   ├── views.py                 # CRUD + aprobación/rechazo
│   └── templates/               # Templates HTML
│
├── semestres/                   # App: Gestión de semestres académicos
│
├── AI_implementation/           # Módulo de IA (MCP + Gemini)
│   ├── ai_orchestrator.py       # Orquestador principal de IA
│   ├── mcp_server.py            # Servidor MCP
│   ├── prompts.py               # Prompts del sistema
│   └── ai_documentation.md      # Documentación de la arquitectura IA
│
├── Diagramas_RF_RNF/            # Documentación de requisitos y diagramas
│
└── frontend/                    # SPA en React + TypeScript + Tailwind
    ├── index.html
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    └── src/
        ├── main.tsx             # Punto de entrada React
        ├── App.tsx              # Router principal con guards
        ├── api/                 # Módulos de API (axios)
        ├── components/          # Componentes reutilizables
        │   ├── layout/          # AppLayout, Sidebar, Topbar
        │   └── ui/              # Button, Card, Modal, Toast, etc.
        ├── pages/               # Páginas (Login, Dashboard, CRUDs)
        ├── context/             # AuthContext (estado global de auth)
        ├── types/               # Interfaces TypeScript
        └── utils/               # Utilidades (formateo, mapeo)
```

## Instalación y Ejecución

### 1. Clonar el repositorio

```bash
git clone https://github.com/FilipaoVfx/Sistema-de-gestion-de-monitores.git
cd Sistema-de-gestion-de-monitores
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con los valores correspondientes
```

Variables requeridas:

| Variable | Descripción |
|---|---|
| `DJANGO_ADMIN_EMAIL` | Email del administrador inicial |
| `DJANGO_ADMIN_PASSWORD` | Contraseña del administrador inicial |
| `DATABASE_URL` | URL de conexión a PostgreSQL |
| `GEMINI_API_KEY` | API Key de Google Gemini |

### 3. Backend (Django)

```bash
# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar migraciones
python manage.py migrate

# Crear admin inicial
python manage.py crear_admin_inicial

# Iniciar servidor de desarrollo
python manage.py runserver
```

### 4. Frontend (React)

```bash
cd frontend

# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev
```

El backend estará disponible en `http://localhost:8000` y el frontend en `http://localhost:5173`.

## Desarrolladores del Proyecto

* **Juan Andres Muñoz Zapata**
* **Enmanuel Velasquez Romero**
* **Juan Andres Rojas Saavedra**
* **Juan Felipe González**
