import socket
import sys
import os
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mission_link import header_parser, header_builder

ML_PORT = 50001
HOST = '0.0.0.0'

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