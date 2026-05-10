"""Servidor MCP para exponer consultas SQL de solo lectura (SELECT) vía stdio."""

import os
from pathlib import Path
from urllib.parse import quote_plus

import psycopg2
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


def _build_database_url_from_parts() -> str | None:
    """Construye DATABASE_URL a partir de DB_* (como en settings.py).

    Formato: postgresql://user:pass@host:port/dbname
    """
    name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")

    if not all([name, user, password, host, port]):
        return None

    user_enc = quote_plus(user)
    pass_enc = quote_plus(password)
    return f"postgresql://{user_enc}:{pass_enc}@{host}:{port}/{name}"


DATABASE_URL = os.getenv("DATABASE_URL") or _build_database_url_from_parts()

# 2. Inicializar el servidor FastMCP
# Este nombre es interno, sirve para identificar el servidor en los logs
mcp = FastMCP("Servidor_sgmsc")

# 3. Definir la Herramienta (Tool)
# El decorador @mcp.tool() convierte esta función normal de Python 
# en una herramienta que el LLM (Gemini) puede "ver" y usar.
@mcp.tool()
def consultar_base_datos(sql_query: str) -> str:
    """
    Herramienta exclusiva de SOLO LECTURA para el Administrador del sistema. 
    Ejecuta consultas SQL en la base de datos PostgreSQL de la universidad para extraer información sobre monitores, horas acumuladas, horarios y rendimiento.

    REGLAS ESTRICTAS Y LIMITANTES (CRÍTICO):
    1. OPERACIONES PERMITIDAS: Estás restringido EXCLUSIVAMENTE a operaciones de consulta (`SELECT`).
    2. OPERACIONES PROHIBIDAS: BAJO NINGUNA CIRCUNSTANCIA puedes generar, intentar o ejecutar sentencias que modifiquen los datos o la estructura de la base de datos. Esto incluye, pero no se limita a: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE` o ejecución de procedimientos almacenados que alteren estado.
    3. MANEJO DE INTENCIONES INSEGURAS: Si el administrador solicita agregar, borrar o modificar información, NO uses esta herramienta. En su lugar, responde directamente que tu rol y tus permisos están limitados estrictamente a la consulta de información.

    El resultado de esta herramienta será una representación en texto de las filas y columnas obtenidas, úsala para redactar una respuesta natural y precisa al administrador.
    """
    
    if not DATABASE_URL:
        return (
            "Error de configuración: falta DATABASE_URL o las variables DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT."
        )

    # Validaciones de seguridad básicas (para desarrollo)
    query_upper = (sql_query or "").upper()
    if any(forbidden in query_upper for forbidden in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE"]):
        return "Error de seguridad: Solo se permiten consultas SELECT (solo lectura)."

    conn = None
    try:
        # Conectar a PostgreSQL usando la variable de entorno
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Ejecutar la consulta generada por la IA
        cur.execute(sql_query)
        
        # Obtener todos los resultados
        resultados = cur.fetchall()
        
        # Obtener los nombres de las columnas para darle más contexto a la IA
        column_names = [desc[0] for desc in cur.description]
        
        cur.close()
        
        # Formatear la respuesta para que la IA la entienda fácilmente
        respuesta = f"Columnas: {', '.join(column_names)}\n"
        respuesta += "Resultados:\n"
        for fila in resultados:
            respuesta += str(fila) + "\n"
            
        return respuesta

    except psycopg2.Error as e:
        # Si la IA se equivoca en la sintaxis SQL, le devolvemos el error
        # para que "aprenda" y corrija la consulta en un segundo intento.
        return f"Error en la consulta SQL: {e}"
        
    except Exception as e:
        return f"Error inesperado del sistema: {e}"
        
    finally:
        # Siempre asegurar que la conexión se cierre, pase lo que pase
        if conn is not None:
            conn.close()

# 4. Punto de entrada para ejecutar el servidor
if __name__ == "__main__":
    # Inicia el servidor MCP para escuchar peticiones a través de la terminal (stdio)
    mcp.run()