import http.client
import json
import time
import os
import sys

NAVE_MAE_IP = "10.0.2.20" 
PORT = 8080

# --- CÓDIGOS DE CORES ANSI ---
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
    missoes = dados.get("missoes", [])
    agora = time.time() 

    print(f"{Cor.BLUE}╔═════════════════════════════════════════════════════════════════════════════╗ {Cor.END}")
    print(f"{Cor.BLUE}║                            SALEMA CONTROL CENTER                            ║{Cor.END}")
    print(f"{Cor.BLUE}╚═════════════════════════════════════════════════════════════════════════════╝{Cor.END}")

    print("-" * 80)

    print(f"\n{Cor.BOLD} FROTA DE ROVERS ({len(rovers)} registados){Cor.END}")
    
    if not rovers:
        print(f"   {Cor.YELLOW}>> Nenhum sinal de telemetria detetado...{Cor.END}")
    else:
        
        print(f"{'ID':<8} {'ESTADO':<12} {'POSIÇÃO (X, Y)':<20} {'BATERIA':<21} {'MISSÃO ATUAL':<20}{Cor.END}")
        
        for r_id, info in rovers.items():
            
            last_seen = info.get('last_seen', 0)
            diffTempo = agora - last_seen
            
            bat = info.get('bateria', 0)
            pos = info.get('posicao', [0,0])
            missao = info.get('missao_atual')

            if diffTempo > 5.0:
            
                estado_display = f"OFFLINE"
                cor_est = Cor.RED
            else:
                estado_raw = info.get('estado_op', 'ONLINE')
                estado_display = estado_raw
                cor_est = obter_cor_estado(estado_raw)

            if missao is None:
                missao_str = "---"
                cor_missao = Cor.END
            else:
                missao_str = str(missao)
                cor_missao = Cor.YELLOW 
            
            pos_str = f"({pos[0]:.1f}, {pos[1]:.1f})"
            cor_bat = obter_cor_bateria(bat)
            barra = barra_progresso(bat)

            print(f"{Cor.BOLD}{r_id:<8}{Cor.END} "
                  f"{cor_est}{estado_display:<12}{Cor.END} "
                  f"{pos_str:<20} "
                  f"{cor_bat}{bat:>5.1f}% {barra}{Cor.END}"
                  f"{cor_missao}{missao_str:>13}{Cor.END} ")

    print("\n" + "-" * 80)
    
    print(f"{Cor.BOLD} REGISTO DE MISSÕES{Cor.END}")
    if not missoes:
        print(f"   {Cor.CYAN}>> Aguardando atribuição de missões...{Cor.END}")
    else:
        # AMARO !
        pass

    print("\n" + "=" * 80)
    print(f"{Cor.BOLD}CTRL+C para encerrar a conexão.{Cor.END}")

if __name__ == "__main__":
    try:
        while True:
            obter_estado_missao()
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{Cor.RED} Ground Control encerrado.{Cor.END}")
        sys.exit(0)