import threading
import logging
import time
import sys
import os
import random

from telemetry_client import run_telemetry_stream
from sync_rover import sync
from mission_link_client import run_mission_link_rover
from physics_simulator import run_physics_simulator            


file_dir = os.path.dirname(__file__)
log_path = os.path.join(file_dir, "../logs/recorder.log")


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path, mode='a'),
        logging.StreamHandler(sys.stdout)]
)

physics_log = logging.getLogger('Physics')
physics_log.setLevel(logging.DEBUG)

# [NOTA DE IMPLEMENTAÇÃO - MEMÓRIA PARTILHADA & MUTEX]
# Este dicionário 'g_rover_state' atua como a memória central do Rover.
# É acedido concorrentemente por 3 threads distintas:
# 1. Physics (Escrita): Atualiza bateria e muda estado para 'low_power'.
# 2. MissionLink (Leitura/Escrita): Lê estado para decidir pedir missões, escreve 'em_missao'.
# 3. Telemetry (Leitura): Lê tudo para enviar para a Nave-Mãe.
#
# O 'g_state_lock' é o mecanismo de sincronização que impede corrupção de dados.
g_rover_state = {
    "rover_id": None,
    "posicao": (random.uniform(0, 100), random.uniform(0, 100)),
    "bateria": 100.0,
    "estado_op": "parado",
    "missao_atual": None
}
g_state_lock = threading.Lock()

# [NOTA DE IMPLEMENTAÇÃO - BOOTSTRAP & HANDSHAKE]
# O processo de arranque segue uma ordem estrita:
# 1. Sincronização (Bloqueante): O Rover não faz nada até receber um ID da Nave-Mãe.
#    Isto garante que não "poluímos" a rede com tráfego não autorizado.
# 2. Configuração: Só depois do 'sync' bem sucedido é que inicializamos o ID no estado.
if __name__ == "__main__":

    logging.info("A simular Sincronização (UDP)...")
    ROVER_ID = sync()
    #ROVER_ID = "1" --> Simulação direta sem sync (Para teste)

    if not ROVER_ID:
        logging.critical("Falha na sincronização. A desligar.")
        sys.exit(1)

    threading.current_thread().name = f"Main-{ROVER_ID}"
    logging.info("Sincronização (Simulada) bem sucedida.")
    with g_state_lock:

        g_rover_state["rover_id"] = ROVER_ID
        g_rover_state["estado_op"] = "parado"

    thread_ts = threading.Thread(
        target=run_telemetry_stream,
        name=f"Telemetry-{ROVER_ID}",
        args=(g_rover_state, g_state_lock),
        daemon=True
    )

    thread_ml = threading.Thread(
        target=run_mission_link_rover,
        name=f"MissionLink-{ROVER_ID}",
        args=(g_rover_state, g_state_lock, ROVER_ID),
        daemon=True
    )

    thread_phys = threading.Thread(
        target=run_physics_simulator,
        name=f"Physics-{ROVER_ID}",
        args=(g_rover_state, g_state_lock),
        daemon=True
    )

    thread_ts.start()
    thread_phys.start()
    thread_ml.start()

    logging.info("[Main] Serviço de Telemetria e Física lançados.")

    try:
        thread_ts.join()
        thread_phys.join()
        thread_ml.join()
    except KeyboardInterrupt:
        logging.info("[Main] A desligar Rover (Ctrl+C)...")
        sys.exit(0)