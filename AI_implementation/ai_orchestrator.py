# AI_implementation/ai_orchestrator.py
"""Orquestador de IA para consultas de SOLO LECTURA vía MCP.

Este módulo quedó mezclado entre dos enfoques (Ollama/OpenAI y Gemini).
El error actual `NameError: client is not defined` ocurre porque el código
intenta usar un cliente OpenAI (`client.chat...`) que ya no existe.

Solución aplicada: flujo consistente con Gemini (google-generativeai) + MCP:
1) Gemini genera una consulta SQL SELECT en JSON estricto.
2) Ejecutamos la consulta con la tool `consultar_base_datos` expuesta por MCP.
3) Gemini redacta la respuesta final usando únicamente los resultados.

Característica de Memoria a Corto Plazo:
- Recupera historial de los últimos 2 minutos desde chat_history
- Inyecta este contexto en el prompt para evitar pérdida de contexto temporal
- Usa sync_to_async para ejecutar consultas Django en contexto async
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from datetime import timedelta
import psycopg2
import google.generativeai as genai
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from urllib.parse import quote_plus
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.core.mail import send_mail
from sgmsc import settings

from .prompts import SYSTEM_PROMPT_MONITORES


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")
FORBIDDEN_SQL = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE")
DESTRUCTIVE_INTENT_KEYWORDS = (
    "DELETE",
    "DROP",
    "TRUNCATE",
    "ALTER",
    "INSERT",
    "UPDATE",
    "BORRAR",
    "ELIMINAR",
    "ELIMINA",
    "QUITAR",
    "MODIFICAR",
    "CREAR",
)


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


def _contiene_intento_destructivo(texto: str) -> bool:
	texto_upper = (texto or "").upper()
	return any(keyword in texto_upper for keyword in DESTRUCTIVE_INTENT_KEYWORDS)


def _formatear_mcp_resultado(tool_name: str, raw_text: str) -> str:
	raw_text = (raw_text or "").strip()
	if not raw_text:
		return f"[{tool_name}] Resultado vacío."
	try:
		obj = json.loads(raw_text)
		return f"[{tool_name}]\n{json.dumps(obj, ensure_ascii=False, indent=2, default=str)}"
	except json.JSONDecodeError:
		return f"[{tool_name}]\n{raw_text}"


async def _call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> str:
	server_params = StdioServerParameters(
		command=sys.executable,
		args=[str(Path(__file__).with_name("mcp_server.py"))],
	)
	async with stdio_client(server_params) as (read, write):
		async with ClientSession(read, write) as session:
			await session.initialize()
			result = await session.call_tool(tool_name, arguments=arguments)
			try:
				return result.content[0].text
			except Exception:
				return str(result)


def _build_tool_catalog() -> str:
	return """
Herramientas MCP disponibles:
1. consultar_base_datos
   - Argumentos: {"sql_query": "SELECT ..."}
   - Usa solo para consultas de lectura.
2. generate_excel_report
   - Argumentos: {"data_json": "<JSON con rows>", "report_name": "reporte"}
   - Usa cuando el usuario pida un archivo Excel o un informe descargable.
3. verificar_conflicto_horario
   - Argumentos: {"sala_id": 1, "dia_semana": "1", "hora_inicio": "08:00", "hora_fin": "10:00", "semestre_id": 1}
   - Usa para validar cruces de horario.
4. busqueda_difusa_nombres
   - Argumentos: {"entidad": "monitor" o "sala", "termino_busqueda": "texto"}
   - Usa para coincidencias aproximadas.

Responde SOLO con JSON válido y una de estas formas:
{"action":"tool_call","tool_name":"consultar_base_datos","arguments":{"sql_query":"SELECT ..."}}
{"action":"final","response":"respuesta natural"}

