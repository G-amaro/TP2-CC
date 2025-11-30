import subprocess
import time
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROVER_SCRIPT = os.path.join(BASE_DIR, '..', 'rover', 'rover_main.py')

def test_parallel_rovers():
    print("=== TESTE: Múltiplos Rovers em Paralelo ===")
    
    rovers = []
    n_rovers = 3  
    
    try:
        for i in range(2, 2 + n_rovers):
            print(f" -> A lançar Rover {i}...")

            proc = subprocess.Popen([sys.executable, ROVER_SCRIPT, str(i)])
            rovers.append(proc)
            time.sleep(1) 
            
        print(f"\n[SUCESSO] {n_rovers} Rovers estão a correr em paralelo.")
        print("Verifique o terminal da Nave-Mãe e os ficheiros em 'telemetry_data/'.")
        print("Este teste vai correr durante 30 segundos...\n")
        
        time.sleep(30)
        
    except Exception as e:
        print(f"[ERRO] Falha ao lançar rovers: {e}")
        
    finally:

        print("\n -> A encerrar Rovers de teste...")
        for proc in rovers:
            proc.terminate()
            proc.wait()
        print("=== Teste Terminado ===")

if __name__ == "__main__":
    test_parallel_rovers()