import sys
import os
import socket
import json
import logging
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mission_link import header_builder, header_parser,  mission_packer, report_parser
from rover.physics_simulator import RATE_MISSION

ML_PORT=50001

# [NOTA DE IMPLEMENTAÇÃO - PERSISTÊNCIA & CONSISTÊNCIA]
# Esta função auxiliar garante que os dados finais das missões são guardados de forma segura.
#
# 1. Atualização em Memória (RAM): Adiciona à lista 'history_list' dentro de um bloco
#    'with lock' para garantir que a Thread da API (que lê esta lista) não acede a dados corrompidos.
#
# 2. Persistência em Disco (JSON): Escreve no ficheiro 'completed_missions.json' para garantir
#    que o histórico sobrevive a reinícios do servidor.
def save_mission_complete(payload_dict, history_list, lock):
    file_dir = os.path.dirname(__file__)
    json_file = os.path.join(file_dir, '../info/completed_missions.json')
    
    payload_dict["received_at"] = str(datetime.now())
    
    with lock:
        history_list.append(payload_dict)

    try:
        disk_history = []
        if os.path.exists(json_file) and os.stat(json_file).st_size > 0:
            with open(json_file, 'r') as f:
                disk_history = json.load(f)
        
        disk_history.append(payload_dict)
        with open(json_file, 'w') as f:
            json.dump(disk_history, f, indent=4)
            
        logging.info(f"Mission {payload_dict.get('id_missao')} guardada.")
    except Exception as e:
        logging.error(f"Erro ao guardar completed_missions: {e}")

# [NOTA DE IMPLEMENTAÇÃO - LÓGICA DE SERVIDOR UDP & IDEMPOTÊNCIA]
# Esta thread gere a comunicação crítica. Como usamos UDP, implementámos lógica extra:
#
# 1. Base de Dados de Fiabilidade ('reliability_db'):
#    - Mantemos o estado da conexão lógica para cada Rover (último SEQ recebido).
#    - Deteção de Duplicados: Se recebermos um pacote com SEQ igual ao anterior, sabemos
#      que o nosso ACK se perdeu. NÃO processamos a missão novamente (evita duplicação).
#      Apenas re-enviamos a resposta antiga ('last_response') que temos em cache.
#
# 2. Atribuição Inteligente de Missões:
#    - Consultamos a Telemetria ('status_db') antes de dar uma missão.
#    - Cálculo de Custo Energético: Estimamos se o rover tem bateria suficiente para
#      a duração da missão (Custo = Tempo * Rate) antes de a atribuir.
#    - Usamos Locks ('lock_missions') para garantir que uma missão sai da lista de
#      pendentes atomicamente (apenas um rover recebe aquela missão específica).
def run_mission_link_mother(status_db, lock_status, missions_db, completed_db, lock_missions):

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
                rover_id = message['rover_id']
                msg_type = message['message_type']

                if rover_id not in reliability_db:
                    reliability_db[rover_id] = {"last_seq": -1, "mother_seq": 1, "last_response": None}

                reliability_rover = reliability_db[rover_id]
                if reliability_rover["last_seq"] == seq_recebido:
                    if reliability_rover["last_response"]: sock.sendto(reliability_rover["last_response"], addr)
                    continue
                elif seq_recebido < reliability_rover["last_seq"]:
                    continue

                response_packet = None
                my_seq = reliability_rover["mother_seq"]

                if msg_type == "MReq":

                    logging.info(f"Rover {rover_id}: Pedido de Missão.")
                    rover_status = None
                    with lock_status:
                        rover_status = status_db.get(str(rover_id))

                    if rover_status is None:
                        response_packet = header_builder(rover_id, 0, seq_recebido, "MAck", "")
                    else:

                        missions_empty=False
                        with lock_missions:
                            if len(missions_db) == 0:
                                missions_empty = True

                        if missions_empty:
                            logging.info(f"Sem missoes no buffer. A enviar ordem de shutdown ao rover {rover_id}.")
                            response_packet = header_builder(rover_id, 0, seq_recebido, "MEnd", "")

                        else:
                            selected_mission = None
                            bat_atual = float(rover_status.get('bateria',0))

                            if bat_atual > 20:
                                with lock_missions: 
                                    for mission in missions_db[:]:
                                        duracao = mission.get('duracao_max_segundos', 0)
                                        custo = (duracao * RATE_MISSION) + 10
                                        mission['bateria_min_prevista'] = float(custo)

                                        if rover_status['bateria'] - custo > 5:
                                            selected_mission = mission
                                            missions_db.remove(mission) 
                                            break

                            if selected_mission:
                                logging.info(f"Atribuida {selected_mission['id_missao']} a Rover {rover_id}")
                                mission_bytes = mission_packer(selected_mission)
                                if mission_bytes:
                                    response_packet = header_builder(rover_id, my_seq, seq_recebido, "MHan", mission_bytes)
                            else:
                                response_packet = header_builder(rover_id, 0, seq_recebido, "MAck", "")

                elif msg_type == "MRep":
                    response_packet = header_builder(rover_id, 0, seq_recebido, "MAck", "")

                elif msg_type == "MCon":
                    relatorio_final = report_parser(message['payload'])
                    if relatorio_final:
                        logging.info(f"Rover {rover_id}: Missão Concluída.")
                        relatorio_final['rover_id'] = rover_id

                        save_mission_complete(relatorio_final, completed_db, lock_missions)
                        
                    response_packet = header_builder(rover_id, 0 , seq_recebido, "MAck", "" )


                if response_packet:
                    sock.sendto(response_packet, addr)
                    reliability_db[rover_id] = {"last_seq": seq_recebido, "last_response": response_packet, "mother_seq": my_seq+1}

        except Exception as e:
            logging.error(f"Erro MissionLink: {e}")