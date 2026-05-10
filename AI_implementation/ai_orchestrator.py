# AI_implementation/ai_orchestrator.py
"""Orquestador de IA para consultas de SOLO LECTURA vía MCP.

Este módulo quedó mezclado entre dos enfoques (Ollama/OpenAI y Gemini).
El error actual `NameError: client is not defined` ocurre porque el código
intenta usar un cliente OpenAI (`client.chat...`) que ya no existe.

Solución aplicada: flujo consistente con Gemini (google-generativeai) + MCP:
1) Gemini genera una consulta SQL SELECT en JSON estricto.
2) Ejecutamos la consulta con la tool `consultar_base_datos` expuesta por MCP.
3) Gemini redacta la respuesta final usando únicamente los resultados.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any
import psycopg2
import google.generativeai as genai
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from urllib.parse import quote_plus

from .prompts import SYSTEM_PROMPT_MONITORES


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")
FORBIDDEN_SQL = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE")


def _build_database_url_from_parts() -> str | None:
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


def _get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL") or _build_database_url_from_parts()
    if not database_url:
        raise RuntimeError(
            "Falta configurar `DATABASE_URL` o las variables DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT en tu .env."
        )
    return database_url


def _embedding_to_vector_literal(embedding: list[float]) -> str:
    """Convierte una lista de floats al literal que entiende pgvector: [0.1, 0.2, ...]."""
    # json.dumps genera un formato compatible: [0.1, 0.2, ...]
    return json.dumps([float(x) for x in embedding])


def _embed_text(text: str) -> list[float]:
    """Obtiene embeddings con `google-generativeai`.

    Nota: este repo usa el SDK `google-generativeai` (deprecado) que llama a la API v1beta.
    En algunas cuentas, los modelos de embedding disponibles son `models/gemini-embedding-*`.
    Por defecto suelen devolver 3072 dimensiones, pero se puede pedir un tamaño menor con
    `output_dimensionality` para que coincida con `vector(768)` en Postgres.
    """
    genai.configure(api_key=_get_gemini_api_key())

    preferred_model = os.getenv("GEMINI_EMBED_MODEL") or "models/gemini-embedding-2"
    candidate_models: list[str] = []
    for model_name in (
        preferred_model,
        "models/gemini-embedding-2",
        "models/gemini-embedding-001",
        "models/gemini-embedding-2-preview",
    ):
        if model_name and model_name not in candidate_models:
            candidate_models.append(model_name)

    try:
        output_dims = int(os.getenv("GEMINI_EMBED_DIM") or "768")
    except ValueError:
        output_dims = 768

    last_exc: Exception | None = None
    for embed_model in candidate_models:
        try:
            result = genai.embed_content(
                model=embed_model,
                content=text,
                output_dimensionality=output_dims,
            )

            if isinstance(result, dict) and "embedding" in result:
                embedding = result["embedding"]
                if isinstance(embedding, list):
                    return [float(x) for x in embedding]

            if hasattr(result, "embedding"):
                embedding = getattr(result, "embedding")
                if isinstance(embedding, list):
                    return [float(x) for x in embedding]

            raise RuntimeError(
                f"No pude extraer el embedding desde la respuesta de embed_content() usando {embed_model}."
            )
        except Exception as exc:
            last_exc = exc
            continue

    raise RuntimeError(f"No pude obtener embedding con ningún modelo. Último error: {last_exc}")


def _get_gemini_api_key() -> str:
	api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("API_KEY")
	if not api_key:
		raise RuntimeError(
			"Falta configurar `GEMINI_API_KEY` (o `GOOGLE_API_KEY` / `API_KEY`) en tu .env/entorno."
		)
	return api_key


def _get_gemini_model() -> genai.GenerativeModel:
	genai.configure(api_key=_get_gemini_api_key())
	# Nota: el set de modelos disponibles depende de tu API key.
	# En este entorno, `list_models()` expone (entre otros) gemini-2.0-flash.
	model_name = os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"
	return genai.GenerativeModel(
		model_name=model_name,
		system_instruction=SYSTEM_PROMPT_MONITORES,
	)


def _extract_json_object(text: str) -> dict[str, Any]:
	text = (text or "").strip()
	if not text:
		raise ValueError("Respuesta vacía del modelo.")

	try:
		obj = json.loads(text)
		if isinstance(obj, dict):
			return obj
	except json.JSONDecodeError:
		pass

	match = re.search(r"\{.*\}", text, flags=re.DOTALL)
	if not match:
		raise ValueError("El modelo no devolvió JSON.")
	obj = json.loads(match.group(0))
	if not isinstance(obj, dict):
		raise ValueError("El JSON devuelto no es un objeto.")
	return obj


def _validate_sql(sql_query: str) -> str:
	sql_query = (sql_query or "").strip()
	if not sql_query:
		raise ValueError("`sql_query` vacío.")

	upper = sql_query.upper()
	if any(word in upper for word in FORBIDDEN_SQL):
		raise ValueError("Solo se permiten consultas SELECT (solo lectura).")
	if not (upper.startswith("SELECT") or upper.startswith("WITH")):
		raise ValueError("La consulta debe iniciar con SELECT o WITH.")
	return sql_query

# --- FUNCIONES DE MEMORIA (RAG) ---
def buscar_memoria_relevante(query_texto: str, session_id: str) -> str:
    """Busca recuerdos similares en `ai_memory` usando pgvector.

    Es "best-effort": si falla (sin tabla, sin extensión, sin permisos, etc.),
    devuelve cadena vacía para no romper el chat.
    """
    try:
        embedding = _embed_text(query_texto)
        vector_literal = _embedding_to_vector_literal(embedding)

        conn = psycopg2.connect(_get_database_url())
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT user_query, ai_response
                    FROM ai_memory
                    WHERE session_id = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT 2
                    """,
                    (session_id, vector_literal),
                )
                recuerdos = cur.fetchall()
        finally:
            conn.close()

        if recuerdos:
            contexto = "\nRecuerdos de esta sesión:\n"
            for user_q, ai_r in recuerdos:
                contexto += f"- Usuario dijo: {user_q}\n- Bot respondió: {ai_r}\n"
            return contexto
        return ""
    except Exception:
        return ""


