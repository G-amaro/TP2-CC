import threading
import logging
import time
import sys
import os
import shutil
import json

from telemetry_server import run_telemetry_server, DATA_DIR
from sync_mother import sync
from mission_link_mother import run_mission_link_mother
from api_server import run_api_server

file_dir = os.path.dirname(__file__)
log_path = os.path.join(file_dir, "../logs/recorder.log")
info_dir = os.path.join(file_dir, "../info")
os.makedirs(os.path.dirname(log_path), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_path, mode='w'), logging.StreamHandler(sys.stdout)]
)

# [NOTA DE IMPLEMENTAÇÃO - MEMÓRIA PARTILHADA & CONCORRÊNCIA]
# Este bloco define o estado global do sistema, acessível por todas as threads.
#
# 1. g_telemetry_database: Dicionário que guarda o estado mais recente de cada Rover.
#    - Escrito por: Thread Telemetry-TCP (freq alta).
#    - Lido por: Thread Mission_Link-UDP (para validar bateria) e API-HTTP (para dashboard).
#
# 2. g_missions_list: Lista de missões pendentes carregadas do JSON.
#    - Modificado por: Thread Mission_Link-UDP (remove missões à medida que atribui).
#
# 3. Locks (g_telemetry_lock, g_missions_lock): Mutexes obrigatórios para garantir
#    "Thread-Safety". Impedem que uma thread leia dados enquanto outra está a escrever,
#    evitando corrupção de memória ou comportamentos imprevisíveis.
g_telemetry_database = {}
g_telemetry_lock = threading.Lock()

g_missions_list = []      
g_completed_missions = [] 
g_missions_lock = threading.Lock()

def carregar_missoes_iniciais():
    f_missoes = os.path.join(info_dir, "missions.json")
    f_completas = os.path.join(info_dir, "completed_missions.json")
    
    with g_missions_lock:
        if os.path.exists(f_missoes):
            try:
                with open(f_missoes, 'r') as f:
                    conteudo = f.read()
                    if conteudo.strip(): g_missions_list.extend(json.loads(conteudo))
            except Exception as e:
                logging.error(f"Erro ao carregar missions.json: {e}")

        with open(f_completas, 'w') as f:
            json.dump([], f)

# [NOTA DE IMPLEMENTAÇÃO - GRACEFUL SHUTDOWN]
# Garante que o sistema deixa o ambiente limpo ao encerrar.
# Remove ficheiros temporários e logs antigos para garantir que a próxima execução
# começa com um estado "limpo" e determinístico.
def cleanup_all_data():
    logging.info("A limpar TODOS os ficheiros...")
    if os.path.exists(DATA_DIR):
        try:
            shutil.rmtree(DATA_DIR)
            os.makedirs(DATA_DIR)
        except Exception: pass

    files_to_delete = ["rovers_info.json", "completed_missions.json"]
    if os.path.exists(info_dir):
        for file in files_to_delete:
            path = os.path.join(info_dir, file)
            if os.path.exists(path):
                try: os.remove(path)
                except Exception: pass

    logging.shutdown()

    if os.path.exists(log_path):
        try:
            os.remove(log_path)
        except Exception as e:
            print(f"erro ao eliminar log: {e}")

# [NOTA DE IMPLEMENTAÇÃO - ORQUESTRAÇÃO DE SERVIÇOS]
# O Main Thread atua apenas como gestor de arranque.
#
# 1. Arquitetura Multi-Thread: Lançamos 4 serviços independentes em paralelo:
#    - Sync (UDP Broadcast): Descoberta de rovers.
#    - Telemetry (TCP Server): Receção de dados contínuos.
#    - Mission Link (UDP Server): Gestão fiável de missões.
#    - API (HTTP Server): Interface para o mundo exterior.
#
# 2. Daemon Threads: Todas as threads são configuradas como 'daemon=True'.
#    Isto significa que se o Main Thread encerrar (via Ctrl+C), todas as threads
#    filhas são mortas automaticamente pelo SO, evitando processos "zombies".
if __name__ == "__main__":
    logging.info("[Main] A arrancar Nave-Mãe...")
    carregar_missoes_iniciais() 

    thread_sync = threading.Thread(target=sync, name="Sync", args=(), daemon=True)

    thread_ts = threading.Thread(
        target=run_telemetry_server, 
        name="Telemetry-TCP",
        args=(g_telemetry_database, g_telemetry_lock),
        daemon=True
    )

    thread_ml = threading.Thread(
        target=run_mission_link_mother,
        name="Mission_Link-UDP",
        args=(g_telemetry_database, g_telemetry_lock, g_missions_list, g_completed_missions, g_missions_lock),
        daemon=True
    )

    thread_api = threading.Thread(
        target=run_api_server,
        name="API-HTTP",
        args=(g_telemetry_database, g_telemetry_lock, g_missions_list, g_completed_missions, g_missions_lock), 
        daemon=True
    )

    thread_sync.start()
    thread_ts.start()
    thread_ml.start()
    thread_api.start()

    logging.info("[Main] Serviço lançado.")

    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        logging.info("[Main] A desligar...")
        cleanup_all_data()
        sys.exit(0)