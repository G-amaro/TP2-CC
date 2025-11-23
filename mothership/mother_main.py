import threading
import logging
import time
import sys
import os
import shutil

from telemetry_server import run_telemetry_server, DATA_DIR
from sync_mother import sync
from mission_link_mother import run_mission_link_mother
# from api_server import run_api_server

file_dir = os.path.dirname(__file__)
log_path = os.path.join(file_dir, "../logs/recorder.log")

# --- Configuração de Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path, mode='a'),
        logging.StreamHandler(sys.stdout)]
)


g_telemetry_database = {}
g_telemetry_lock = threading.Lock()
# g_rovers_info_lock = threading.Lock()

# --- FUNÇÃO DE LIMPEZA ---
def cleanup_telemetry_data():
    """Apaga os ficheiros de histórico de telemetria gerados."""
    logging.info("A limpar ficheiros de telemetria...")
    
    # Opção 1: Apagar a pasta inteira e recriá-la
    if os.path.exists(DATA_DIR):
        try:
            shutil.rmtree(DATA_DIR) # Apaga a pasta e tudo o que lá está
            os.makedirs(DATA_DIR)   # Recria a pasta vazia para a próxima vez
            logging.info(f"Pasta {DATA_DIR} limpa com sucesso.")
        except Exception as e:
            logging.error(f"Erro ao limpar dados: {e}")

# --- Bloco Main ---
if __name__ == "__main__":
    
    logging.info("[Main] A arrancar Nave-Mãe (Modo Teste)...")

    thread_sync = threading.Thread(
        target=sync,
        name="Sync",
        args=(),
        daemon = True # se a main for eliminada, nao se torna uma thread zombi
    )

    thread_ts = threading.Thread(
        target=run_telemetry_server, 
        name="Telemetry-TCP",
        args=(g_telemetry_database, g_telemetry_lock),
        daemon = True
    )

    thread_ml = threading.Thread(
        target=run_mission_link_mother,
        name="Mission_Link-UDP",
        args=(g_telemetry_database, g_telemetry_lock),
        daemon=True
    )

    thread_sync.start()
    thread_ts.start()
    thread_ml.start()
    # thread_api.start()

    logging.info("[Main] Serviço lançado.")

    # --- Manter Vivo ---
    try:
        while True:
            time.sleep(1)
        
    except KeyboardInterrupt:
        print("\n") # Só para dar uma quebra de linha visual
        logging.info("[Main] Interrupção recebida (Ctrl+C).")
        
        # --- CHAMAR LIMPEZA AQUI ---
        cleanup_telemetry_data()
        
        logging.info("[Main] A desligar Nave-Mãe.")
        sys.exit(0)