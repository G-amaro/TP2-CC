import socket
import json
import sys
import os
import time
from datetime import datetime


rover_id=None
if sys.argv.__len__() == 2:
    rover_id = int(sys.argv[1])

file_dir = os.path.dirname(__file__)
json_path = os.path.join(file_dir, "../info/rovers_info.json")
with open(json_path, "r") as f:
    dados = json.load(f)

rover_info = None

for r in dados:
    if r["id"] == rover_id:
        rover_info = r
        break



MOTHER_PORT = 50000
MOTHER_IP = '10.0.3.20'

msg_sync= {
        "rover_id": str(rover_info["id"]),
        "message_type": "sync",
        "message": "ola, sou o rover " + str(rover_info["id"]),
        "timestamp": datetime.now().isoformat()
    }


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

sock.sendto(json.dumps(msg_sync).encode('utf-8'), (MOTHER_IP, MOTHER_PORT))
sock.close()