def guardar_en_memoria(query: str, response: str, session_id: str) -> None:
    """Guarda la interacción en `ai_memory` (best-effort)."""
    try:
        embedding = _embed_text(query)
        vector_literal = _embedding_to_vector_literal(embedding)

        conn = psycopg2.connect(_get_database_url())
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ai_memory (session_id, user_query, ai_response, embedding)
                    VALUES (%s, %s, %s, %s::vector)
                    """,
                    (session_id, query, response, vector_literal),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        return

async def get_ai_response(user_message: str, session_id: str = "default") -> str:
    """Genera respuesta del asistente usando Gemini + MCP (solo lectura) y Memoria Semántica."""

    model = _get_gemini_model()

    # --- RAG: Recuperar el contexto de la sesión actual ---
    # Si la función buscar_memoria_relevante devuelve vacío, no pasa nada.
    contexto_previo = buscar_memoria_relevante(user_message, session_id)
    # ---------------------------------------------------------------

    planner_prompt = (
        "Devuelve SOLO un JSON válido (sin markdown ni texto extra).\n"
        "Formato exacto:\n"
        "{\"sql_query\": \"SELECT ...\"}\n\n"
        "Reglas: SOLO SELECT; no uses tablas del sistema (auth_*, django_*); "
        "usa el esquema del system prompt.\n\n"
        f"{contexto_previo}\n" # <--- RAG PASO 2: Inyectar contexto al planner
        f"Pregunta del administrador: {user_message}"
    )

    try:
        plan_resp = model.generate_content(planner_prompt)
    except Exception as exc:
        return f"Error al llamar a Gemini para generar SQL: {exc}"

    plan_text = getattr(plan_resp, "text", "") or ""
    try:
        plan = _extract_json_object(plan_text)
        sql_query = _validate_sql(str(plan.get("sql_query", "")))
    except Exception as exc:
        return (
            "No pude generar una consulta SQL válida. "
            f"Detalle: {exc}. Respuesta del modelo: {plan_text[:200]}"
        )

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).with_name("mcp_server.py"))],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_result = await session.call_tool(
                "consultar_base_datos",
                arguments={"sql_query": sql_query},
            )
            try:
                tool_response_text = mcp_result.content[0].text
            except Exception:
                tool_response_text = str(mcp_result)

    final_prompt = (
        "Responde al administrador usando SOLO el resultado de la base de datos. "
        "Si el resultado indica error, explica el motivo y sugiere una consulta SELECT alternativa.\n\n"
        f"{contexto_previo}\n" # <--- RAG PASO 3: Inyectar contexto para mantener coherencia en la redacción
        f"Pregunta del administrador: {user_message}\n\n"
        f"SQL ejecutado:\n{sql_query}\n\n"
        f"Resultado de BD:\n{tool_response_text}\n\n"
        "Respuesta:"
    )

    try:
        final_resp = model.generate_content(final_prompt)
    except Exception as exc:
        return (
            "Obtuve datos de la base de datos, pero falló Gemini al redactar la respuesta. "
            f"Detalle: {exc}\n\nResultado de BD:\n{tool_response_text}"
        )

    final_text = getattr(final_resp, "text", "") or ""
    respuesta_limpia = final_text.strip() or "Respuesta vacía del modelo."

    # --- RAG PASO 4: Guardar la interacción final en la memoria ---
    # Solo guardamos si llegamos a este punto (es decir, no hubo errores)
    guardar_en_memoria(user_message, respuesta_limpia, session_id)
    # ---------------------------------------------------------------

    return respuesta_limpia