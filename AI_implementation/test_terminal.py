# test_terminal.py

import asyncio
import traceback
from AI_implementation.ai_orchestrator import get_ai_response

async def simular_chat():
    print("="*50)
    print("🤖 SIMULADOR DE CHAT - ADMIN DE MONITORES")
    print("Conectado a PostgreSQL vía MCP y a Qwen vía Ollama Cloud")
    print("Escribe 'salir' para terminar la simulación.")
    print("="*50)

    while True:
        # 1. Leer la pregunta del usuario
        pregunta = input("\n🧑‍💻 Admin: ")
        
        # 2. Condición para salir del bucle
        if pregunta.lower() in ['salir', 'exit', 'quit']:
            print("👋 Saliendo del simulador...")
            break
            
        if not pregunta.strip():
            continue

        print("⏳ Pensando y consultando la base de datos...")
        
        try:
            # 3. Llamar a nuestro orquestador asíncrono
            respuesta = await get_ai_response(pregunta)
            
            # 4. Imprimir la respuesta de la IA
            print(f"\n🤖 Bot:\n{respuesta}")
            
        except Exception as e:
            print(f"\n❌ Error durante la ejecución: {e}")
            # Esto imprimirá Todo el rastro del error con lujo de detalles
            traceback.print_exc()

if __name__ == "__main__":
    # Como get_ai_response es una función asíncrona (async/await), 
    # necesitamos asyncio para ejecutarla en un script normal.
    asyncio.run(simular_chat())