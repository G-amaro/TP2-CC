import http.server
import json
import logging

HOST = '0.0.0.0' 
PORT = 8080      

class MothershipHandler(http.server.BaseHTTPRequestHandler):
    db = None
    lock = None

    def do_GET(self):

        if self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*') 
            self.end_headers()

            response_data = {
                "rovers": {},
                "missoes": [] 
            }

            if self.lock and self.db is not None:
                with self.lock:
                    response_data["rovers"] = self.db.copy()
            
            try:
                message = json.dumps(response_data)
                self.wfile.write(message.encode('utf-8'))
            except Exception as e:
                logging.error(f"[API] Erro JSON: {e}")

        else:
            self.send_error(404, "Endpoint nao encontrado")

    def log_message(self, format, *args):
        return

def run_api_server(database, lock):
    logging.info(f"[API] A iniciar servidor HTTP na porta {PORT}...")
    
    MothershipHandler.db = database
    MothershipHandler.lock = lock

    try:
        server_address = (HOST, PORT)
        httpd = http.server.HTTPServer(server_address, MothershipHandler)
        logging.info(f"[API] Servidor API Online.")
        httpd.serve_forever()
    except Exception as e:
        logging.error(f"[API] Erro fatal: {e}")