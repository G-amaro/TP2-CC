import socket
import threading
import os
import logging
import time

# [NOTA DE IMPLEMENTAÇÃO - DESCOBERTA E ATRIBUIÇÃO DE ID]
# Esta função implementa o handshake inicial (Bootstrap) do Rover.
#
# 1. Protocolo de Descoberta (UDP):
#    - O Rover não sabe o seu ID ao iniciar. Envia um pedido genérico ("Req")
#      para a Nave-Mãe na porta 50000.
#    - A Nave-Mãe responde com "A" + ID (ex: "A01"), atribuindo a identidade ao Rover.
#
# 2. Fiabilidade no Arranque:
#    - Usamos um mecanismo de retransmissão com "Exponential Backoff" (espera 2s, 4s, 8s...).
#    - Isto é crítico porque se o pacote "Req" se perder no arranque, o Rover ficaria
#      inutilizável. O loop garante robustez contra perdas iniciais na rede.
#
# 3. Configuração de Thread:
#    - Atualiza o nome da thread atual para incluir o ID recebido, facilitando o
#      debugging nos logs (ex: de "Sync" para "Sync-01").
def sync():

    threading.current_thread().name = f"Sync"

    SYNC_PORT = 50000
    MOTHER_IP = '10.0.2.20'

    msg_type = "Req"
    msg_str = f"{msg_type}"
    message = msg_str.encode('utf-8')

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', 0))

    sending_max_times = 5
    timeout = 2
    time_sleep = 2

    while sending_max_times > 0:

        sock.sendto(message, (MOTHER_IP, SYNC_PORT))
        sending_max_times-=1

        sock.settimeout(timeout)

        try:

            data, addr = sock.recvfrom(32)
            logging.debug(f"Sync Rover recebeu dados: {data}")


            response_data= data.decode('utf-8')

            if(len(response_data) < 3):
                continue

            response_type = response_data[0] #
            response_rover_id = response_data[1:3]

            threading.current_thread().name = f"Sync-{response_rover_id}"

            if response_type == "A":
                logging.info(f"Nave Mae({addr[0]}:{addr[1]}) -> Rover {response_rover_id}  : sync ack")
                sock.close()
                return response_rover_id

        except socket.timeout:
            time.sleep(time_sleep)
            time_sleep *= 2
            continue
        except Exception as e:
            logging.error(f" Erro no sync: {e}.")

    logging.error(f"Rover "+ str(response_rover_id) + ": Max number of sync tries with mothership exceeded. Sync ACK missing.")

    sock.close()
    return False