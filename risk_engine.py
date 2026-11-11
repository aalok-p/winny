import json
import os
import urllib.request
import urllib.error

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

def buildprompt(payment, history, rules):
    return (
        "You are a payment fraud detector for a family money app called Winny. Analyze this payment and return ONLY valid JSON, no other text.\n\n"
        "Payment: " + json.dumps(payment, ensure_ascii=True) + "\n"
        "Payer history: " + json.dumps(history, ensure_ascii=True) + "\n"
        "Family rules: " + json.dumps(rules, ensure_ascii=True) + "\n\n"
        "Look for contradictions and suspicious patterns:\n"
        "- Does the purpose match the payee type? (rent should go to companies, tuition to universities, medical to hospitals)\n"
        "- Does the country in the purpose match the payee country?\n"
        "- Is the amount appropriate for the stated purpose?\n"
        "- Is there urgency or secrecy language? Legitimate payments never ask for secrecy.\n"
        "- Is this a new payee with a large or unusual request?\n"
        "- Does anything about this feel structurally impossible or contradictory?\n\n"
        "Return this exact JSON format:\n"
        "{\n"
        "  \"level\": \"low\" or \"medium\" or \"high\",\n"
        "  \"reason\": \"one plain-English sentence explaining the decision\",\n"
        "  \"flags\": [\"list\", \"of\", \"specific\", \"issues\", \"found\"],\n"
        "  \"cosign\": true or false\n"
        "}\n\n"
        "Rules for your decision:\n"
        "- Secrecy language (don't tell, keep secret, between us, confidential) = always high, always cosign\n"
        "- New payee + urgency + large amount = high, cosign\n"
        "- New payee with normal amount and no other issues = medium, cosign false (caution only)\n"
        "- Known trusted payee + scheduled + normal amount = low, cosign false\n"
        "- Any structural contradiction (purpose vs payee mismatch, country mismatch) on new payee = high, cosign\n"
        "- Use your judgment for edge cases. Err on the side of caution."
    )

def callai(prompt):
    key = os.getenv("AI_API_KEY", "")
    base = os.getenv("AI_BASE_URL", "")
    model = os.getenv("AI_MODEL", "")
    if not key or not base or not model:
        raise RuntimeError("missing ai config")
    url = base.rstrip("/") + "/chat/completions"
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json"
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        out = json.loads(resp.read().decode("utf-8"))
    text = out["choices"][0]["message"]["content"]
    return text

def parse(text):
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end >= start:
        t = t[start:end + 1]
    obj = json.loads(t)
    level = str(obj.get("level", "")).lower()
    if level not in ["low", "medium", "high"]:
        level = "medium"
    reason = str(obj.get("reason", "This payment needs a closer look."))
    flags = obj.get("flags", [])
    if not isinstance(flags, list):
        flags = [str(flags)]
    flags = [str(x) for x in flags]
    cosign = bool(obj.get("cosign", level == "high"))
    return {"level": level, "reason": reason, "flags": flags, "cosign": cosign}

def fallback(payment, history, rules):
    payee = str(payment.get("payee", ""))
    purpose = str(payment.get("purpose", "")).lower()
    amount = float(payment.get("amount", 0) or 0)
    payees = history.get("payees", []) if isinstance(history, dict) else []
    known = False
    for p in payees:
        if str(p).lower() == payee.lower():
            known = True
            break
    avg = 0
    if isinstance(history, dict):
        try:
            avg = float(history.get("avg", 0) or 0)
        except Exception:
            avg = 0
    secrecywords = ["don't tell", "keep secret", "between us", "confidential"]
    secrecy = any(w in purpose for w in secrecywords)
    flags = []
    if secrecy:
        flags.append("secrecy")
        return {"level": "high", "reason": "The message asks you to keep this secret. Legitimate payments never do.", "flags": flags, "cosign": True}
    large = amount >= 1000 or (avg > 0 and amount > avg * 3)
    if not known and large:
        flags.append("new payee large amount")
        return {"level": "high", "reason": "This is a large payment to someone you have not paid before.", "flags": flags, "cosign": True}
    if not known:
        flags.append("new payee")
        return {"level": "medium", "reason": "This is your first payment to " + payee + ".", "flags": flags, "cosign": False}
    return {"level": "low", "reason": "This payment looks normal based on what we can see.", "flags": flags, "cosign": False}

def assess(payment, history, rules):
    try:
        prompt = buildprompt(payment, history, rules)
        text = callai(prompt)
        return parse(text)
    except Exception:
        return fallback(payment, history, rules)

if __name__ == "__main__":
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    loadenv(os.path.join(here, ".env"))
    scamrent = {
        "amount": 2800,
        "currency": "GBP",
        "payee": "John Smith",
        "payee_country": "NG",
        "purpose": "Urgent deposit for London apartment, don't tell anyone",
        "scheduled": False,
        "timestamp": "2026-11-11T10:00:00Z"
    }
    history1 = {"past": [], "avg": 100, "payees": [], "countries": []}
    rules = {"limit": 5000, "trusted": [], "approved": []}
    scamtuition = {
        "amount": 5000,
        "currency": "USD",
        "payee": "Sunshine Travel Agency",
        "payee_country": "US",
        "purpose": "University tuition fee for semester",
        "scheduled": False,
        "timestamp": "2026-11-11T10:00:00Z"
    }
    history2 = {"past": [], "avg": 100, "payees": [], "countries": []}
    allowance = {
        "amount": 120,
        "currency": "GBP",
        "payee": "British Gas",
        "payee_country": "GB",
        "purpose": "Monthly gas bill",
        "scheduled": True,
        "timestamp": "2026-11-11T10:00:00Z"
    }
    history3 = {"past": [], "avg": 120, "payees": ["British Gas"], "countries": ["GB"]}
    rules3 = {"limit": 5000, "trusted": ["British Gas"], "approved": ["British Gas"]}
    if not os.getenv("AI_API_KEY"):
        print("Set AI_API_KEY, AI_BASE_URL, and AI_MODEL to run live tests.")
        r1 = fallback(scamrent, history1, rules)
        r2 = fallback(scamtuition, history2, rules)
        r3 = fallback(allowance, history3, rules3)
    else:
        r1 = assess(scamrent, history1, rules)
        r2 = assess(scamtuition, history2, rules)
        r3 = assess(allowance, history3, rules3)
    print("PASS" if r1.get("level") == "high" else "FAIL", "Rent scam", r1.get("level"), r1.get("reason"))
    print("PASS" if r2.get("level") == "high" else "FAIL", "Tuition scam", r2.get("level"), r2.get("reason"))
    print("PASS" if r3.get("level") == "low" else "FAIL", "Monthly allowance", r3.get("level"), r3.get("reason"))