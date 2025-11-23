import time
from datetime import datetime
import socket
import logging
import sys
import os
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mission_link import header_builder,header_parser,  mission_parser, report_packer

ML_PORT = 50001
MOTHER_IP = '10.0.2.20'

def  run_mission_link_rover(state, lock, rover_id):

    seq = 1
    ack_seq = 0


    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', 0))

    while True:

        if state['estado_op']=="idle":
            resposta = message_to_mother(rover_id, seq, ack_seq, "MReq", "", sock)
            if resposta is None:
                time.sleep(5)
                continue

            elif resposta is True :

                seq += 1
                time.sleep(10)
            else :
                seq += 1
                execute_mission(resposta, rover_id, seq, lock, state, sock)




def message_to_mother(rover_id, seq, ack_seq, message_type, payload, sock):

    #mission request message (payload is empty)
    message = header_builder(rover_id, seq, ack_seq, message_type, payload)

    sending_max_times = 3
    timeout = 2
    timesleep = 2

    while sending_max_times> 0:

        sock.sendto(message, (MOTHER_IP, ML_PORT))
        sending_max_times -= 1

        sock.settimeout(timeout)

        try:
            data, addr = sock.recvfrom(1024)

            answer = header_parser(data)

            #o rover só vai receber mission handle e ack
            if answer['ack_seq'] == seq:


                if answer['message_type'] == "MAck":
                    return True


                if answer['message_type'] == "MHan":
                    return answer['payload'] #o payload vai ser a missao


        except socket.timeout:
            time.sleep(timesleep)
            timesleep *= 2

    return False


def execute_mission(payload_bytes,  rover_id, seq, lock, state, sock):

    mission_data = mission_parser(payload_bytes)

    if not mission_data:
        print("nao consegui ler o payload da missao")
        return seq

    with lock:
        state['missao_atual'] = mission_data
        state['estado_op'] = "em_missao"

    tarefa = mission_data['tarefa']
    m_id = mission_data['id_missao']
    intervalo = mission_data['report_intervalo_segundos']
    duracao = mission_data['duracao_max_segundos']

    n_relatorios = round(duracao/intervalo)

    processo = 0
    step = round(100/n_relatorios)

    while processo < 85: #para nao interferir com o relatorio final

        time.sleep(intervalo)
        processo += step

        dados_fake = generate_simulated_data(tarefa)

        report_dict = {
            "id_missao": m_id,
            "progress": processo,
            "tarefa": tarefa,
            **dados_fake
        }

        report_bytes = report_packer(report_dict)

        if report_bytes:

            ack = message_to_mother(rover_id, seq, 0, "MRep", report_bytes, sock)

            if ack:
                seq += 1

            else:

                with lock: state["estado_op"] = "erro"
                return seq


    time.sleep(intervalo)

    dados_finais = generate_simulated_data(tarefa)

    final_dict = {
        "id_missao": m_id,
        "progress": 100,
        "tarefa": tarefa,
        **dados_finais
    }

    final_bytes = report_packer(final_dict)

    if final_bytes:

        ack_conc = message_to_mother(rover_id, seq, 0, "MCon", final_bytes, sock)

        if ack_conc:

            seq += 1

    with lock:
        state["estado_op"] = "idle"
        state["missao_atual"] = None

    return seq




def generate_simulated_data(tarefa):
    dados = {}

    if tarefa == "captura_imagens":
        qtd = random.randint(1,3)
        lista = []
        for i in range(qtd):
            nome = f"img_{random.randint(10,99)}_{i}.png"
            lista.append(nome)

        dados["imagens"] = lista

    elif tarefa == "analise_atmosferica":
        dados['temperatura'] = round(random.uniform(-80.0,-10.0), 2)
        dados['composicao'] = {
            "co2" : random.randint(90,98),
            "o2": random.randint(0,5),
            "n2" : random.randint(1,5)
        }

    elif tarefa == "coleta_amostras_solo":
        dados['id_amostra'] = random.randint(1000, 9999)
        dados['peso'] = random.randint(100,900)
        dados['profundidade'] = round(random.uniform(5.0,30.0),1)

    return dados