"""Prototype pédagogique local, Python 3.10+, sans dépendance externe."""
import json
import sys
import threading
import webbrowser
from nlp import analyze, CATALOG
from vision import recognize, engine_check
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Handler(BaseHTTPRequestHandler):
    ocr_lock = threading.Lock()
    ocr_status = None
    def send(self, code, body, kind='application/json; charset=utf-8'):
        data = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/':
            self.send(200, Path(__file__).with_name('interface.html').read_text(encoding='utf-8'), 'text/html; charset=utf-8')
        elif self.path == '/health':
            if Handler.ocr_status is None:
                Handler.ocr_status=engine_check()
            self.send(200, json.dumps({'status':'ok','service':'PharmaDarija','version':4,'ocr':Handler.ocr_status},ensure_ascii=False))
        elif self.path == '/catalog':
            self.send(200, json.dumps({'medicaments': list(CATALOG), 'source':'catalogue_pedagogique_sans_stock'},ensure_ascii=False))
        elif self.path == '/dataset/exemple.png':
            image=Path(__file__).with_name('dataset')/'doliprane_net.png'
            if not image.exists():
                return self.send(404, '{"erreur":"Exemple absent"}')
            data=image.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type','image/png')
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send(404, '{"erreur":"Route inconnue"}')

    def do_POST(self):
        if self.path not in ('/analyze','/recognize'):
            return self.send(404, '{"erreur":"Route inconnue"}')
        try:
            length = int(self.headers.get('Content-Length', 0))
            maximum=9*1024*1024 if self.path=='/recognize' else 64000
            if length <= 0 or length > maximum:
                return self.send(400, '{"erreur":"Taille de requête invalide"}')
            data = json.loads(self.rfile.read(length))
            if self.path=='/recognize':
                if not isinstance(data,dict) or not isinstance(data.get('rotation_complete',False),bool):
                    return self.send(400,'{"erreur":"Objet JSON et rotation_complete booléen attendus"}')
                if not Handler.ocr_lock.acquire(blocking=False):
                    return self.send(429,'{"erreur":"Une lecture photo est déjà en cours. Réessayez dans quelques instants."}')
                try:
                    result=recognize(data.get('image_base64'),data.get('rotation_complete',False))
                    return self.send(200,json.dumps(result,ensure_ascii=False))
                except RuntimeError as error:
                    return self.send(503,json.dumps({'erreur':str(error)},ensure_ascii=False))
                finally:
                    Handler.ocr_lock.release()
            text = data.get('text') if isinstance(data, dict) else None
            if not isinstance(text, str) or not text.strip() or len(text) > 1000:
                return self.send(400, '{"erreur":"text doit contenir entre 1 et 1000 caractères"}')
            history = data.get('historique', [])
            if not isinstance(history,list) or len(history)>12 or any(not isinstance(m,str) or not m.strip() or len(m)>1000 for m in history):
                return self.send(400, '{"erreur":"historique doit contenir au plus 12 messages texte de 1 à 1000 caractères"}')
            self.send(200, json.dumps(analyze(text.strip(),history), ensure_ascii=False))
        except (ValueError, UnicodeDecodeError) as error:
            self.send(400,json.dumps({'erreur':str(error) if self.path=='/recognize' else 'JSON invalide'},ensure_ascii=False))

    def log_message(self, *_):
        pass  # Les messages patients ne sont pas consignés.


class LocalServer(ThreadingHTTPServer):
    # Sur Windows, empêcher deux démos d'écouter simultanément sur le même port.
    allow_reuse_address = False


if __name__ == '__main__':
    try:
        server = LocalServer(('127.0.0.1', 8000), Handler)
    except OSError:
        if '--open' in sys.argv:
            import urllib.request
            try:
                health=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2))
                if health.get('service')=='PharmaDarija' and health.get('version')==4:
                    webbrowser.open('http://127.0.0.1:8000')
                    sys.exit(0)
            except (OSError,ValueError):
                pass
        print('Le port 8000 est occupé. Arrêtez l’ancienne démo avant de relancer.')
        sys.exit(1)
    print('Démo PharmaDarija : http://127.0.0.1:8000\nArrêt : Ctrl+C')
    if '--open' in sys.argv:
        threading.Timer(0.7, lambda: webbrowser.open('http://127.0.0.1:8000')).start()
    server.serve_forever()
