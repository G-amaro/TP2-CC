from datetime import datetime

#rover_id: "01"  (2 char)
#seq: "001" (3 char) if "000" then it's only a ack
#ack_seq: "001" (3 char) if "000" then it's only a message
#message_type: MHan, MReq, MRep, MErr, MCon.... (4 char)
#timestamp: "20241022102721" (14 char)
#payload_size: "000" (3 char) #para propositos de verificação

W_ID = 2
W_SEQ = 3
W_ACK = 3
W_MSQ_TYPE = 4
W_TIME = 14
W_PAYLOAD_SIZE = 3
W_HEADER_TOTAL = W_ID + W_SEQ + W_ACK + W_MSQ_TYPE + W_TIME + W_PAYLOAD_SIZE



W_M_ID = 4
W_M_TASK = 1
W_M_XYZ = 3 #(3 each)
W_M_DUR = 5
W_M_REP = 3
W_M_BAT = 3


#missao de captura de imagens
W_M_IMG_NUM = 2
W_M_IMG_DIR = 1


#missao de recolha de amostra de solo
W_M_SOL_PROF = 5
W_M_SOL_WGHT = 4

TASK_CODES = {
    "captura_imagens": "I" ,
     "coleta_amostras_solo": "S",
    "analise_atmosferica": "A"
}

def header_builder(rover_id, seq, ack_seq, message_type, payload_bytes):


    payload= None
    if not isinstance(payload_bytes, bytes):
        payload = str(payload_bytes.encode('utf-8'))

    payload_size = len(payload)
    mh_rover_id = str(rover_id).zfill(W_ID)
    mh_seq = str(seq).zfill(W_SEQ)
    mh_ack_seq = str(ack_seq).zfill(W_ACK)
    mh_message_type = str(message_type)            #.ljust(W_MSQ_TYPE) não deve ser preciso.
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    mh_payload_size = str(payload_size).zfill(W_PAYLOAD_SIZE)


    mission_header = mh_rover_id + mh_seq + mh_ack_seq +  mh_message_type + timestamp + mh_payload_size + payload

    return mission_header.encode('utf-8')


def header_parser(message):

    try:
        if len(message) < W_HEADER_TOTAL:
            #por aqui uma messagem de log de erro
            return None


        cursor = 0

        r_id = message[cursor : cursor + W_ID]
        cursor += W_ID
        r_seq = message[cursor : cursor + W_SEQ]
        cursor += W_SEQ
        r_ack_seq = message[cursor : cursor + W_ACK]
        cursor += W_ACK

        r_message_type_bytes = message[cursor : cursor + W_MSQ_TYPE]
        cursor += W_MSQ_TYPE
        r_message_type = r_message_type_bytes.decode('utf-8')

        r_time_bytes = message[cursor : cursor + W_TIME]
        cursor += W_TIME
        r_time = r_time_bytes.decode('utf-8')

        r_payload_size = message[cursor : cursor + W_PAYLOAD_SIZE]
        cursor += W_PAYLOAD_SIZE

        r_payload = message[cursor:]

        answer = {
            "rover_id": int(r_id),
            "seq": int(r_seq),
            "ack_seq": int(r_ack_seq),
            "message_type": r_message_type,
            "time": r_time,
            "payload_size": int(r_payload_size),
            "payload": r_payload
        }

        return answer
    except ValueError:
        #fazer log de erro
        return None




def mission_packer(mission):
    try:
        m_id = str(mission['id_missao']).zfill(W_M_ID)

        m_task = TASK_CODES[mission['tarefa']]


        coords = mission['coordenadas']
        m_x = str(coords['x']).zfill(W_M_XYZ)
        m_y = str(coords['y']).zfill(W_M_XYZ)
        m_z = str(coords['z']).zfill(W_M_XYZ)

        m_dur = str(mission['duracao_max_segundos']).zfill(W_M_DUR)
        m_rep = str(mission['report_intervalo_segundos']).zfill(W_M_REP)
        m_bat = str(mission['bat_min_prevista']).zfill(W_M_BAT)

        header = m_id + m_task + m_x + m_y + m_z + m_dur + m_rep + m_bat



        parametros = mission['parametros_tarefa']
        params = ""
        if m_task == "I":
            p_num =  str(parametros['num_fotos']).zfill(W_M_IMG_NUM)
            p_dir = str(parametros['direcao'])
            params = p_num + p_dir
        elif m_task == "S":
            prof = float(parametros['profundidade_alvo_cm'])
            p_prof = f"{prof:05.1f}"

            if len(p_prof) > W_M_SOL_PROF:
                p_prof = "999.9"

            p_peso = str(parametros['peso_alvo_gramas']).zfill(W_M_SOL_WGHT)
            params = p_prof + p_peso

        message = header + params

        return message.encode('utf-8')
    except Exception as e:
        #log error
        return None


def mission_parser(mission_bytes):

    try:
        if not mission_bytes: return None

        mission = mission_bytes.decode('utf-8')
        cursor = 0

        r_id = mission[cursor : cursor + W_M_ID]
        cursor += W_M_ID

        r_task_code = mission[cursor : cursor + W_M_TASK]
        cursor += W_M_TASK


        r_x = mission[cursor : cursor + W_M_XYZ]
        cursor += W_M_XYZ
        r_y = mission[cursor : cursor + W_M_XYZ]
        cursor += W_M_XYZ
        r_z = mission[cursor : cursor + W_M_XYZ]
        cursor += W_M_XYZ
        r_dur = mission[cursor : cursor + W_M_DUR]
        cursor += W_M_DUR
        r_rep = mission[cursor : cursor + W_M_REP]
        cursor += W_M_REP
        r_bat = mission[cursor : cursor + W_M_BAT]
        cursor += W_M_BAT

        mission_dic = {
            "id_missao": int(r_id),
            "tarefa": r_task_code,
            "coordenadas": {"x": int(r_x), "y": int(r_y), "z": int(r_z)},
            "duracao_max_segundos": int(r_dur),
            "report_intervalo_segundos": int(r_rep),
            "bat_min_prevista": int(r_bat),
            "parametros_tarefa": {}
        }

        if r_task_code == "I":
            p_num = mission[cursor : cursor + W_M_IMG_NUM]
            cursor += W_M_IMG_NUM
            p_dir = mission[cursor : cursor + W_M_IMG_DIR]
            cursor += W_M_IMG_DIR

            mission_dic["parametros_tarefa"]={
                "num_fotos": int(p_num),
                "direcao": p_dir,
            }

        elif r_task_code == "S":
            p_prof = mission[cursor : cursor + W_M_SOL_PROF]
            cursor += W_M_SOL_PROF
            p_peso = mission[cursor : cursor + W_M_SOL_WGHT]
            cursor += W_M_SOL_WGHT

            mission_dic["parametros_tarefa"]={
                "profundidade_alvo_cm": float(p_prof),
                "peso_alvo_gramas": int(p_peso),
            }

        return mission_dic
    except Exception as e:
        #log de erro
        return None