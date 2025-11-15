# Ficheiro: mothership/mother_main.py

import threading
import logging
import time
import sys
import os

# --- Importar as FUNÇÕES de serviço ---
from telemetry_server import run_telemetry_server
# from mission_link_server import run_mission_link_server # <<< COMENTADO
# from api_server import run_api_server                   # <<< COMENTADO

# --- Configuração de Logging Simples (para a consola) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# --- 1. Definir o Estado Partilhado (Databases e Locks) ---
g_telemetry_database = {}
g_telemetry_lock = threading.Lock()

# g_rovers_info_lock = threading.Lock() # <<< Pode ser comentado se não for usado


# --- O Bloco Main (A "thread principal") ---
if __name__ == "__main__":
    
    logging.info("[Main] A arrancar Nave-Mãe (Modo Teste Telemetria)...")

    # --- 2. Criar as Threads de Serviço ---

    # Thread 1: Servidor de Telemetria (TCP)
    thread_ts = threading.Thread(
        target=run_telemetry_server, 
        name="Telemetry-TCP",
        args=(g_telemetry_database, g_telemetry_lock)
    )
    
    # --- As outras threads estão comentadas ---
    # Thread 2: Servidor de Mission Link (UDP)
    # thread_ml = threading.Thread(
    #     target=run_mission_link_server,
    #     name="MissionLink-UDP",
    #     args=(g_rovers_info_lock)
    # )
    
    # Thread 3: Servidor da API (HTTP)
    # thread_api = threading.Thread(
    #     target=run_api_server, 
    #     name="API-HTTP",
    #     args=(g_telemetry_database, g_telemetry_lock)
    # )

    # --- 3. Lançar os Serviços ---
    thread_ts.start()
    # thread_ml.start()     # <<< COMENTADO
    # thread_api.start()    # <<< COMENTADO

    logging.info("[Main] Serviço de Telemetria lançado.")

    # --- 4. Manter a Thread Principal Viva ---
    try:
        thread_ts.join()
        # thread_ml.join()
        # thread_api.join()
    except KeyboardInterrupt:
        logging.info("[Main] A desligar Nave-Mãe (Ctrl+C)...")
        sys.exit(0)