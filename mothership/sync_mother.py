import socket
import json
import logging
import os
import time
from datetime import datetime

MOTHER_IP = '10.0.3.20'
PORT = 50000

file_dir = os.path.dirname(__file__)
log_path = os.path.join(file_dir, "../logs/recorder.log")

logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', PORT))

while True:
    sock.settimeout(5)
    #receber
    try:
        answer, addr = sock.recvfrom(1024)
        answer= json.loads(answer.decode('utf-8'))
        logging.info(f"Mensagem de {addr[0]}:{addr[1]} -> {answer}")
    except socket.timeout:
        sock.close()


