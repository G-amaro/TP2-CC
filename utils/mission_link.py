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


#############################################
W_M_ID = 4
W_M_TASK = 1
W_M_XYZ = 3 #(3 each)
W_M_DUR = 5
W_M_REP = 3
W_M_BAT = 5


#missao de captura de imagens
W_M_IMG_NUM = 2
W_M_IMG_DIR = 1


#missao de recolha de amostra de solo
W_M_SOL_PROF = 5
W_M_SOL_WGHT = 4

####################################################
#Report byte number
W_R_ID =4
W_R_PROG = 3
W_R_TASK = 1

#imagens
W_R_I_QTY = 2
W_R_I_NAME = 20

#atmosfera
W_R_A_TEMP = 6
W_R_A_GAS = 3

#solo
W_R_S_ID = 4
W_R_S_WGHT = 4
W_R_S_PROF = 5

TASK_CODES = {
    "captura_imagens": "I" ,
     "coleta_amostras_solo": "S",
    "analise_atmosferica": "A"
}

CODES_TO_TASK = {v: k for k, v in TASK_CODES.items()}


def header_builder(rover_id, seq, ack_seq, message_type, payload_input):


    payload= None
    if  isinstance(payload_input, str):
        payload = payload_input.encode('utf-8')
    elif isinstance(payload_input, bytes):
        payload = payload_input


    payload_size = len(payload)
    mh_rover_id = str(rover_id).zfill(W_ID)
    mh_seq = str(seq).zfill(W_SEQ)
    mh_ack_seq = str(ack_seq).zfill(W_ACK)
    mh_message_type = str(message_type)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    mh_payload_size = str(payload_size).zfill(W_PAYLOAD_SIZE)


    mission_header = mh_rover_id + mh_seq + mh_ack_seq +  mh_message_type + timestamp + mh_payload_size

    return mission_header.encode('utf-8') + payload


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

        m_dur = str(mission['duracao_max_segundos']).zfill(W_M_DUR)
        m_rep = str(mission['report_intervalo_segundos']).zfill(W_M_REP)

        bat_val = float(mission.get('bateria_min_prevista', 0.0))

        m_bat = f"{bat_val:05.1f}"

        if len(m_bat) > W_M_BAT:
            m_bat = "100.0"



        header = m_id + m_task + m_x + m_y + m_dur + m_rep + m_bat



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
        r_dur = mission[cursor : cursor + W_M_DUR]
        cursor += W_M_DUR
        r_rep = mission[cursor : cursor + W_M_REP]
        cursor += W_M_REP
        r_bat = mission[cursor : cursor + W_M_BAT]
        cursor += W_M_BAT

        mission_dic = {
            "id_missao": int(r_id),
            "tarefa": CODES_TO_TASK.get(r_task_code, "desconhecida"),
            "coordenadas": {"x": int(r_x), "y": int(r_y)},
            "duracao_max_segundos": int(r_dur),
            "report_intervalo_segundos": int(r_rep),
            "bat_min_prevista": float(r_bat),
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

def report_packer(report_dict):
    try:
        r_id = str(report_dict['id_missao']).zfill(W_R_ID)
        r_prog = str(report_dict['progress']).zfill(W_R_PROG)

        task_name = report_dict['tarefa']
        r_task = TASK_CODES.get(task_name, "X")

        header = r_id  + r_prog + r_task
        params = ""

        if r_task == "I":
            lista = report_dict.get('imagens', [])
            qtd = len(lista)

            if qtd > 3: qtd = 3

            p_qtd = str(qtd).zfill(W_R_I_QTY)

            slots = ""
            for i in range(3):
                if i < qtd:
                    nome = str(lista[i])[:W_R_I_NAME].ljust(W_R_I_NAME)
                else:
                    nome = " " * W_R_I_NAME # vazio

                slots += nome

            params = p_qtd + slots

        elif r_task == "A":
            temp_val = float(report_dict.get('temperatura',0))
            p_temp = f"{temp_val:06.2f}"

            comp = report_dict.get('composicao', {})
            p_co2 = str(comp.get('co2', 0)).zfill(W_R_A_GAS)
            p_o2  = str(comp.get('o2', 0)).zfill(W_R_A_GAS)
            p_n2  = str(comp.get('n2', 0)).zfill(W_R_A_GAS)

            params = p_temp + p_co2 + p_o2 + p_n2

        elif r_task == "S":
            p_id = str(report_dict.get('id_amostra',0)).zfill(W_R_S_ID)
            p_peso = str(report_dict.get('peso',0)).zfill(W_R_S_WGHT)

            prof = float(report_dict.get('profundidade',0))
            p_prof = f"{prof:05.1f}"

            params = p_id + p_peso + p_prof

        return (header + params).encode('utf-8')
    except Exception as e:
        #logging.error()
        return None


def report_parser(data_bytes):
    try:
        if not data_bytes: return None
        data_str = data_bytes.decode('utf-8')
        cursor = 0

        r_id = data_str[cursor : cursor + W_R_ID]
        cursor += W_R_ID
        r_prog = data_str[cursor : cursor + W_R_PROG]
        cursor += W_R_PROG
        r_task = data_str[cursor : cursor + W_R_TASK]
        cursor += W_R_TASK

        task_name = CODES_TO_TASK.get(r_task, "desconhecida")

        report = {
            "id_missao": int(r_id),
            "tarefa": task_name,
            "progress": int(r_prog)
        }

        if r_task == "I":
            qtd = int(data_str[cursor : cursor + W_R_I_QTY])
            cursor += W_R_I_QTY
            lista_imgs = []

            for _ in range(3):
                raw_name =data_str[cursor : cursor + W_R_I_NAME]
                cursor += W_R_I_NAME
                clean_name =raw_name.strip()
                if clean_name:
                    lista_imgs.append(clean_name)

            report["imagens"] = lista_imgs[:qtd]

        elif r_task == "A":
            p_temp = data_str[cursor : cursor + W_R_A_TEMP]
            cursor += W_R_A_TEMP

            p_co2 = data_str[cursor : cursor + W_R_A_GAS]
            cursor += W_R_A_GAS
            p_o2 = data_str[cursor : cursor + W_R_A_GAS]
            cursor += W_R_A_GAS
            p_n2 = data_str[cursor : cursor + W_R_A_GAS]
            cursor += W_R_A_GAS

            report["temperatura"] = float(p_temp)
            report["composicao"] = {
                "co2": int(p_co2),
                "o2": int(p_o2),
                "n2": int(p_n2)
            }

        elif r_task == "S":
            p_id = data_str[cursor : cursor + W_R_S_ID]
            cursor += W_R_S_ID
            p_peso = data_str[cursor : cursor + W_R_S_WGHT]
            cursor += W_R_S_WGHT
            p_prof = data_str[cursor : cursor + W_R_S_PROF]
            cursor += W_R_S_PROF

            report["id_amostra"] = int(p_id)
            report["peso"] = int(p_peso)
            report["profundidade"] = float(p_prof)

        return report
    except Exception as e:
        #logs
        return None