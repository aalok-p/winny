import json
import os
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

import engine
import family
import risk_engine

here = os.path.dirname(os.path.abspath(__file__))
try:
    risk_engine.loadenv(os.path.join(here, ".env"))
except Exception:
    pass
envpath = os.path.join(here, ".env")
if os.path.exists(envpath):
    with open(envpath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def readbody(handler):
    length = int(handler.headers.get("Content-Length", 0))
    if not length:
        return {}
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw)
    except Exception:
        return {}

def sendjson(handler, data, status=200):
    body = json.dumps(data).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(body)

def sendcors(handler):
    handler.send_response(204)
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        sendcors(self)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)
        if path == "/api/history":
            familyid = qs.get("familyid", [None])[0]
            if not familyid:
                sendjson(self, {"error": "familyid required"}, 400)
                return
            sendjson(self, engine.history(familyid))
        elif path == "/api/holds":
            familyid = qs.get("familyid", [None])[0]
            if not familyid:
                sendjson(self, {"error": "familyid required"}, 400)
                return
            sendjson(self, engine.getholds(familyid))
        elif path == "/api/family":
            fid = qs.get("id", [None])[0]
            if not fid:
                sendjson(self, {"error": "id required"}, 400)
                return
            sendjson(self, family.getfamily(fid))
        elif path == "/api/cosigners":
            familyid = qs.get("familyid", [None])[0]
            memberid = qs.get("memberid", [None])[0]
            if not familyid or not memberid:
                sendjson(self, {"error": "familyid and memberid required"}, 400)
                return
            sendjson(self, family.getcosigners(familyid, memberid))
        else:
            sendjson(self, {"error": "not found"}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = readbody(self)
        if path == "/api/assess":
            payment = body.get("payment", {})
            history = body.get("history", {})
            rules = body.get("rules", {})
            sendjson(self, risk_engine.assess(payment, history, rules))
        elif path == "/api/propose":
            payment = body.get("payment", {})
            payerid = body.get("payerid")
            familyid = body.get("familyid")
            if not payerid or not familyid:
                sendjson(self, {"error": "payerid and familyid required"}, 400)
                return
            sendjson(self, engine.propose(payment, payerid, familyid))
        elif path == "/api/approved":
            holdid = body.get("holdid")
            if not holdid:
                sendjson(self, {"error": "holdid required"}, 400)
                return
            sendjson(self, engine.approved(holdid))
        elif path == "/api/decide":            
            holdid = body.get("holdid")
            cosignerid = body.get("cosignerid")
            action = body.get("action")
            if not holdid or not cosignerid or not action:
                sendjson(self, {"error": "holdid, cosignerid, and action required"}, 400)
                return
            sendjson(self, engine.decide(holdid, cosignerid, action))
        elif path == "/api/family":
            name = body.get("name")
            if not name:
                sendjson(self, {"error": "name required"}, 400)
                return
            sendjson(self, family.newfamily(name))
        elif path == "/api/member":
            familyid = body.get("familyid")
            name = body.get("name")
            email = body.get("email")
            roles = body.get("roles")
            if not familyid or not name or not email or not roles:
                sendjson(self, {"error": "familyid, name, email, and roles required"}, 400)
                return
            sendjson(self, family.addmember(familyid, name, email, roles))
        elif path == "/api/cosign":
            familyid = body.get("familyid")
            cosignerid = body.get("cosignerid")
            supervisedid = body.get("supervisedid")
            if not familyid or not cosignerid or not supervisedid:
                sendjson(self, {"error": "familyid, cosignerid, and supervisedid required"}, 400)
                return
            sendjson(self, family.addcosign(familyid, cosignerid, supervisedid))
        else:
            sendjson(self, {"error": "not found"}, 404)

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    port = 8081
    server = HTTPServer(("", port), Handler)
    print("Winny server on port " + str(port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()