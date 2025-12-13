import logging
import time
import threading

log = logging.getLogger('physics') 


LOW_POWER_THRESHOLD = 20.0  
RECHARGE_TIME = 30          
RATE_MISSION = 0.5
RATE_IDLE = 0.2
UPDATE_INTERVAL = 1        

# [NOTA DE IMPLEMENTAÇÃO - SIMULAÇÃO DE AMBIENTE & THREAD INDEPENDENTE]
# Esta thread simula as leis da física e o consumo de energia do hardware.
#
# 1. Ciclo Infinito (Daemon): Corre em background (UPDATE_INTERVAL = 1s) para
#    atualizar a bateria independentemente do que o Rover esteja a fazer.
#
# 2. Gestão de Concorrência (CRÍTICO): Como esta thread ESCREVE no estado ('bateria', 'estado_op')
#    enquanto a Telemetria LÊ e o MissionLink LÊ/ESCREVE, o uso de 'lock' é obrigatório.
#    Sem o lock, poderíamos ter leituras incorretas (ex: bateria negativa) ou corrupção de dados.
#
# 3. Máquina de Estados de Energia:
#    - Dreno: Se 'em_missao', gasta mais (RATE_MISSION). Se 'parado', gasta menos.
#    - Trigger de Recarga: Se bateria < 20%, força o estado para 'low_power_sleep'.
#      Isto sinaliza à thread 'MissionLink' que deve pausar a execução da missão atual.
#    - Recuperação: Após RECHARGE_TIME, restaura a bateria a 100% e devolve o controlo.
def run_physics_simulator(state, lock):
    log.info(f"Simulador de Física iniciado. Limite de recarga: {LOW_POWER_THRESHOLD:.0f}%.")
    
    while True:
        try:
            time.sleep(UPDATE_INTERVAL)

            with lock:
                current_state = state["estado_op"]
                current_battery = state["bateria"]

                if state["bateria"] <= 0.0:
                    state["bateria"] = 0.0
                    if current_state != "low_power_sleep":
                        state["estado_op"] = "low_power_sleep"
                        log.critical("BATERIA ESGOTADA! Falha crítica no sistema.")
                        state["recharge_start_time"] = time.time()

                if current_state == "low_power_sleep":

                    recharge_start = state.get("recharge_start_time")
                    if recharge_start and (time.time() - recharge_start) >= RECHARGE_TIME:

                        state["bateria"] = 100.0

                        if(state['missao_atual'] != None):
                            state["estado_op"] = "em_missao"
                        else:
                            state["estado_op"] = "parado" 


                        state["recharge_start_time"] = None 
                        log.info("RECARGA FORÇADA COMPLETA! Bateria a 100%. Rover pronto para missões.")

                    continue 

                if current_battery > 0.0:
                    if current_state == "em_missao" or current_state == "a_caminho":
                        state["bateria"] -= RATE_MISSION
                    elif current_state == "parado":
                        state["bateria"] -= RATE_IDLE

                if state["bateria"] <= LOW_POWER_THRESHOLD:
                    if current_state != "low_power_sleep" :
                        state["estado_op"] = "low_power_sleep"

                    state["recharge_start_time"] = time.time() 
                    log.warning(f"Bateria em {state['bateria']:.1f}%. Entrando em MODO DE RECARGA ({RECHARGE_TIME}s).")

        except KeyboardInterrupt:
            break
        except Exception as e:
            log.error(f"Erro no simulador de física: {e}", exc_info=True)
            break
    log.info("Simulador de Física terminado.")