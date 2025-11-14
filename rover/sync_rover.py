import socket
import json
import sys
import os
import logging
import time
from datetime import datetime


# rover_id=None
# if sys.argv.__len__() == 2:
#     rover_id = int(sys.argv[1])

def sync(rover_id):
    file_dir = os.path.dirname(__file__)
    log_path = os.path.join(file_dir, "../logs/recorder.log")

    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    MOTHER_IP = None
    MOTHER_PORT = 50000


    MOTHER_IP = '10.0.2.20'

    msg_sync= {
            "rover_id": str(rover_id),
            "type": "sync request"
            #,"timestamp": datetime.now().isoformat()
        }

    sending_max_times = 5
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', 0))

    timeout = 2
    time_sleep = 1


    while sending_max_times > 0:

        sock.sendto(json.dumps(msg_sync).encode('utf-8'), (MOTHER_IP, MOTHER_PORT))
        sending_max_times-=1

        sock.settimeout(timeout)

        try:

            data, addr = sock.recvfrom(1024)
            print("rover 2 recebeu: {}".format(data))
            data= json.loads(data.decode('utf-8'))

            if data['type'] == "sync ack":
                logging.info(f"Nave Mae({addr[0]}:{addr[1]}) -> Rover {data['id']}  : {data['type']}")
                break


        except socket.timeout:
            time.sleep(time_sleep)
            time_sleep *= 2
            continue




    if sending_max_times == 0:
        logging.error(f"Rover "+ str(rover_id) + ": Max number of sync tries with mothership exceeded. Sync ACK missing.")
    sock.close()