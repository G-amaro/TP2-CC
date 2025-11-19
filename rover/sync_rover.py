import socket
import threading
import os
import logging
import time

def sync(rover_id):
    threading.current_thread().name = f"Sync-{rover_id}"

    SYNC_PORT = 50000
    MOTHER_IP = '10.0.2.20'


    #mensagem em JSON
    # msg_sync= {
    #         "rover_id": str(rover_id),
    #         "type": "sync request"
    #         #,"timestamp": datetime.now().isoformat()
    #     }
    # message = json.dumps(msg_sync).encode('utf-8')

    #mensagem em string (nº de bytes otimizado)
    msg_type = "R" # "R" significa request e "A" ack
    msg_rover_id = str(rover_id).zfill(2)

    msg_str = f"{msg_type}{msg_rover_id}"
    message = msg_str.encode('utf-8')


    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', 0))


    sending_max_times = 5
    timeout = 2
    time_sleep = 2


    while sending_max_times > 0:

        sock.sendto(message, (MOTHER_IP, SYNC_PORT))
        sending_max_times-=1

        sock.settimeout(timeout)

        try:

            data, addr = sock.recvfrom(32)
            print("rover "+ rover_id + " recebeu: {}".format(data))


            response_data= data.decode('utf-8') # Exemplo de output possivel "A01" A = ack e 01 = possivel id do rover

            if(len(response_data) < 3):
                continue

            response_type = response_data[0] #
            response_rover_id = response_data[1:3]




            if response_type == "A" and response_rover_id == msg_rover_id:
                logging.info(f"Nave Mae({addr[0]}:{addr[1]}) -> Rover {response_rover_id}  : sync ack")
                sock.close()
                return True



        except socket.timeout:
            time.sleep(time_sleep)
            time_sleep *= 2
            continue



    logging.error(f"Rover "+ str(rover_id) + ": Max number of sync tries with mothership exceeded. Sync ACK missing.")

    sock.close()
    return False