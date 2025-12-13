import socket
import sys
import os
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mission_link import header_parser, header_builder

ML_PORT = 50001
HOST = '0.0.0.0'

# [NOTA DE IMPLEMENTAÇÃO - INTEGRAÇÃO & "CHAOS ENGINEERING"]
# Este script atua como um "Fault Injector" (Injetor de Falhas).
# Substitui a Nave-Mãe real para validar a robustez do Rover.
#
# 1. Teste Determinístico: Em vez de usar perda de pacotes aleatória (ex: 20%),
#    que é difícil de reproduzir, este servidor ignora propositadamente as
#    primeiras 2 mensagens de CADA sequência.
#
# 2. Objetivo: Obrigar o Rover a entrar em Timeout e disparar a lógica de
#    retransmissão (Stop-and-Wait) implementada no 'mission_link_client.py'.
#
# 3. Critério de Sucesso: Se o Rover conseguir completar a troca de mensagens
#    à 3ª tentativa, provamos que o mecanismo de fiabilidade funciona.
def run_chaos_server():
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - [MÃE-CAOS] - %(message)s'
    )
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, ML_PORT))
    
    logging.info(f"--- SERVIDOR DE CAOS INICIADO NA PORTA {ML_PORT} ---")
    logging.info("Vou ignorar as primeiras 2 mensagens de cada sequência para TESTAR RETRANSMISSÕES.")

    tentativas = {}

    while True:
        try:
            data, addr = sock.recvfrom(4096)
            
            msg = header_parser(data)
            if not msg:
                logging.warning("Recebi lixo (ignorado).")
                continue
                
            rover_id = msg['rover_id']
            seq = msg['seq']
            msg_type = msg['message_type']
            
            key = (rover_id, seq)
            
            count = tentativas.get(key, 0) + 1
            tentativas[key] = count
            
            print(f"\n>> Recebido '{msg_type}' do Rover {rover_id} (Seq {seq}). Esta é a tentativa #{count}.")

            if count < 3:
                logging.warning(f"   [X] A IGNORAR (Simulação de Perda). O Rover deve retransmitir (Timeout).")
            else:
                logging.info(f"   [V] A RESPONDER (Sucesso). O Rover deve ficar feliz.")
                
                response = header_builder(rover_id, 0, seq, "MAck", "")
                sock.sendto(response, addr)
                
                logging.info(f"   -> ACK enviado para {addr}")

        except KeyboardInterrupt:
            logging.info("Teste terminado.")
            break
        except Exception as e:
            logging.error(f"Erro: {e}")

if __name__ == "__main__":
    run_chaos_server()