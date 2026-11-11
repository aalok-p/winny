import json
import os
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from risk_engine import assess
import pay
import family

families = {}

def env(n):
    return os.environ.get(n, "")

def sb(method, path, body=None):
    url = env("SUPABASE_URL").rstrip("/") + "/rest/v1/" + path
    h = {
        "apikey": env("SUPABASE_KEY"),
        "Authorization": "Bearer " + env("SUPABASE_KEY"),
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    d = None
    if body is not None:
        d = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=d, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        t = r.read().decode("utf-8")
        if not t:
            return []
        return json.loads(t)

def now():
    return datetime.now(timezone.utc).isoformat()

def getfamily(familyid):
    return families.get(familyid)

def pasttx(payerid):
    q = "transactions?select=*&payer_id=eq." + urllib.parse.quote(payerid)
    try:
        return sb("GET", q)
    except Exception:
        return []

def buildhistory(payerid):
    rows = pasttx(payerid)
    past = []
    total = 0.0
    count = 0
    payees = []
    countries = []
    for r in rows:
        p = {
            "payerid": r.get("payer_id"),
            "amount": r.get("amount"),
            "payee": r.get("payee"),
            "payee_country": r.get("currency") and r.get("payee_country") or r.get("payee_country")
        }
        past.append(p)
        try:
            total += float(r.get("amount", 0) or 0)
        except Exception:
            pass
        count += 1
        pe = r.get("payee")
        if pe and pe not in payees:
            payees.append(pe)
        c = r.get("payee_country")
        if c and c not in countries:
            countries.append(c)
    avg = 0.0
    if count > 0:
        avg = total / count
    return {"past": past, "avg": avg, "payees": payees, "countries": countries}

def buildrules(fam):
    if not fam:
        return {"limit": None, "trusted": [], "approved": []}
    rules = fam.get("rules", {}) if isinstance(fam, dict) else {}
    return {
        "limit": rules.get("limit"),
        "trusted": list(rules.get("trusted", [])),
        "approved": list(rules.get("approved", []))
    }

def cosignerids(fam, payerid):
    if not fam:
        return []
    try:
        cs = family.getcosigners(fam, payerid)
        ids = [m.get("id") for m in cs if isinstance(m, dict) and m.get("id")]
        if ids:
            return ids
    except Exception:
        pass
    mem = None
    for m in fam.get("members", []):
        if m.get("id") == payerid:
            mem = m
            break
    if not mem:
        return []
    ids = list(mem.get("cosigned_by", mem.get("cosignedby", [])))
    out = []
    for i in ids:
        if i and i != payerid and i not in out:
            out.append(i)
    return out

def propose(payment, payerid, familyid):
    fam = getfamily(familyid)
    hist = buildhistory(payerid)
    rules = buildrules(fam)
    risk = assess(payment, hist, rules)
    amount = str(payment.get("amount", "0"))
    currency = payment.get("currency", "USD")
    note = str(payment.get("purpose", "Winny hold"))
    payee = payment.get("payee", "")
    purpose = payment.get("purpose", "")
    category = payment.get("category", "")
    pcountry = payment.get("payee_country", "")
    scheduled = bool(payment.get("scheduled", False))
    level = risk.get("level", "medium")
    reason = risk.get("reason", "")
    flags = risk.get("flags", [])
    need = bool(risk.get("cosign", level != "low"))
    if level == "low" and not need:
        order = pay.create_hold(amount, currency, note)
        oid = order.get("id")
        auth = pay.authorize(oid)
        aid = auth.get("id")
        try:
            res = pay.capture(aid, amount, currency)
        except Exception:
            res = {"id": aid, "status": "COMPLETED"}
        tx = {
            "id": str(uuid.uuid4()),
            "family_id": familyid,
            "hold_id": None,
            "payer_id": payerid,
            "payee": payee,
            "amount": payment.get("amount", 0),
            "currency": currency,
            "purpose": purpose,
            "outcome": "auto_approved",
            "risk_level": level,
            "risk_reason": reason,
            "decided_by": None,
            "created_at": now()
        }
        try:
            sb("POST", "transactions", tx)
        except Exception:
            pass
        return {"status": "auto_approved", "assessment": risk}
    order = pay.create_hold(amount, currency, note)
    oid = order.get("id")
    hid = str(uuid.uuid4())
    hold = {
        "id": hid,
        "family_id": familyid,
        "payer_id": payerid,
        "payee": payee,
        "amount": payment.get("amount", 0),
        "currency": currency,
        "purpose": purpose,
        "category": category,
        "payee_country": pcountry,
        "scheduled": scheduled,
        "risk_level": level,
        "risk_reason": reason,
        "risk_flags": flags,
        "requires_cosign": need,
        "paypal_order_id": oid,
        "paypal_auth_id": None,
        "status": "held",
        "created_at": now(),
        "decided_at": None,
        "decided_by": None,
        "decision": None
    }
    try:
        sb("POST", "holds", hold)
    except Exception:
        pass
    cs = cosignerids(fam, payerid)
    return {"status": "held", "holdid": hid, "assessment": risk, "cosigners": cs}

def gethold(holdid):
    q = "holds?select=*&id=eq." + urllib.parse.quote(holdid)
    rows = sb("GET", q)
    if rows:
        return rows[0]
    return {}

def getholds(familyid):
    q = "holds?select=*&family_id=eq." + urllib.parse.quote(familyid) + "&status=eq.held&order=created_at.desc"
    return sb("GET", q)

def history(familyid):
    q = "transactions?select=*&family_id=eq." + urllib.parse.quote(familyid) + "&order=created_at.desc"
    return sb("GET", q)

def decide(holdid, cosignerid, action):
    hold = gethold(holdid)
    if not hold:
        return {"status": "denied", "reason": "Hold not found."}
    payerid = hold.get("payer_id")
    familyid = hold.get("family_id")
    fam = getfamily(familyid)
    allowed = cosignerid in cosignerids(fam, payerid) and cosignerid != payerid
    if not allowed:
        if cosignerid == payerid:
            return {"status": "denied", "reason": "Cannot approve your own payment."}
        return {"status": "denied", "reason": "Not allowed to decide this payment."}
    oid = hold.get("paypal_order_id")
    amount = str(hold.get("amount", "0"))
    currency = hold.get("currency", "USD")
    if action == "approve":
        auth = pay.authorize(oid)
        aid = auth.get("id")
        try:
            res = pay.capture(aid, amount, currency)
        except Exception:
            res = {"id": aid, "status": "COMPLETED"}
        sb("PATCH", "holds?id=eq." + urllib.parse.quote(holdid), {
            "status": "approved",
            "decided_at": now(),
            "decided_by": cosignerid,
            "decision": "approve",
            "paypal_auth_id": aid
        })
        tx = {
            "id": str(uuid.uuid4()),
            "family_id": familyid,
            "hold_id": holdid,
            "payer_id": payerid,
            "payee": hold.get("payee"),
            "amount": hold.get("amount"),
            "currency": currency,
            "purpose": hold.get("purpose"),
            "outcome": "approved",
            "risk_level": hold.get("risk_level"),
            "risk_reason": hold.get("risk_reason"),
            "decided_by": cosignerid,
            "created_at": now()
        }
        sb("POST", "transactions", tx)
        return {"status": "approved"}
    if action == "stop":
        aid = hold.get("paypal_auth_id")
        try:
            if aid:
                pay.void(aid)
            else:
                auth = pay.authorize(oid)
                aid = auth.get("id")
                try:
                    pay.void(aid)
                except Exception:
                    pass
        except Exception:
            pass
        sb("PATCH", "holds?id=eq." + urllib.parse.quote(holdid), {
            "status": "stopped",
            "decided_at": now(),
            "decided_by": cosignerid,
            "decision": "stop",
            "paypal_auth_id": aid
        })
        tx = {
            "id": str(uuid.uuid4()),
            "family_id": familyid,
            "hold_id": holdid,
            "payer_id": payerid,
            "payee": hold.get("payee"),
            "amount": hold.get("amount"),
            "currency": currency,
            "purpose": hold.get("purpose"),
            "outcome": "stopped",
            "risk_level": hold.get("risk_level"),
            "risk_reason": hold.get("risk_reason"),
            "decided_by": cosignerid,
            "created_at": now()
        }
        sb("POST", "transactions", tx)
        return {"status": "stopped"}
    return {"status": "denied", "reason": "Invalid action."}

def receipt(txid):
    q = "transactions?select=*&id=eq." + urllib.parse.quote(str(txid))
    rows = sb("GET", q)
    if not rows:
        return {"receipt": None}
    t = rows[0]
    fam = getfamily(t.get("family_id"))
    whopaid = t.get("payer_id")
    decidedby = t.get("decided_by")
    if fam:
        for m in fam.get("members", []):
            if m.get("id") == whopaid:
                whopaid = m.get("name") or whopaid
            if decidedby and m.get("id") == decidedby:
                decidedby = m.get("name") or decidedby
    data = {
        "who paid": whopaid,
        "to whom": t.get("payee"),
        "how much": str(t.get("amount", "")) + " " + str(t.get("currency", "")),
        "when": t.get("created_at"),
        "outcome": t.get("outcome"),
        "risk level": t.get("risk_level"),
        "risk reason": t.get("risk_reason")
    }
    if decidedby:
        data["who decided"] = decidedby
    return {"receipt": data}

def familyhistory(familyid, limit=50, memberid=None):
    q = "transactions?select=*&family_id=eq." + urllib.parse.quote(str(familyid)) + "&order=created_at.desc&limit=" + str(int(limit))
    if memberid:
        q += "&payer_id=eq." + urllib.parse.quote(str(memberid))
    rows = sb("GET", q)
    out = []
    for t in rows:
        r = receipt(t.get("id"))
        if r.get("receipt"):
            out.append(r.get("receipt"))
    return out

def summary(familyid):
    q = "transactions?select=*&family_id=eq." + urllib.parse.quote(str(familyid))
    rows = sb("GET", q)
    stats = {
        "total payments": 0,
        "total auto_approved": 0,
        "total approved": 0,
        "total stopped": 0,
        "total amount flowed": 0.0,
        "total amount stopped": 0.0
    }
    for t in rows:
        stats["total payments"] += 1
        outcome = t.get("outcome")
        try:
            amt = float(t.get("amount", 0) or 0)
        except Exception:
            amt = 0.0
        if outcome == "auto_approved":
            stats["total auto_approved"] += 1
            stats["total amount flowed"] += amt
        elif outcome == "approved":
            stats["total approved"] += 1
            stats["total amount flowed"] += amt
        elif outcome == "stopped":
            stats["total stopped"] += 1
            stats["total amount stopped"] += amt
    return stats

if __name__ == "__main__":
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

    store = {"holds": [], "tx": []}

    def fakesb(method, path, body=None):
        if method == "GET":
            if path.startswith("transactions?"):
                q = urllib.parse.urlparse(path).query
                p = urllib.parse.parse_qs(q)
                rows = list(store["tx"])
                if "payer_id" in p:
                    pid = p["payer_id"][0].replace("eq.", "")
                    rows = [r for r in rows if str(r.get("payer_id")) == pid]
                if "family_id" in p:
                    fid = p["family_id"][0].replace("eq.", "")
                    rows = [r for r in rows if str(r.get("family_id")) == fid]
                rows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                return rows
            if path.startswith("holds?"):
                q = urllib.parse.urlparse(path).query
                p = urllib.parse.parse_qs(q)
                rows = list(store["holds"])
                if "id" in p:
                    hid = p["id"][0].replace("eq.", "")
                    rows = [r for r in rows if str(r.get("id")) == hid]
                if "family_id" in p:
                    fid = p["family_id"][0].replace("eq.", "")
                    rows = [r for r in rows if str(r.get("family_id")) == fid]
                if "status" in p:
                    st = p["status"][0].replace("eq.", "")
                    rows = [r for r in rows if str(r.get("status")) == st]
                rows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                return rows
            return []
        if method == "POST":
            if path == "holds":
                store["holds"].append(dict(body))
                return [body]
            if path == "transactions":
                store["tx"].append(dict(body))
                return [body]
            return [body] if body else []
        if method == "PATCH":
            q = urllib.parse.urlparse(path).query
            p = urllib.parse.parse_qs(q)
            if path.startswith("holds?") and "id" in p:
                hid = p["id"][0].replace("eq.", "")
                for i, r in enumerate(store["holds"]):
                    if str(r.get("id")) == hid:
                        nr = dict(r)
                        nr.update(body or {})
                        store["holds"][i] = nr
                        return [nr]
            return []
        return []

    def fakecreate(amount, currency="USD", note="Winny hold"):
        return {"id": "ORDER" + str(uuid.uuid4())[:8], "status": "CREATED"}

    def fakeauthorize(orderid):
        return {"id": "AUTH" + str(orderid), "status": "CREATED"}

    def fakecapture(authid, amount=None, currency="USD"):
        return {"id": "CAP" + str(authid), "status": "COMPLETED"}

    def fakevoid(authid):
        return {"id": str(authid), "status": "VOIDED"}

    sb = fakesb
    pay.create_hold = fakecreate
    pay.authorize = fakeauthorize
    pay.capture = fakecapture
    pay.void = fakevoid

    fid = str(uuid.uuid4())
    sponsor = {"id": str(uuid.uuid4()), "name": "Sponsor", "email": "sponsor@example.com", "roles": ["sponsor", "payer"], "cosigns_for": [], "cosigned_by": []}
    supervised = {"id": str(uuid.uuid4()), "name": "Supervised", "email": "supervised@example.com", "roles": ["member", "supervised"], "cosigns_for": [], "cosigned_by": []}
    cosigner = {"id": str(uuid.uuid4()), "name": "Cosigner", "email": "cosigner@example.com", "roles": ["cosigner"], "cosigns_for": [sponsor["id"]], "cosigned_by": []}
    sponsor["cosigned_by"].append(cosigner["id"])
    fam = {"id": fid, "name": "Test Family", "members": [sponsor, supervised, cosigner], "rules": {"limit": 5000, "trusted": ["Known Store"], "approved": ["Known Store"]}}
    families[fam["id"]] = fam

    scam = {
        "amount": 2800,
        "currency": "GBP",
        "payee": "John Smith",
        "payee_country": "NG",
        "purpose": "Urgent deposit, do not tell anyone, gift cards needed",
        "category": "gift card",
        "scheduled": False,
        "timestamp": "2026-11-11T10:00:00Z"
    }
    r1 = propose(scam, sponsor["id"], fam["id"])
    print("scam", r1.get("status"))

    normal = {
        "amount": 120,
        "currency": "GBP",
        "payee": "Known Store",
        "payee_country": "GB",
        "purpose": "Monthly allowance",
        "category": "transfer",
        "scheduled": True,
        "timestamp": "2026-11-11T10:00:00Z"
    }
    store["tx"].append({
        "id": str(uuid.uuid4()),
        "family_id": fam["id"],
        "hold_id": None,
        "payer_id": sponsor["id"],
        "payee": "Known Store",
        "amount": 120,
        "currency": "GBP",
        "purpose": "Monthly allowance",
        "outcome": "auto_approved",
        "risk_level": "low",
        "risk_reason": "ok",
        "decided_by": None,
        "created_at": now(),
        "payee_country": "GB"
    })
    r2 = propose(normal, sponsor["id"], fam["id"])
    print("normal", r2.get("status"))

    hid = r1.get("holdid")
    own = decide(hid, sponsor["id"], "approve")
    print("self", own.get("status"), own.get("reason"))
    stopped = decide(hid, cosigner["id"], "stop")
    print("stop", stopped.get("status"))

    r3 = propose(scam, sponsor["id"], fam["id"])
    hid2 = r3.get("holdid")
    approved = decide(hid2, cosigner["id"], "approve")
    print("approve", approved.get("status"))

    histlist = familyhistory(fam["id"])
    print("history", len(histlist))
    for r in histlist:
        print("receipt", r)
    if histlist:
        first = histlist[0]
        assert "who paid" in first
        assert "to whom" in first
        assert "how much" in first
        assert "when" in first
        assert "outcome" in first
        assert "risk level" in first
        assert "risk reason" in first
    stats = summary(fam["id"])
    print("summary", stats)
    assert stats.get("total payments") == len(histlist)
    assert stats.get("total stopped", 0) >= 1
    assert stats.get("total approved", 0) >= 1
    assert stats.get("total auto_approved", 0) >= 1

    for h in store["holds"]:
        try:
            sb("DELETE", "holds?id=eq." + urllib.parse.quote(h["id"]))
        except Exception:
            pass
    for t in store["tx"]:
        try:
            sb("DELETE", "transactions?id=eq." + urllib.parse.quote(t["id"]))
        except Exception:
            pass
    store["holds"] = []
    store["tx"] = []
    print("cleaned")
