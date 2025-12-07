import socket
import json
import logging
import os
import time
from contextlib import aclosing
from datetime import datetime


KNOWN_ROVERS = {
    "10.0.4.20": 1,
    "10.0.0.20": 2,
    "10.0.1.20": 3
}


def sync():

    SYNC_PORT = 50000




    file_dir = os.path.dirname(__file__)
    info_dir = os.path.join(file_dir, "../info")
    os.makedirs(info_dir, exist_ok=True)

    json_path = os.path.join(info_dir, "rovers_info.json")

    dados = []
    if not os.path.exists(json_path):
        with open(json_path, "w") as f:
            json.dump([], f)


    try:
        with open(json_path, "r") as f:
            dados = json.load(f)
    except json.decoder.JSONDecodeError:
        dados = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', SYNC_PORT))

    while True:
        #receber
        try:
            answer, addr = sock.recvfrom(32)
            answer_str= answer.decode('utf-8') # Exemplo de output possivel "R01". R = request e 01 = possivel id do rover

            answer_type=answer_str
            if not answer_type=="Req":
                continue

            id_rover = addr[0]
            answer_id_rover = KNOWN_ROVERS.get(id_rover, 0)

            if answer_id_rover == 0:
                logging.error("Rover id could not be found")



            logging.info(f"Rover {answer_id_rover} ({addr[0]}:{addr[1]}) -> Nave Mae: sync request")

            info = False

            for r in dados:
                if int(r["id"]) == answer_id_rover: #info ja existe (atualizar info)
                    r["IP"]   = addr[0]
                    r["port"] = addr[1]
                    info = True
                    break

            if not info:
                rover_info = {
                    "id":   answer_id_rover,
                    "IP":   addr[0],
                    "port": addr[1]
                }
                dados.append(rover_info)

            with open(json_path, "w") as f:
                json.dump(dados, f, indent=4)


            ack = "A" + str(answer_id_rover).zfill(2)
            sock.sendto(ack.encode('utf-8'), addr)


        except Exception as e:
            logging.error(f"Erro: {e}")






