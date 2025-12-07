import math
import time
import socket
import logging
import sys
import os
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mission_link import header_builder,header_parser,  mission_parser, report_packer


ROVER_SPEED= 5.0
UPDATE_RATE = 1.0
ML_PORT = 50001
MOTHER_IP = '10.0.2.20'

def  run_mission_link_rover(state, lock, rover_id):

    logging.info(f"Serviço Mission Link iniciado para Rover {rover_id}")
    seq = 1
    ack_seq = 0


    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', 0))

    while True:
        # por logica de carregar
        estado_atual = ""
        with lock:
            estado_atual = state['estado_op']

        if estado_atual == "low_power_sleep":
            logging.info(f"Em modo de recarga. A aguardar...")
            time.sleep(5)
            continue

        if estado_atual=="parado":

            logging.info(f"A pedir missao (Seq {seq})...")

            resposta = message_to_mother(rover_id, seq, ack_seq, "MReq", "", sock)
            if resposta is False:
                logging.warning(f"Sem resposta da mae. a esperar 5s...")
                time.sleep(5)
                continue

            elif resposta == "SHUTDOWN":
                logging.info("Mãe enviou ordem de fim (MEnd). A desligar...")
                os._exit(0)

            elif resposta is True :
                logging.info(f"Mae não deu missão (MAck). Esperar 10s.")
                seq += 1
                time.sleep(10)
            else :
                seq += 1
                seq = execute_mission(resposta, rover_id, seq, lock, state, sock)

        else:
            time.sleep(1)




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
                    return answer['payload']

                if answer['message_type'] == "MEnd":
                    return "SHUTDOWN"


        except socket.timeout:
            logging.warning(f"Socket timeout no envio de {message_type}. Tentativas restantes: {sending_max_times}. a esperar {timesleep}s.")
            time.sleep(timesleep)
            timesleep *= 2

        except Exception as e:
            logging.error(f"Erro de Socket: {e}")

    logging.error(f"Falha: a mae nao respondeu após 3 tentativas (seq {seq}).")
    return False


def execute_mission(payload_bytes,  rover_id, seq, lock, state, sock):

    mission_data = mission_parser(payload_bytes)

    if not mission_data:
        logging.error("ERRO: nao consegui ler o payload da missao")
        return seq



    tarefa = mission_data['tarefa']
    m_id = mission_data['id_missao']
    intervalo = mission_data['report_intervalo_segundos']
    duracao = mission_data['duracao_max_segundos']
    dest_x = mission_data['coordenadas']['x']
    dest_y = mission_data['coordenadas']['y']

    with lock:
        state['missao_atual'] = m_id
        state['estado_op'] = "a_caminho"

    move_to_target(state, lock, dest_x, dest_y)

    with lock:
        state['estado_op'] = "em_missao"

    logging.info(f" ------------ A INICIAR MISSAO {m_id}: {tarefa} ---------------")
    logging.info(f"Duracao: {duracao} segundos | reportar a cada {intervalo} segundos")

    n_relatorios = max(1,round(duracao/intervalo))

    processo = 0
    step = round(100/n_relatorios)

    while processo < 90: #para nao interferir com o relatorio final
        current_state = ""
        with lock:
            current_state = state["estado_op"]


        if current_state == "low_power_sleep":
            logging.warning("Bateria Critica! A pausar missao para recarga...")

            while True:
                time.sleep(1)
                with lock:
                    if state["estado_op"] != "low_power_sleep":
                        state["estado_op"] = "em_missao"
                        break


            logging.info("Recarga completa. A retornar missao...")

        time.sleep(intervalo)
        processo += step




        if processo >= 100:
            processo = 100
            break

        with lock:
            state['progresso'] = processo


        dados_fake = generate_simulated_data(tarefa)

        report_dict = {
            "id_missao": m_id,
            "progress": processo,
            "tarefa": tarefa,
            **dados_fake
        }

        report_bytes = report_packer(report_dict)

        if report_bytes:
            logging.info(f"A enviar Relatório {processo}% (Seq {seq})...")
            ack = message_to_mother(rover_id, seq, 0, "MRep", report_bytes, sock)


            if ack:
                seq += 1

            else:
                seq += 1
                logging.warning(f"Mãe nao confirmou relatório. continuando missao na mesma...")




    time.sleep(intervalo)
    logging.info(f"A enviar Conclusão 100% (Seq {seq})...")
    dados_finais = generate_simulated_data(tarefa)

    with lock:
        state['progresso'] = processo

    final_dict = {
        "id_missao": m_id,
        "progress": 100,
        "tarefa": tarefa,
        **dados_finais
    }

    final_bytes = report_packer(final_dict)

    if final_bytes:

        ack_conc = message_to_mother(rover_id, seq, 0, "MCon", final_bytes, sock)
        seq += 1

        if ack_conc:
            logging.info("Missao concluida e confirmada pela Mae!")


        else:
            logging.warning(f"Mãe nao confirmou relatório de conclusao.")

    with lock:
        state["estado_op"] = "parado"
        state["missao_atual"] = None
        state['progresso'] = 0


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

def move_to_target(state, lock, target_x, target_y):

    with lock:
        start_x, start_y = state['posicao']

    logging.info(f"A viajar de ({start_x:.1f}, {start_y:.1f}) para ({target_x:.1f}, {target_y:.1f})...")

    dx = target_x - start_x
    dy = target_y - start_y
    distance = math.hypot(dx, dy)

    if distance < 0.1:
        logging.info("Já chegou ao  local.")

    step_distance = ROVER_SPEED * UPDATE_RATE

    steps = int(distance / step_distance)
    step_x = (dx / distance) * step_distance
    step_y = (dy / distance) * step_distance

    current_x, current_y = start_x, start_y

    for _ in range(steps):
        time.sleep(UPDATE_RATE)

        current_x += step_x
        current_y += step_y
        with lock:
            state['posicao'] = (current_x, current_y)


    with lock:
        state['posicao'] = (current_x, current_y)

    logging.info(f"Chegou ao destino")