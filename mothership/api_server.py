import http.server
import json
import logging

HOST = '0.0.0.0' 
PORT = 8080      

class MothershipHandler(http.server.BaseHTTPRequestHandler):
    r_db, r_lock = None, None
    m_db, c_db, m_lock = None, None, None

    def do_GET(self):
        if self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*') 
            self.end_headers()

            response_data = {
                "rovers": {},
                "missoes_pendentes": [],
                "missoes_concluidas": []
            }

            if self.r_lock and self.r_db is not None:
                with self.r_lock:
                    response_data["rovers"] = self.r_db.copy()
            
            if self.m_lock and self.m_db is not None:
                with self.m_lock:
                    response_data["missoes_pendentes"] = list(self.m_db)
                    response_data["missoes_concluidas"] = list(self.c_db)

            try:
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            except Exception as e:
                logging.error(f"[API] Erro JSON: {e}")
        else:
            self.send_error(404, "Endpoint nao encontrado")
    
    def log_message(self, format, *args): return

def run_api_server(r_db, r_lock, m_db, c_db, m_lock):
    logging.info(f"[API] A iniciar servidor HTTP na porta {PORT}...")
    
    MothershipHandler.r_db = r_db
    MothershipHandler.r_lock = r_lock
    MothershipHandler.m_db = m_db
    MothershipHandler.c_db = c_db
    MothershipHandler.m_lock = m_lock

    try:
        httpd = http.server.HTTPServer((HOST, PORT), MothershipHandler)
        logging.info(f"[API] Servidor API Online.")
        httpd.serve_forever()
    except Exception as e:
        logging.error(f"[API] Erro fatal: {e}")