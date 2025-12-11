import unittest
from unittest.mock import MagicMock, patch
import socket
import sys
import os

# Setup do path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importar a função que queremos testar
from rover.mission_link_client import message_to_mother

class TestMissionReliability(unittest.TestCase):

    def test_retransmission_on_timeout(self):
        """
        Cenário: Perda de Pacotes (Simulada).
        A Nave-Mãe não responde (Timeout). O Rover deve tentar 3 vezes.
        """
        print("\n=== TESTE: Lógica de Retransmissão (Perda de Pacotes) ===")
        
        # 1. Criar um Mock do Socket
        mock_sock = MagicMock()
        
        # Configurar o mock para lançar 'timeout' sempre que fizermos recvfrom
        mock_sock.recvfrom.side_effect = socket.timeout
        
        # 2. Executar a função (Rover 1, Seq 10, msg "MReq")
        # Esperamos que devolva False após esgotar as tentativas
        resultado = message_to_mother(1, 10, 0, "MReq", "", mock_sock)
        
        # 3. Validações
        self.assertFalse(resultado, "A função deve retornar False quando esgota as tentativas.")
        
        # O mais importante: Verificar se o sendto foi chamado 3 vezes (Retransmissão)
        self.assertEqual(mock_sock.sendto.call_count, 3, "O Rover devia ter retransmitido 3 vezes!")
        print(" -> Sucesso: O Rover retransmitiu 3 vezes perante timeouts.")

    @patch('rover.mission_link_client.header_parser') # Mockar o parser para facilitar
    def test_success_after_failure(self, mock_parser):
        """
        Cenário: Latência/Perda Parcial.
        A 1ª tentativa falha (Timeout), mas a 2ª funciona.
        """
        print("\n=== TESTE: Sucesso após Falha (Latência) ===")
        
        mock_sock = MagicMock()
        
        # Configurar efeitos sequenciais:
        # 1ª chamada a recvfrom -> Timeout (Perda)
        # 2ª chamada a recvfrom -> Sucesso (Dados válidos)
        sucesso_payload = b"HEADER_VALIDO..."
        mock_sock.recvfrom.side_effect = [socket.timeout, (sucesso_payload, ('10.0.0.1', 5000))]
        
        # Configurar o parser para devolver um ACK válido na 2ª vez
        mock_parser.return_value = {
            'ack_seq': 20, # Corresponde ao nosso seq enviado
            'message_type': 'MAck',
            'payload': ''
        }
        
        # Executar (Seq 20)
        resultado = message_to_mother(1, 20, 0, "MRep", "DADOS", mock_sock)
        
        # Validações
        self.assertTrue(resultado, "A função devia ter sucesso na 2ª tentativa.")
        self.assertEqual(mock_sock.sendto.call_count, 2, "O Rover devia ter enviado 2 vezes (1 original + 1 retry).")
        print(" -> Sucesso: O Rover recuperou após 1 pacote perdido.")

if __name__ == '__main__':
    unittest.main()