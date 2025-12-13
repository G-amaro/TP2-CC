import logging
import time
import threading

log = logging.getLogger('physics') 


LOW_POWER_THRESHOLD = 20.0  
RECHARGE_TIME = 30          
RATE_MISSION = 0.5
RATE_IDLE = 0.2
UPDATE_INTERVAL = 1        

def run_physics_simulator(state, lock):
    log.info(f"Simulador de Física iniciado. Limite de recarga: {LOW_POWER_THRESHOLD:.0f}%.")
    
    while True:
        try:
            time.sleep(UPDATE_INTERVAL)

            with lock:
                current_state = state["estado_op"]
                current_battery = state["bateria"]

                # --- C. VERIFICAR 0% (Falha Crítica) ---
                if state["bateria"] <= 0.0:
                    state["bateria"] = 0.0
                    if current_state != "low_power_sleep":
                        state["estado_op"] = "low_power_sleep"
                        log.critical("BATERIA ESGOTADA! Falha crítica no sistema.")
                        state["recharge_start_time"] = time.time()

                # ==========================================================
                # 1. GESTÃO DO ESTADO DE SONO (Recarga Forçada)
                # ==========================================================
                if current_state == "low_power_sleep":

                    # Verifica se o tempo de recarga terminou
                    recharge_start = state.get("recharge_start_time")
                    if recharge_start and (time.time() - recharge_start) >= RECHARGE_TIME:

                        # --- ACORDA E RECARREGA ---
                        state["bateria"] = 100.0

                        if(state['missao_atual'] != None):
                            state["estado_op"] = "em_missao"
                        else:
                            state["estado_op"] = "parado" # Volta ao estado normal


                        state["recharge_start_time"] = None # Limpa o temporizador
                        log.info("RECARGA FORÇADA COMPLETA! Bateria a 100%. Rover pronto para missões.")

                    continue # Não aplica dreno enquanto dorme

                # ==========================================================
                # 2. VERIFICAÇÃO DE DRENO E ESTADOS CRÍTICOS
                # ==========================================================

                # --- A. Aplicar Dreno Normal ---
                if current_battery > 0.0:
                    if current_state == "em_missao" or current_state == "a_caminho":
                        state["bateria"] -= RATE_MISSION
                    elif current_state == "parado":
                        state["bateria"] -= RATE_IDLE

                # --- B. VERIFICAR LIMITE DE 20% (Entrar em Sono) ---
                if state["bateria"] <= LOW_POWER_THRESHOLD:
                    if current_state != "low_power_sleep" :
                        state["estado_op"] = "low_power_sleep"

                    state["recharge_start_time"] = time.time() # Inicia o temporizador
                    log.warning(f"Bateria em {state['bateria']:.1f}%. Entrando em MODO DE RECARGA ({RECHARGE_TIME}s).")



        except KeyboardInterrupt:
            break
        except Exception as e:
            log.error(f"Erro no simulador de física: {e}", exc_info=True)
            break
    log.info("Simulador de Física terminado.")