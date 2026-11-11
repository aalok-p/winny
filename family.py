import json
import os
import urllib.request
import urllib.error
import urllib.parse

def loadenv(path=".env"):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def supa(path, method, body):
    url = os.getenv("SUPABASE_URL", "").rstrip("/") + path
    key = os.getenv("SUPABASE_KEY", "")
    headers = {
        "apikey": key,
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return {}
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return json.loads(raw)
        except Exception:
            return {"error": raw, "status": e.code}

def newfamily(name):
    out = supa("/rest/v1/families", "POST", {"name": name})
    if isinstance(out, list) and out:
        return out[0]
    return out

def addmember(familyid, name, email, roles):
    out = supa("/rest/v1/members", "POST", {"family_id": familyid, "name": name, "email": email, "roles": roles})
    if isinstance(out, list) and out:
        return out[0]
    return out

def addcosign(familyid, cosignerid, supervisedid):
    out = supa("/rest/v1/cosigns", "POST", {"family_id": familyid, "cosigner_id": cosignerid, "supervised_id": supervisedid})
    if isinstance(out, list) and out:
        return out[0]
    return out

def getmembers(familyid):
    out = supa("/rest/v1/members?family_id=eq." + str(familyid), "GET", None)
    if isinstance(out, list):
        return out
    return []

def getfamily(familyid):
    f = supa("/rest/v1/families?id=eq." + str(familyid), "GET", None)
    fam = f[0] if isinstance(f, list) and f else f
    members = getmembers(familyid)
    cosigns = supa("/rest/v1/cosigns?family_id=eq." + str(familyid), "GET", None)
    if not isinstance(cosigns, list):
        cosigns = []
    if isinstance(fam, dict):
        fam["members"] = members
        fam["cosigns"] = cosigns
    return fam

def getcosigners(familyid, memberid):
    c = supa("/rest/v1/cosigns?family_id=eq." + str(familyid) + "&supervised_id=eq." + str(memberid), "GET", None)
    if not isinstance(c, list):
        return []
    res = []
    for x in c:
        cid = x.get("cosigner_id")
        m = supa("/rest/v1/members?id=eq." + str(cid), "GET", None)
        if isinstance(m, list) and m:
            res.append(m[0])
    return res

def getsupervised(familyid, memberid):
    c = supa("/rest/v1/cosigns?family_id=eq." + str(familyid) + "&cosigner_id=eq." + str(memberid), "GET", None)
    if not isinstance(c, list):
        return []
    res = []
    for x in c:
        sid = x.get("supervised_id")
        m = supa("/rest/v1/members?id=eq." + str(sid), "GET", None)
        if isinstance(m, list) and m:
            res.append(m[0])
    return res

def rmmember(familyid, memberid):
    supa("/rest/v1/cosigns?cosigner_id=eq." + str(memberid), "DELETE", None)
    supa("/rest/v1/cosigns?supervised_id=eq." + str(memberid), "DELETE", None)
    out = supa("/rest/v1/members?id=eq." + str(memberid) + "&family_id=eq." + str(familyid), "DELETE", None)
    return out

if __name__ == "__main__":
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    loadenv(os.path.join(here, ".env"))
    fam = newfamily("The Desais")
    fid = fam.get("id")
    print("family", fam)
    ravi = addmember(fid, "Ravi", "ravi@example.com", ["sponsor"])
    meera = addmember(fid, "Meera", "meera@example.com", ["member", "supervised"])
    arjun = addmember(fid, "Arjun", "arjun@example.com", ["cosigner"])
    nani = addmember(fid, "Nani", "nani@example.com", ["supervised"])
    addcosign(fid, arjun.get("id"), meera.get("id"))
    addcosign(fid, arjun.get("id"), nani.get("id"))
    print("getfamily", getfamily(fid))
    cs = getcosigners(fid, meera.get("id"))
    print("cosigners for Meera", [m.get("name") for m in cs])
    supv = getsupervised(fid, arjun.get("id"))
    print("supervised by Arjun", [m.get("name") for m in supv])
    supa("/rest/v1/cosigns?family_id=eq." + str(fid), "DELETE", None)
    supa("/rest/v1/members?family_id=eq." + str(fid), "DELETE", None)
    supa("/rest/v1/families?id=eq." + str(fid), "DELETE", None)
    print("cleaned up")
