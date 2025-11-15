# Ficheiro: mothership/telemetry_server.py

import socket
import threading
import json
import logging

# Constantes para este módulo
TELEMETRY_PORT = 50010  # Porta TCP
HOST = '0.0.0.0'       # Ouvir em todas as interfaces

def handle_rover_telemetry(client_socket, rover_addr, db, lock):
    """
    Esta função corre numa THREAD SEPARADA para cada rover.
    Recebe e processa dados de telemetria de UM rover específico.
    """
    # Obter o logger de telemetria (que o main configurou)
    log = logging.getLogger('telemetry')
    
    rover_id = f"ID_Desconhecido@{rover_addr[0]}"
    log.info(f"Nova ligação handler criada para {rover_addr}")

    try:
        # Usar makefile() é a forma mais fácil de ler "linha a linha" (até ao '\n')
        # 'r' = modo de leitura, 'utf-8' = encoding
        client_file = client_socket.makefile('r', encoding='utf-8')
        
        # Este loop 'for' bloqueia até receber uma linha completa (terminada em \n)
        for line in client_file:
            
            # 1. Tentar fazer parse do JSON
            try:
                telemetry_data = json.loads(line)
                
                # Obter o ID do rover (e usá-lo para logging futuro)
                rover_id = telemetry_data.get("rover_id", rover_id) 
                
                log.info(f"Recebido de {rover_id}: Estado={telemetry_data['estado']}, Bat={telemetry_data['bateria']:.1f}%")

                # 2. Atualizar a "base de dados" global de forma segura
                # O 'lock' é passado a partir do main
                with lock:
                    # 'db' é o g_telemetry_database do main
                    db[rover_id] = telemetry_data
                    
            except json.JSONDecodeError:
                log.warning(f"Recebida mensagem mal formatada (não-JSON) de {rover_id}")
            except KeyError as e:
                log.warning(f"Mensagem de {rover_id} não tinha a chave esperada: {e}")

    except (socket.error, BrokenPipeError, ConnectionResetError):
        log.warning(f"Ligação perdida com {rover_addr} (Rover: {rover_id})")
    except Exception as e:
        log.error(f"Erro inesperado no handler de {rover_addr} (Rover: {rover_id}): {e}")
    finally:
        # 3. Limpar
        log.info(f"A fechar ligação handler com {rover_addr} (Rover: {rover_id})")
        with lock:
            # Opcional: Marcar rover como 'offline' na BD
            if rover_id in db:
                db[rover_id]["estado"] = "offline"
        
        client_socket.close()
        # A thread termina aqui


def run_telemetry_server(db, lock):
    """
    Esta é a função "Rececionista" (Thread B).
    É o ponto de entrada chamado pelo 'mother_main.py'.
    
    A sua única tarefa é aceitar novas ligações TCP
    e lançar threads "Handler" para cuidar delas.
    """
    # Obter o logger de telemetria
    log = logging.getLogger('telemetry')
    
    try:
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # SO_REUSEADDR permite reiniciar o servidor rapidamente
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        server_sock.bind((HOST, TELEMETRY_PORT))
        server_sock.listen()
        
        log.info(f"Servidor de Telemetria (TCP) à escuta na porta {TELEMETRY_PORT}...")

        while True:
            # 1. 'accept()' bloqueia até um novo rover se ligar
            client_sock, addr = server_sock.accept()
            log.info(f"Nova ligação de {addr}. A criar thread handler...")
            
            # 2. Criar e lançar a thread "Handler" para este cliente
            handler_thread = threading.Thread(
                target=handle_rover_telemetry, 
                args=(client_sock, addr, db, lock), # Passar a BD e o Lock
                name=f"Handler-{addr[0]}",
                daemon=True  # Permite ao programa fechar mesmo se as threads estiverem a correr
            )
            handler_thread.start()

    except Exception as e:
        log.critical(f"Servidor de Telemetria (TCP) CRASHOU: {e}", exc_info=True)
    finally:
        log.info("Servidor de Telemetria (TCP) a desligar.")
        if 'server_sock' in locals():
            server_sock.close()