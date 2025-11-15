import socket
import json
import time
import logging

# --- Constantes de Rede ---
# (Estas poderiam ser importadas de um ficheiro de config,
# mas para este trabalho, podem ficar aqui)
MOTHER_IP = '10.0.2.20'
TELEMETRY_PORT = 50010  # Porta TCP (a mesma do telemetry_server.py)
SEND_INTERVAL = 5       # Enviar telemetria a cada 5 segundos

def run_telemetry_stream(state, lock):
    """
    Esta é a função de "target" para a Thread de Telemetria do Rover.
    
    1. Tenta ligar-se ao servidor TCP da Nave-Mãe.
    2. Se conseguir, entra em loop e envia dados de estado a cada X seg.
    3. Se a ligação falhar, tenta religar-se.
    """
    # Obter o logger. Se o main configurou um, isto vai para o ficheiro.
    # Se não, vai para a consola.
    log = logging.getLogger(__name__) # Usar __name__ é boa prática

    log.info("Thread de Telemetria (TCP) iniciada.")

    # A variável 'sock' tem de ser gerida dentro do loop
    # para que seja recriada em cada tentativa de ligação.
    sock = None

    while True:
        try:
            # --- 1. Criar e Ligar o Socket ---
            # AF_INET = IPv4, SOCK_STREAM = TCP
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            log.info(f"A tentar ligar ao servidor de Telemetria em {MOTHER_IP}:{TELEMETRY_PORT}...")
            sock.connect((MOTHER_IP, TELEMETRY_PORT))
            log.info(f"Ligado ao servidor de Telemetria!")

            # --- 2. Loop de Envio (enquanto estiver ligado) ---
            while True:
                
                # --- A. Ler o estado partilhado ---
                with lock:
                    # Criamos uma cópia para não segurar o lock
                    # enquanto preparamos e enviamos a msg
                    state_copy = state.copy() 
                
                # --- B. Preparar a mensagem ---
                telemetry_data = {
                    "rover_id": state_copy["rover_id"],
                    "timestamp": time.time(),
                    "posicao": state_copy["posicao"],
                    "estado": state_copy["estado_op"],
                    "bateria": round(state_copy["bateria"], 2)
                }
                
                # --- C. Formatar e Enviar ---
                # Usamos json.dumps para criar a string
                # Adicionamos '\n' como delimitador (o nosso protocolo)
                message_str = json.dumps(telemetry_data) + '\n'
                
                # Convertemos a string para bytes (utf-8) e enviamos
                sock.sendall(message_str.encode('utf-8'))
                
                log.info(f"Telemetria enviada: {telemetry_data['estado']}, Bat: {telemetry_data['bateria']:.1f}%")

                time.sleep(SEND_INTERVAL)

        except (socket.error, ConnectionRefusedError, BrokenPipeError, ConnectionResetError, TimeoutError) as e: 
            log.warning(f"Erro na Telemetria ({e}). A tentar religar em 10 seg...")
            
        except KeyboardInterrupt:
            log.info("A desligar thread de telemetria.")
            break # Sair do loop 'while True' principal
            
        except Exception as e:
            log.error(f"Erro inesperado na telemetria: {e}", exc_info=True)

        finally:
            # --- 3. Limpar antes de tentar religar ---
            if sock:
                sock.close() # Importante fechar o socket antigo
            log.info("Socket de telemetria fechado. A aguardar 10s.")
            time.sleep(10) # Esperar 10s antes de tentar o 'connect' de novo