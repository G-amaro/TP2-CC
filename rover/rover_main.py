import threading
import logging
import time
import sys
import os
import random

from telemetry_client import run_telemetry_stream
from sync_rover import sync
# from mission_link_client import run_mission_link, do_rover_sync 
# from physics_simulator import run_physics_simulator             


file_dir = os.path.dirname(__file__)
log_path = os.path.join(file_dir, "../logs/recorder.log")


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path, mode='a'),
        logging.StreamHandler(sys.stdout)]
)

g_rover_state = {
    "rover_id": None,
    "posicao": (random.uniform(0, 100), random.uniform(0, 100)),
    "bateria": 100.0,
    "estado_op": "idle",
    "missao_atual": None
}
g_state_lock = threading.Lock()

if __name__ == "__main__":
    
    if len(sys.argv) != 2:
        print("Erro: Forneça o <rover_id> como argumento.")
        sys.exit(1)
        
    ROVER_ID = sys.argv[1]
    
    with g_state_lock:
        g_rover_state["rover_id"] = ROVER_ID
        g_rover_state["estado_op"] = "sync"


    logging.info("A simular Sincronização (UDP)...")
    sync_success = sync(ROVER_ID) 
    threading.current_thread().name = f"Main-{ROVER_ID}"

    if not sync_success:
        logging.critical("Falha na sincronização. A desligar.")
        sys.exit(1)
        
    logging.info("Sincronização (Simulada) bem sucedida.")
    with g_state_lock:
        g_rover_state["estado_op"] = "parado"


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

    thread_ts.start()
    # thread_ml.start() 

    logging.info("[Main] Serviço de Telemetria lançado.")

    # --- 6. Manter a Thread Principal Viva ---
    # (Sem a física, apenas esperamos pela thread de telemetria)
    try:
        thread_ts.join()
        # thread_ml.join()
    except KeyboardInterrupt:
        logging.info("[Main] A desligar Rover (Ctrl+C)...")
        sys.exit(0)