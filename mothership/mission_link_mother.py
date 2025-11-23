import sys
import os
import socket
import json
import logging
import threading
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mission_link import header_builder, header_parser,  mission_packer, report_parser, report_packer

ML_PORT=50001

def save_mission_complete(payload_dict):
    file_dir = os.path.dirname(__file__)
    json_file = os.path.join(file_dir, '../info/completed_missions.json')

    history = []
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            history = json.load(f)

    payload_dict["received_at"] = str (datetime.now())
    history.append(payload_dict)

    with open(json_file, 'w') as f:
        json.dump(history, f, indent=4)

    logging.info(f"Mission {payload_dict.get('id_missao')} save complete")


def run_mission_link_mother(status_db, lock_status):
    threading.current_thread().name = f"Mission Link Mother"

    file_dir = os.path.dirname(__file__)
    json_path = os.path.join(file_dir, "../info/missions.json")

    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            missions = json.load(f)

    logging.info(f"Carregadas {len(missions)} missoes do ficheiro 'missions.json'")

    reliability_db = {}

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', ML_PORT))

    logging.info(f"Servidor Mission Link inicializado com sucesso")

    while True:
        try:
            data, addr = sock.recvfrom(4096)
            message = header_parser(data)

            if message:
                seq_recebido = message['seq']
                rover_id=message['rover_id']
                msg_type = message['message_type']

                if rover_id not in reliability_db:
                    logging.info(f"Novo Rover detetado no Mission Link: ID {rover_id}")
                    reliability_db[rover_id] = {
                        "last_seq" : -1,
                        "mother_seq": 1,
                        "last_response": None
                    }

                reliability_rover = reliability_db[rover_id]
                if reliability_rover["last_seq"] == seq_recebido:
                    logging.warning(f"Rover {rover_id} -> Nave Mae: mensagem duplicada recebida. seq: {seq_recebido}. reenviando resposta anterior")
                    ultima_resposta = reliability_rover["last_response"]

                    if ultima_resposta: sock.sendto(ultima_resposta, addr)
                    continue

                elif seq_recebido < reliability_rover["last_seq"]:
                    logging.warning(f"Mensagem antiga recebida. Seq: {seq_recebido}. Ignorando.")
                    continue

                response_packet = None

                my_seq =reliability_rover["mother_seq"]

                if msg_type == "MReq":

                    logging.info(f"Rover {rover_id} -> Nave Mae: Mission Request recebido. A verificar condições...")
                    rover_status =None
                    with lock_status:
                        rover_status = status_db.get(str(rover_id))

                    if rover_status is None:
                        logging.info(f"Nave Mae: Mission Request ignorado: sem dados de telemetria de Rover {rover_id}.")
                        continue

                    selected_mission =None

                    bat_atual=float(rover_status.get('bateria',0))
                    estado_atual = rover_status.get('estado', 'parado').strip()

                    if bat_atual > 25 and estado_atual == "parado":
                        for mission in missions[:]:
                            custo = mission.get('bateria_min_prevista', 0)

                            if rover_status['bateria'] - custo > 15:
                                selected_mission = mission
                                missions.remove(mission)
                                break

                    else:
                        logging.info(f"Nave Mae: Rover {rover_id} não elegível (Bat: {bat_atual}%, Est: {estado_atual})")

                    if selected_mission:
                        logging.info(f"Nave Mae: Missao {selected_mission['id_missao']} atribuida a Rover {rover_id}.")
                        mission_bytes = mission_packer(selected_mission)
                        if mission_bytes:

                            response_packet = header_builder(rover_id, my_seq, seq_recebido, "MHan", mission_bytes)


                    else:
                        logging.info(f"Nenhuma missao atribuida a Rover {rover_id}. (Buffer vazio ou bateria insuficiente)")


                elif msg_type == "MRep":
                    relatorio = report_parser(message['payload'])
                    if relatorio:
                        logging.info(f"Rover {rover_id} -> Nave Mae: Relatório {relatorio.get('progress')} da missao {relatorio.get('id_missao')}")

                    response_packet = header_builder(rover_id, 0, seq_recebido, "MAck", "") #acks simples nao ttêm seq numero, logo é 0
                elif msg_type == "MCon":
                    relatorio_final= report_parser(message['payload'])
                    if relatorio_final:
                        logging.info(f"Rover {rover_id} -> Nave Mae: Relatório Final da missao {relatorio_final.get('id_missao')}")
                        save_mission_complete(relatorio_final)

                    response_packet = header_builder(rover_id, 0 , seq_recebido, "MAck", "" )
                elif msg_type == "MAck":
                    logging.debug(f"Rover {rover_id} -> Nave Mae: Ack recebido do Rover {rover_id}")
                    pass


                elif msg_type == "Err":
                    logging.error(f"ERRO reportado pelo rover {rover_id}")
                    response_packet = header_builder(rover_id, 0 , seq_recebido, "MAck", "")

                if response_packet:
                    sock.sendto(response_packet, addr)

                    reliability_db[rover_id]= {
                        "last_seq": seq_recebido,
                        "last_response": response_packet,
                        "mother_seq": my_seq+1,
                    }

        except Exception as e:
            logging.error(f"ERRO: erro no loop: {e}")