Si necesitas más de una tool, usa una por turno y espera el resultado antes de decidir la siguiente.
""".strip()


def _solicita_reporte_excel(texto: str) -> bool:
	texto = (texto or "").lower()
	palabras_clave = ("excel", "xlsx", "reporte", "informe", "archivo", "descargar")
	return any(palabra in texto for palabra in palabras_clave)


def _nombre_reporte_desde_pregunta(texto: str) -> str:
	texto = re.sub(r"[^a-zA-Z0-9]+", "_", (texto or "").strip().lower())
	texto = texto.strip("_")
	return texto[:40] or "reporte"


def _enviar_alerta_jefe(usuario: str, sql_peligroso: str) -> None:
	"""Envía el correo de alerta al jefe de departamento."""
	destinatario = getattr(settings, "EMAIL_JEFE_DEPARTAMENTO", None)
	remitente = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)
	if not destinatario:
		raise RuntimeError("Falta configurar EMAIL_JEFE_DEPARTAMENTO.")
	if not remitente:
		raise RuntimeError("Falta configurar EMAIL_HOST_USER o DEFAULT_FROM_EMAIL.")

	asunto = "ALERTA DE SEGURIDAD CRITICA: intento de operacion destructiva"
	mensaje = (
		"El sistema de proteccion IA ha bloqueado un intento de alteracion destructiva en la base de datos.\n\n"
		f"Usuario implicado: {usuario}\n"
		f"Fecha y hora: {timezone.now()}\n\n"
		f"Consulta o intento bloqueado:\n{sql_peligroso}\n\n"
		"La accion no se ejecuto y el sistema sigue seguro."
	)

	send_mail(
		subject=asunto,
		message=mensaje,
		from_email=remitente,
		recipient_list=[destinatario],
		fail_silently=False,
	)


def _bloquear_intento_destructivo(usuario: str, intento: str) -> str:
	error_correo = None
	try:
		_enviar_alerta_jefe(usuario, intento)
	except Exception as exc:
		error_correo = str(exc)

	mensaje = "Operacion bloqueada por politicas de seguridad. El incidente ha sido reportado."
	if error_correo:
		mensaje += f" No se pudo enviar el correo de alerta: {error_correo}"
	return mensaje


def _validate_sql(sql_query: str, session_id: str = "Usuario Desconocido") -> str:
	sql_query = (sql_query or "").strip()
	if not sql_query:
		raise ValueError("`sql_query` vacío.")

	upper = sql_query.upper()

	if any(keyword in upper for keyword in ("DELETE", "TRUNCATE", "DROP")):
		raise ValueError(_bloquear_intento_destructivo(session_id, sql_query))

	if any(word in upper for word in FORBIDDEN_SQL):
		raise ValueError("Solo se permiten consultas SELECT (solo lectura). No puedes alterar datos.")

	if not (upper.startswith("SELECT") or upper.startswith("WITH")):
		raise ValueError("La consulta debe iniciar con SELECT o WITH.")

	return sql_query

# --- FUNCIONES DE MEMORIA CORTO PLAZO ---
def _recuperar_memoria_corto_plazo_sync(session_id: str) -> str:
    """Consulta sincrónica para recuperar el historial de los últimos 5 minutos.
    
    Esta función se ejecuta dentro de sync_to_async para evitar bloqueos.
    Recupera mensajes del historial de chat donde:
    - session_id coincide con el del admin
    - created_at >= hace 5  minutos
    
    Devuelve un string formateado o vacío si hay error.
    """
    try:
        conn = psycopg2.connect(_get_database_url())
        try:
            with conn.cursor() as cur:
                # Consultar los últimos 5 minutos de historial
                five_minutes_ago = timezone.now() - timedelta(minutes=5)
                cur.execute(
                    """
                    SELECT user_message, ai_response
                    FROM chat_history
                    WHERE session_id = %s AND created_at >= %s
                    ORDER BY created_at ASC
                    """,
                    (session_id, five_minutes_ago),
                )
                registros = cur.fetchall()
        finally:
            conn.close()

        if registros:
            memoria_texto = ""
            for user_msg, ai_resp in registros:
                memoria_texto += f"Usuario: {user_msg}\nAsistente: {ai_resp}\n"
            return memoria_texto.strip()
        return ""
    except Exception:
        # Best-effort: si falla, devolvemos vacío para no romper el chat
        return ""


def _guardar_en_historial_sync(session_id: str, user_message: str, ai_response: str) -> None:
    """Guarda la interacción en la tabla chat_history (best-effort)."""
    try:
        conn = psycopg2.connect(_get_database_url())
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chat_history (session_id, user_message, ai_response, created_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (session_id, user_message, ai_response, timezone.now()),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        return

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
	"""Genera respuesta del asistente usando Gemini + MCP."""

	if _contiene_intento_destructivo(user_message):
		mensaje_bloqueo = _bloquear_intento_destructivo(session_id, user_message)
		return mensaje_bloqueo

	model = _get_gemini_model()
	recuperar_memoria = sync_to_async(_recuperar_memoria_corto_plazo_sync)
	memoria_corto_plazo = await recuperar_memoria(session_id)
	contexto_previo = buscar_memoria_relevante(user_message, session_id)

	prompt_memoria = ""
	if memoria_corto_plazo:
		prompt_memoria = (
			"<MEMORIA RECIENTE (ULTIMOS 5 MINUTOS - PRIORIDAD MAXIMA)>\n"
			"Aqui esta el contexto inmediato de la conversacion. Si el usuario hace referencia a algo reciente, "
			"retienes esta informacion como fuente principal:\n"
			f"{memoria_corto_plazo}\n"
			"</MEMORIA RECIENTE>\n\n"
		)

	contexto_base = "\n\n".join(part for part in (prompt_memoria, contexto_previo) if part)
	historial_tools: list[str] = []
	ultima_respuesta_modelo = ""

	for _ in range(4):
		planner_prompt = (
			f"{contexto_base}\n\n"
			f"{_build_tool_catalog()}\n\n"
			"<PREGUNTA_ACTUAL>\n"
			f"{user_message}\n"
			"</PREGUNTA_ACTUAL>\n\n"
			"<RESULTADOS_DE_TOOLS>\n"
			f"{chr(10).join(historial_tools) if historial_tools else 'Sin resultados previos.'}\n"
			"</RESULTADOS_DE_TOOLS>"
		)

		try:
			plan_resp = model.generate_content(planner_prompt)
		except Exception as exc:
			return f"Error al llamar a Gemini para planificar la respuesta: {exc}"

		plan_text = getattr(plan_resp, "text", "") or ""
		ultima_respuesta_modelo = plan_text

		try:
			plan = _extract_json_object(plan_text)
		except Exception:
			break

		action = str(plan.get("action") or "").lower()
		if action == "final":
			respuesta_final = str(plan.get("response") or plan.get("final_response") or "").strip()
			if respuesta_final:
				respuesta_limpia = respuesta_final
				guardar_sync = sync_to_async(_guardar_en_historial_sync)
				await guardar_sync(session_id, user_message, respuesta_limpia)
				guardar_en_memoria(user_message, respuesta_limpia, session_id)
				return respuesta_limpia
			break

		tool_name = str(plan.get("tool_name") or plan.get("tool") or "").strip()
		arguments = plan.get("arguments") or {}
		if not tool_name:
			sql_query = str(plan.get("sql_query") or "").strip()
			if sql_query:
				tool_name = "consultar_base_datos"
				arguments = {"sql_query": sql_query}
			else:
				break

		if not isinstance(arguments, dict):
			return "El modelo devolvio argumentos invalidos para la tool."

		if tool_name == "consultar_base_datos" and "sql_query" in arguments:
			try:
				arguments["sql_query"] = _validate_sql(str(arguments.get("sql_query", "")), session_id=session_id)
			except Exception as exc:
				return (
					"No pude generar una consulta SQL valida. "
					f"Detalle: {exc}. Respuesta del modelo: {plan_text[:200]}"
				)

		if tool_name not in {
			"consultar_base_datos",
			"generate_excel_report",
			"verificar_conflicto_horario",
			"busqueda_difusa_nombres",
		}:
			return f"Tool no soportada: {tool_name}"

		try:
			resultado_tool = await _call_mcp_tool(tool_name, arguments)
		except Exception as exc:
			return f"Error ejecutando la tool {tool_name}: {exc}"

		historial_tools.append(_formatear_mcp_resultado(tool_name, resultado_tool))

		if tool_name == "consultar_base_datos":
			try:
				consulta_obj = json.loads(resultado_tool)
				if isinstance(consulta_obj, dict) and consulta_obj.get("rows"):
					if _solicita_reporte_excel(user_message):
						reporte_nombre = _nombre_reporte_desde_pregunta(user_message)
						try:
							excel_resultado = await _call_mcp_tool(
								"generate_excel_report",
								{
									"data_json": json.dumps(consulta_obj, ensure_ascii=False, default=str),
									"report_name": reporte_nombre,
								},
							)
						except Exception as exc:
							return f"Error generando el Excel: {exc}"
						historial_tools.append(_formatear_mcp_resultado("generate_excel_report", excel_resultado))
						url_excel = excel_resultado.strip()
						if url_excel:
							guardar_sync = sync_to_async(_guardar_en_historial_sync)
							await guardar_sync(session_id, user_message, url_excel)
							guardar_en_memoria(user_message, url_excel, session_id)
							return f"Listo. Generé el archivo Excel: {url_excel}"
					arguments_cache = json.dumps(consulta_obj, ensure_ascii=False, default=str)
					historial_tools.append(f"[consultar_base_datos_resumen]\n{arguments_cache}")
			except Exception:
				pass

	final_prompt = (
		"Responde al administrador usando solo la informacion de las tools y la memoria disponible. "
		"No muestres SQL ni detalles internos innecesarios.\n\n"
		f"{contexto_base}\n\n"
		f"<PREGUNTA_ACTUAL>\n{user_message}\n</PREGUNTA_ACTUAL>\n\n"
		f"<RESULTADOS_DE_TOOLS>\n{chr(10).join(historial_tools) if historial_tools else 'Sin resultados.'}\n</RESULTADOS_DE_TOOLS>\n\n"
		"Respuesta:"
	)

	try:
		final_resp = model.generate_content(final_prompt)
	except Exception as exc:
		if historial_tools:
			return (
				"Obtuve datos de las herramientas, pero fallo Gemini al redactar la respuesta. "
				f"Detalle: {exc}\n\n" + "\n\n".join(historial_tools)
			)
		return f"Error al llamar a Gemini para redactar la respuesta: {exc}"

	final_text = getattr(final_resp, "text", "") or ""
	respuesta_limpia = final_text.strip() or ultima_respuesta_modelo.strip() or "Respuesta vacia del modelo."

	guardar_sync = sync_to_async(_guardar_en_historial_sync)
	await guardar_sync(session_id, user_message, respuesta_limpia)
	guardar_en_memoria(user_message, respuesta_limpia, session_id)

	return respuesta_limpia
