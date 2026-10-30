"""Small PayPal helpers for Winny. Sandbox only, standard library only."""

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("PAYPAL_BASE", "https://api-m.sandbox.paypal.com")


def request(method, path, body=None, token=None, form=False):
    headers = {"Accept": "application/json"}
    data = None
    if form:
        data = urllib.parse.urlencode(body).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    if method == "POST":
        headers["Prefer"] = "return=representation"

    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            raw = res.read().decode()
            return res.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as err:
        raw = err.read().decode()
        try:
            return err.code, json.loads(raw)
        except json.JSONDecodeError:
            return err.code, {"raw": raw}


def token():
    client_id = os.environ["PAYPAL_CLIENT_ID"]
    secret = os.environ["PAYPAL_CLIENT_SECRET"]
    basic = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    status, payload = request(
        "POST", "/v1/oauth2/token", {"grant_type": "client_credentials"}, token=basic, form=True
    )
    if status != 200:
        raise RuntimeError(payload)
    return payload["access_token"]


def create_hold(amount, currency="USD", note="Winny hold"):
    body = {
        "intent": "AUTHORIZE",
        "purchase_units": [{"amount": {"currency_code": currency, "value": amount}, "description": note}],
        "payment_source": {"paypal": {"experience_context": {"brand_name": "Winny", "user_action": "PAY_NOW"}}},
    }
    status, payload = request("POST", "/v2/checkout/orders", body, token=token())
    if status not in (200, 201):
        raise RuntimeError(payload)
    return payload


def get_order(order_id):
    status, payload = request("GET", f"/v2/checkout/orders/{order_id}", token=token())
    if status != 200:
        raise RuntimeError(payload)
    return payload


def authorize(order_id):
    status, payload = request("POST", f"/v2/checkout/orders/{order_id}/authorize", {}, token=token())
    if status not in (200, 201):
        raise RuntimeError(payload)
    return payload["purchase_units"][0]["payments"]["authorizations"][0]


def capture(auth_id, amount=None, currency="USD"):
    body = {}
    if amount:
        body = {"amount": {"currency_code": currency, "value": amount}, "final_capture": True}
    status, payload = request("POST", f"/v2/payments/authorizations/{auth_id}/capture", body, token=token())
    if status not in (200, 201):
        raise RuntimeError(payload)
    return payload


def void(auth_id):
    status, payload = request("POST", f"/v2/payments/authorizations/{auth_id}/void", {}, token=token())
    if status not in (200, 204):
        raise RuntimeError(payload)
    return payload
