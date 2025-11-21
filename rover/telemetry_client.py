import socket
import time
import logging
import sys 

MOTHER_IP = '10.0.2.20'
TELEMETRY_PORT = 50010
SEND_INTERVAL = 5

# --- Definição do Protocolo (39 Bytes) ---
ID_W, POS_W, BAT_W, STATE_W, MISSION_W = 2, 5, 5, 12, 10
TOTAL_MSG_SIZE = ID_W + (POS_W * 2) + BAT_W + STATE_W + MISSION_W 
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 10 


def run_telemetry_stream(state, lock):
    log = logging.getLogger('telemetry')
    log.info(f"Thread Telemetria iniciada (Protocolo Fixo: {TOTAL_MSG_SIZE} bytes).")
    
    sock = None

    reconnect_attempts = 0

    while reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
        try:

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            log.info(f"A ligar a {MOTHER_IP}:{TELEMETRY_PORT}...")
            sock.connect((MOTHER_IP, TELEMETRY_PORT))
            
            log.info("Ligado! Reiniciando contador de falhas.")
            reconnect_attempts = 0

            while True:
                
                with lock:
                    st = state.copy() 
                
                id_str = str(st["rover_id"]).rjust(ID_W)
                x, y = st["posicao"]
                pos_x_str = f"{x:.1f}".rjust(POS_W)
                pos_y_str = f"{y:.1f}".rjust(POS_W)
                bat_str = f"{st['bateria']:.1f}".rjust(BAT_W)
                est_str = str(st["estado_op"]).ljust(STATE_W)
                
                missao_raw = st.get("missao_atual")
                if missao_raw is None: missao_raw = "Nenhuma"
                miss_str = str(missao_raw).ljust(MISSION_W)

                final_str = id_str + pos_x_str + pos_y_str + bat_str + est_str + miss_str
                
                msg_bytes = final_str.encode('utf-8')

                if len(msg_bytes) != TOTAL_MSG_SIZE:
                    log.error(f"Erro tamanho mensagem: tem {len(msg_bytes)}, esperava {TOTAL_MSG_SIZE}")

                sock.sendall(msg_bytes)
                log.info(f"Enviado: ID={id_str}|Pos=({pos_x_str},{pos_y_str})|Bat={bat_str}|Est={est_str.strip()}|Mis={miss_str.strip()}")

                time.sleep(SEND_INTERVAL)
        
        except (socket.error, ConnectionRefusedError, BrokenPipeError, ConnectionResetError, TimeoutError) as e: 
            
            reconnect_attempts += 1
            log.warning(f"Erro na Telemetria ({e}). Tentativa {reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS}. A tentar religar em {RECONNECT_DELAY} seg...")

            if sock: sock.close()
            time.sleep(RECONNECT_DELAY)
            
        except KeyboardInterrupt:
            log.info("Interrupção recebida. A desligar serviço de telemetria.")
            break 
            
        except Exception as e:
            log.error(f"Erro fatal na telemetria: {e}", exc_info=True)
            reconnect_attempts = MAX_RECONNECT_ATTEMPTS 

    if reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
        log.critical(f"Limite máximo de {MAX_RECONNECT_ATTEMPTS} tentativas de reconexão excedido. O Rover está a desligar o serviço de telemetria.")

    log.info("Thread de Telemetria terminada.")