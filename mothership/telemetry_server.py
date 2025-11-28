# Ficheiro: mothership/telemetry_server.py

import socket
import threading
import logging
import time
import json  
import os    

TELEMETRY_PORT = 50010
HOST = '0.0.0.0'

# --- Definição do Protocolo (39 Bytes) ---
ID_W, POS_W, BAT_W, STATE_W, MISSION_W = 2, 5, 5, 12, 10
TOTAL_MSG_SIZE = ID_W + (POS_W * 2) + BAT_W + STATE_W + MISSION_W 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'telemetry_data')

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def recv_all(sock, n):
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet: return None
        data += packet
    return data

def save_telemetry_to_file(rover_id, data):
    
    filename = f"rover_{rover_id}_history.json"
    filepath = os.path.join(DATA_DIR, filename)
    
    try:
        with open(filepath, "a") as f:
            json.dump(data, f)
            f.write('\n') 
    except Exception as e:
        logging.getLogger('telemetry').error(f"Erro a gravar ficheiro JSON para Rover {rover_id}: {e}")

def handle_rover_telemetry(client_socket, rover_addr, db, lock):
    log = logging.getLogger('telemetry')
    log.info(f"Handler iniciado para {rover_addr}")
    
    try:
        while True:
            msg_bytes = recv_all(client_socket, TOTAL_MSG_SIZE)
            
            if not msg_bytes:
                log.warning(f"Rover {rover_addr} desligou-se.")
                break
            
            try:
                msg = msg_bytes.decode('utf-8')
            except UnicodeDecodeError:
                log.error(f"Erro decode bytes de {rover_addr}")
                continue

            cursor = 0
            id_str = msg[cursor : cursor + ID_W]; cursor += ID_W
            x_str  = msg[cursor : cursor + POS_W]; cursor += POS_W
            y_str  = msg[cursor : cursor + POS_W]; cursor += POS_W
            bat_str= msg[cursor : cursor + BAT_W]; cursor += BAT_W
            est_str= msg[cursor : cursor + STATE_W]; cursor += STATE_W
            mis_str= msg[cursor : cursor + MISSION_W]

            try:
                r_id = int(id_str.strip())
                r_x = float(x_str.strip())
                r_y = float(y_str.strip())
                r_bat = float(bat_str.strip())
                r_est = est_str.strip()
                r_mis = mis_str.strip()
                
                telemetry_data = {
                    "rover_id": r_id,
                    "last_seen": time.time(),
                    "posicao": (r_x, r_y),
                    "bateria": r_bat,
                    "estado": r_est,
                    "missao": r_mis
                }

                log.info(f"RX Rover {r_id}: Pos({r_x},{r_y}) Bat({r_bat}%) Est({r_est})")
                
                with lock:
                    db[str(r_id)] = telemetry_data 

                save_telemetry_to_file(r_id, telemetry_data)

            except ValueError as e:
                log.error(f"Erro parse dados: {e}. Msg crua: '{msg}'")

    except Exception as e:
        log.error(f"Erro no handler {rover_addr}: {e}")
    finally:
        client_socket.close()


def run_telemetry_server(db, lock):
    log = logging.getLogger('telemetry')
    try:
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, TELEMETRY_PORT))
        server_sock.listen()
        log.info(f"Servidor Telemetria à escuta na porta {TELEMETRY_PORT}")
        
        while True:
            c, a = server_sock.accept()
            t = threading.Thread(target=handle_rover_telemetry, args=(c, a, db, lock), daemon=True)
            t.start()
    except Exception as e:
        log.critical(f"Servidor CRASHOU: {e}")
    finally:
        if 'server_sock' in locals(): server_sock.close()