
from datetime import datetime
import socket
import logging
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mission_link import header_builder, header_parser

ML_PORT = 50001
MOTHER_IP = '10.0.2.20'

def  run_mission_link(state, lock, rover_id):

    seq = 1
    ack_seq = 0


    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', 0))

    ack = message_to_mother(rover_id, seq, ack_seq, "MReq", "", sock)
    if not ack :
        sock.close()
        return
    elif ack == True :
        pass
        seq += 1
    else :
        payload = ack
        seq += 1
        execute_mission(payload, rover_id, seq, lock, state)




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
            sock.settimeout(timesleep)
            timesleep *= 2

    return False


def execute_mission(payload,  rover_id, seq, lock, state):

    j=0