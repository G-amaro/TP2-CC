import socket
import json
import logging
import os
import time
from contextlib import aclosing
from datetime import datetime

MOTHER_PORT = 50000

file_dir = os.path.dirname(__file__)
log_path = os.path.join(file_dir, "../logs/recorder.log")

logging.basicConfig(
    filename = log_path,
    level    = logging.INFO,
    format   = '%(asctime)s - %(levelname)s - %(message)s'
)

file_dir  = os.path.dirname(__file__)
json_path = os.path.join(file_dir, "../info/rovers_info.json")
with open(json_path, "r") as f:
    dados = json.load(f)


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', MOTHER_PORT))

while True:
    #receber

    answer, addr = sock.recvfrom(1024)
    answer= json.loads(answer.decode('utf-8'))
    logging.info(f"Rover {answer['rover_id']} ({addr[0]}:{addr[1]}) -> Nave Mae: {answer['type']}")

    if answer['type'] == "sync request":
        info = False

        for r in dados:
            if r["id"] == answer["rover_id"]: #info ja existe (atualizar info)
                r["IP"]   = addr[0]
                r["port"] = addr[1]
                info = True
                break

        if not info:
            rover_info = {
                "id":   answer["rover_id"],
                "IP":   addr[0],
                "port": addr[1]
            }
            dados.append(rover_info)

        with open(json_path, "w") as f:
            json.dump(dados, f, indent=4)

        ack_msg = {
            "id": answer["rover_id"],
            "type": "sync ack"
        }

        sock.sendto(json.dumps(ack_msg).encode('utf-8'), addr)





