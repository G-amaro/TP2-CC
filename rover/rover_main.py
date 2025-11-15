# Ficheiro: rover/rover_main.py

import threading
import logging
import time
import sys
import os
import random

# --- Importar as FUNÇÕES de serviço ---
from telemetry_client import run_telemetry_stream
# from mission_link_client import run_mission_link, do_rover_sync # <<< COMENTADO
# from physics_simulator import run_physics_simulator             # <<< COMENTADO

# --- Configuração de Logging Simples (para a consola) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# --- 1. Definir o Estado Partilhado ---
g_rover_state = {
    "rover_id": None,
    "posicao": (random.uniform(0, 100), random.uniform(0, 100)),
    "bateria": 100.0,
    "estado_op": "idle",
    "missao_atual": None
}
g_state_lock = threading.Lock()


# --- O Bloco Main (A "thread principal") ---
if __name__ == "__main__":
    
    # --- 2. Obter ID do Rover ---
    if len(sys.argv) != 2:
        print("Erro: Forneça o <rover_id> como argumento.")
        sys.exit(1)
        
    ROVER_ID = sys.argv[1]
    
    threading.current_thread().name = f"Main-{ROVER_ID}"
    
    with g_state_lock:
        g_rover_state["rover_id"] = ROVER_ID
        g_rover_state["estado_op"] = "sync"

    logging.info(f"--- A INICIAR ROVER {ROVER_ID} (Modo Teste Telemetria) ---")
    
    # --- 3. Executar Sincronização (FORÇAR SUCESSO) ---
    logging.info("A simular Sincronização (UDP)...")
    # sync_success = do_rover_sync(g_rover_state, g_state_lock) # <<< COMENTADO
    sync_success = True # <<< FORÇAR SUCESSO PARA O TESTE
    
    if not sync_success:
        logging.critical("Falha na sincronização. A desligar.")
        sys.exit(1)
        
    logging.info("Sincronização (Simulada) bem sucedida.")
    with g_state_lock:
        g_rover_state["estado_op"] = "parado"

    # --- 4. Criar as Threads de Serviço ---
    
    # Thread 1: Cliente de Telemetria (TCP)
    thread_ts = threading.Thread(
        target=run_telemetry_stream,
        name=f"Telemetry-{ROVER_ID}",
        args=(g_rover_state, g_state_lock)
    )

    # Thread 2: Cliente de Mission Link (UDP)
    # thread_ml = threading.Thread(
    #     target=run_mission_link,
    #     name=f"MissionLink-{ROVER_ID}",
    #     args=(g_rover_state, g_state_lock)
    # )

    # --- 5. Lançar os Serviços ---
    thread_ts.start()
    # thread_ml.start() # <<< COMENTADO

    logging.info("[Main] Serviço de Telemetria lançado.")

    # --- 6. Manter a Thread Principal Viva ---
    # (Sem a física, apenas esperamos pela thread de telemetria)
    try:
        thread_ts.join()
        # thread_ml.join()
    except KeyboardInterrupt:
        logging.info("[Main] A desligar Rover (Ctrl+C)...")
        sys.exit(0)