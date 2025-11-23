import sys
import os
import socket
import json
import logging
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


def run_mission_link_mother(status_db, lock_status):

    file_dir = os.path.dirname(__file__)
    json_path = os.path.join(file_dir, "../info/missions.json")

    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            missions = json.load(f)

    reliability_db = {}

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', ML_PORT))

    while True:
        try:
            data, addr = sock.recvfrom(4096)
            message = header_parser(data)

            if message:
                seq_recebido = message['seq']
                rover_id=message['rover_id']
                msg_type = message['message_type']

                if rover_id in reliability_db and reliability_db[rover_id]["last_seq"] == seq_recebido:

                    ultima_resposta = reliability_db[rover_id]["last_response"]
                    sock.sendto(ultima_resposta, addr)
                    continue

                if rover_id in reliability_db and seq_recebido < reliability_db[rover_id]["last_seq"]:
                    continue

                response_packet = None

                if msg_type == "MReq":

                    rover_status =None
                    with lock_status:
                        rover_status = status_db.get(str(rover_id))

                    if rover_status is None:
                        continue

                    selected_mission =None

                    if rover_status.get('bateria',0) > 25  and rover_status.get('estado','idle') == "idle":
                        for mission in missions[:]:
                            custo = mission.get('bateria_min_prevista', 0)

                            if rover_status['bateria'] - custo > 15:
                                selected_mission = mission
                                missions.remove(mission)
                                break

                    if selected_mission:
                        mission_bytes = mission_packer(selected_mission)
                        if mission_bytes:

                            response_packet = header_builder(rover_id, seq_recebido+ 1, seq_recebido, "MHan", mission_bytes)


                    else:
                        #do logs
                        j=0

                elif msg_type == "MRep":
                    relatorio = report_parser(message['payload'])
                    #if relatorio:
                        #logs

                    response_packet = header_builder(rover_id, 0, seq_recebido, "MAck", "") #acks simples nao ttêm seq numero, logo é 0
                elif msg_type == "MCon":
                    relatorio_final= report_parser(message['payload'])
                    if relatorio_final:
                        #logs
                        save_mission_complete(relatorio_final)

                    response_packet = header_builder(rover_id, 0 , seq_recebido, "MAck", "" )
                elif msg_type == "MAck":
                    pass


                elif msg_type == "Err":
                    #log
                    response_packet = header_builder(rover_id, 0 , seq_recebido, "MAck", "")

                if response_packet:
                    sock.sendto(response_packet, addr)

                    reliability_db[rover_id]= {
                        "last_seq": seq_recebido,
                        "last_response": response_packet
                    }

        except Exception as e:
            logging.error(e)








