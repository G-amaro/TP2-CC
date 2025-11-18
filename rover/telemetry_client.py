import socket
import time
import logging

# --- Constantes de Rede ---
MOTHER_IP = '10.0.2.20'
TELEMETRY_PORT = 50010
SEND_INTERVAL = 5

# --- Definição do Protocolo (39 Bytes) ---
ID_W, POS_W, BAT_W, STATE_W, MISSION_W = 2, 5, 5, 12, 10
TOTAL_MSG_SIZE = ID_W + (POS_W * 2) + BAT_W + STATE_W + MISSION_W 

def run_telemetry_stream(state, lock):
    log = logging.getLogger('telemetry') # Usar logger configurado no main
    log.info(f"Thread Telemetria iniciada (Protocolo Fixo: {TOTAL_MSG_SIZE} bytes).")
    sock = None

    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            log.info(f"A ligar a {MOTHER_IP}:{TELEMETRY_PORT}...")
            sock.connect((MOTHER_IP, TELEMETRY_PORT))
            log.info("Ligado!")

            while True:
                with lock:
                    # Copiar dados para evitar bloquear a thread principal
                    st = state.copy() 
                
                # --- A. Formatar Dados (Padding) ---
                
                # 1. ID (2 chars)
                id_str = str(st["rover_id"]).rjust(ID_W)

                # 2. Posição (Separar X e Y, 5 chars cada)
                x, y = st["posicao"]
                pos_x_str = f"{x:.1f}".rjust(POS_W)
                pos_y_str = f"{y:.1f}".rjust(POS_W)

                # 3. Bateria (5 chars)
                bat_str = f"{st['bateria']:.1f}".rjust(BAT_W)

                # 4. Estado (12 chars)
                est_str = str(st["estado_op"]).ljust(STATE_W)

                # 5. Missão (10 chars) - Tratar se for None
                missao_raw = st.get("missao_atual")
                if missao_raw is None:
                    missao_raw = "Nenhuma"
                miss_str = str(missao_raw).ljust(MISSION_W)

                # --- B. Montar Mensagem ---
                final_str = id_str + pos_x_str + pos_y_str + bat_str + est_str + miss_str
                
                # Codificar para bytes (Método do Professor)
                msg_bytes = final_str.encode('utf-8')

                # Validação de segurança
                if len(msg_bytes) != TOTAL_MSG_SIZE:
                    log.error(f"Erro tamanho mensagem: tem {len(msg_bytes)}, esperava {TOTAL_MSG_SIZE}")
                    # (Opcional: cortar ou rejeitar)
                
                # --- C. Enviar ---
                sock.sendall(msg_bytes)
                log.info(f"Enviado: ID={id_str}|Pos=({pos_x_str},{pos_y_str})|Bat={bat_str}|Est={est_str.strip()}|Mis={miss_str.strip()}")

                time.sleep(SEND_INTERVAL)

        except (socket.error, ConnectionRefusedError, BrokenPipeError) as e: 
            log.warning(f"Ligação perdida ({e}). A tentar em 10s...")
            if sock: sock.close()
            time.sleep(10)
        except Exception as e:
            log.error(f"Erro fatal na telemetria: {e}", exc_info=True)
            if sock: sock.close()
            time.sleep(10)