import http.client
import json
import time
import os
import sys

NAVE_MAE_IP = "10.0.2.20"
PORT = 8080

class Cor:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def limpar_ecra():
    os.system('cls' if os.name == 'nt' else 'clear')

def obter_cor_bateria(nivel):
    if nivel > 60: return Cor.GREEN
    if nivel > 20: return Cor.YELLOW
    return Cor.RED

def obter_cor_estado(estado):
    if estado == "Moving": return Cor.CYAN
    if estado == "Idle": return Cor.END
    if estado == "Emergency": return Cor.RED + Cor.BOLD
    return Cor.END

def barra_progresso(percentagem, tamanho=10):
    cheio = int(tamanho * percentagem / 100)
    vazio = tamanho - cheio
    return "█" * cheio + "░" * vazio

def obter_estado_missao():
    try:
        conn = http.client.HTTPConnection(NAVE_MAE_IP, PORT, timeout=1)
        conn.request("GET", "/api/status")
        response = conn.getresponse()
        
        if response.status == 200:
            raw_data = response.read().decode()
            dados = json.loads(raw_data)
            mostrar_interface(dados)
        else:
            print(f"{Cor.RED}[Erro HTTP {response.status}]{Cor.END}")
        conn.close()
    except Exception:
        limpar_ecra()
        print(f"\n{Cor.RED}  SEM SINAL DA NAVE-MÃE ({NAVE_MAE_IP}){Cor.END}")
        print("A tentar reconectar...")

def mostrar_interface(dados):
    limpar_ecra()
    rovers = dados.get("rovers", {})
    missoes_pend = dados.get("missoes_pendentes", [])
    missoes_conc = dados.get("missoes_concluidas", [])
    agora = time.time() 

    print(f"{Cor.BLUE}╔═════════════════════════════════════════════════════════════════════════════╗ {Cor.END}")
    print(f"{Cor.BLUE}║                            SALEMA CONTROL CENTER                            ║{Cor.END}")
    print(f"{Cor.BLUE}╚═════════════════════════════════════════════════════════════════════════════╝{Cor.END}")
    print("-" * 80)
    print(f"\n{Cor.BOLD} FROTA DE ROVERS ({len(rovers)} registados){Cor.END}")
    
    if not rovers:
        print(f"   {Cor.YELLOW}>> Nenhum sinal de telemetria detetado...{Cor.END}")
    else:
        print(f"{'ID':<8} {'ESTADO':<12} {'POSIÇÃO (X, Y)':<21} {'BATERIA':<16} {'MISSÃO ATUAL/PROG':<20}{Cor.END}")
        for r_id, info in rovers.items():
            last_seen = info.get('last_seen', 0)
            diff = agora - last_seen
            bat = info.get('bateria', 0)
            pos = info.get('posicao', [0,0])
            missao = info.get('missao_atual')

            if diff > 5.0:
                estado_disp = "OFFLINE"
                cor_est = Cor.RED
            else:
                estado_disp = info.get('estado_op', 'ONLINE')
                cor_est = obter_cor_estado(estado_disp)

            if missao is None:
                missao_str = "---"
                cor_mis = Cor.END
            else:
                missao_str = str(missao)
                cor_mis = Cor.YELLOW 

            print(f"{Cor.BOLD}{r_id:<8}{Cor.END} "
                  f"{cor_est}{estado_disp:<12}{Cor.END} "
                  f"({pos[0]:.1f}, {pos[1]:.1f})".ljust(21) + 
                  f"{obter_cor_bateria(bat)}{bat:>13.1f}% {barra_progresso(bat)}{Cor.END}"
                  f"{cor_mis}{missao_str:>13}{Cor.END} ")

    print("\n" + "-" * 80)
    print(f"{Cor.BOLD} MISSÕES PENDENTES: {len(missoes_pend)}{Cor.END}")
    
    print("\n" + "-" * 80)
    print(f"{Cor.BOLD} MISSÕES CONCLUÍDAS ({len(missoes_conc)}){Cor.END}")
    if missoes_conc:
        print(f"{'ID':<10} {'ROVER':<10} {'TEMPO (s)':<10}{Cor.END}")
        for m in missoes_conc:
             print(f"{' ':<1}{m.get('id_missao','?'):<10} {str(m.get('rover_id','?')):<10} {str(m.get('tempo_execucao','?')):<10}")

    print("\n" + "=" * 80)
    print(f"{Cor.BOLD}CTRL+C para encerrar.{Cor.END}")

if __name__ == "__main__":
    try:
        while True:
            obter_estado_missao()
            time.sleep(1)
    except KeyboardInterrupt:
        sys.exit(0)