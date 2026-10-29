
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("PAYPAL_BASE", "https://api-m.sandbox.paypal.com")


def load_env(path=".env"):
    if not os.path.exists(path):
        return
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def request(method, path, body=None, token=None, form=False):
    url = BASE + path
    data = None
    headers = {"Accept": "application/json"}

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

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            raw = res.read().decode()
            return res.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as err:
        raw = err.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return err.code, payload


def access_token():
    client_id = os.environ.get("PAYPAL_CLIENT_ID")
    secret = os.environ.get("PAYPAL_CLIENT_SECRET")
    if not client_id or not secret:
        sys.exit(
            "Missing PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET.\n"
            "Copy .env.example to .env and paste your sandbox app credentials."
        )

    basic = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    status, payload = request(
        "POST",
        "/v1/oauth2/token",
        {"grant_type": "client_credentials"},
        token=basic,
        form=True,
    )
    if status != 200 or "access_token" not in payload:
        sys.exit(f"Token request failed ({status}): {json.dumps(payload, indent=2)}")
    return payload["access_token"]


def create_order(amount, currency, note="Winny sandbox test"):
    client_id = os.environ.get("PAYPAL_CLIENT_ID")
    token = access_token()
    body = {
        "intent": "AUTHORIZE",
        "purchase_units": [
            {
                "amount": {"currency_code": currency, "value": amount},
                "description": note,
            }
        ],
        "payment_source": {
            "paypal": {
                "experience_context": {
                    "brand_name": "Winny",
                    "user_action": "PAY_NOW",
                    "shipping_preference": "NO_SHIPPING",
                }
            }
        },
    }
    status, payload = request("POST", "/v2/checkout/orders", body, token=token)
    if status not in (200, 201):
        sys.exit(f"Order creation failed ({status}): {json.dumps(payload, indent=2)}")

    order = {"id": payload["id"], "status": payload.get("status")}
    for link in payload.get("links", []):
        if link.get("rel") in ("approve", "payer-action"):
            order["approve"] = link["href"]
    print(f"Order created: {order['id']}  status={order['status']}")
    if order.get("approve"):
        print(f"Approve as the sandbox buyer: {order['approve']}")
        print(f"   client_id={client_id[:6]}...")
    return order


def show_order(order_id):
    token = access_token()
    status, payload = request("GET", f"/v2/checkout/orders/{order_id}", token=token)
    if status != 200:
        sys.exit(f"Order fetch failed ({status}): {json.dumps(payload, indent=2)}")
    return payload


def wait_for_approval(order_id, timeout=300):
    print("\nWaiting for buyer approval in the sandbox checkout window...")
    deadline = time.time() + timeout
    seen = None
    while time.time() < deadline:
        payload = show_order(order_id)
        state = payload.get("status")
        if state != seen:
            print(f"   status: {state}")
            seen = state
        if state in ("APPROVED", "COMPLETED"):
            return payload
        if state in ("VOIDED", "PAYER_ACTION_REQUIRED") and state == "VOIDED":
            sys.exit("Order was voided before approval.")
        time.sleep(5)
    sys.exit(
        "Timed out waiting for approval.\n"
        "Open the approval link, sign in with a sandbox PERSONAL account, and click Pay."
    )


def authorize(order_id):
    token = access_token()
    status, payload = request("POST", f"/v2/checkout/orders/{order_id}/authorize", {}, token=token)
    if status not in (200, 201):
        sys.exit(
            f"Authorize failed ({status}): {json.dumps(payload, indent=2)}\n"
            "If this says ORDER_NOT_APPROVED, the buyer has not approved yet."
        )

    try:
        auth = payload["purchase_units"][0]["payments"]["authorizations"][0]
    except (KeyError, IndexError):
        sys.exit(f"Unexpected authorize payload: {json.dumps(payload, indent=2)}")

    print(f"Authorization created: {auth['id']}  status={auth.get('status')}")
    print(f"   valid until: {auth.get('expiration_time', 'n/a')}")
    return auth


def capture(auth_id, amount=None, currency=None):
    token = access_token()
    body = {}
    if amount and currency:
        body = {"amount": {"currency_code": currency, "value": amount}, "final_capture": True}
    status, payload = request("POST", f"/v2/payments/authorizations/{auth_id}/capture", body, token=token)
    if status not in (200, 201):
        sys.exit(f"Capture failed ({status}): {json.dumps(payload, indent=2)}")
    print(f"Captured: {payload.get('id')}  status={payload.get('status')}  amount={payload.get('amount')}")
    return payload


def void(auth_id):
    token = access_token()
    status, payload = request("POST", f"/v2/payments/authorizations/{auth_id}/void", {}, token=token)
    if status not in (200, 204):
        sys.exit(f"Void failed ({status}): {json.dumps(payload, indent=2)}")
    print(f"Voided: status={payload.get('status', 'NO_CONTENT')}  money returned to the buyer")
    return payload


def run_flow(amount, currency):
    order = create_order(amount, currency)
    approved = wait_for_approval(order["id"])
    print(f"\nBuyer approved. Order status: {approved.get('status')}")

    auth = authorize(order["id"])
    auth_id = auth["id"]

    print("\nThe hold now exists. Nothing has been captured.")
    answer = input("Capture or void? [c/v] (default c): ").strip().lower() or "c"

    if answer.startswith("v"):
        void(auth_id)
        print("\nResult: hold released, buyer keeps the money. This is the Winny stop path.")
    else:
        capture(auth_id, amount, currency)
        print("\nResult: money moved. This is the Winny approve path.")
    return 0


def main(argv):
    load_env()
    if len(argv) < 2 or argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return 0

    command = argv[1]
    args = argv[2:]
    amount = "12.00"
    currency = "USD"
    if "--amount" in args:
        amount = args[args.index("--amount") + 1]
    if "--currency" in args:
        currency = args[args.index("--currency") + 1]

    if command == "flow":
        return run_flow(amount, currency)
    if command == "order":
        create_order(amount, currency)
        return 0
    if command == "show" and args:
        print(json.dumps(show_order(args[0]), indent=2))
        return 0
    if command == "authorize" and args:
        authorize(args[0])
        return 0
    if command == "capture" and args:
        capture(args[0], amount, currency)
        return 0
    if command == "void" and args:
        void(args[0])
        return 0

    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
