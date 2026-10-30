# Pay

Four calls. In this order. Sandbox base URL is `https://api-m.sandbox.paypal.com`.

## 1. Create a hold

```
POST /v2/checkout/orders
{"intent": "AUTHORIZE", "purchase_units": [{"amount": {"currency_code": "USD", "value": "12.00"}}]}
```

Returns an order id. The buyer approves it in the checkout window. Status goes `CREATED` then `APPROVED`.

## 2. Authorize

```
POST /v2/checkout/orders/{order_id}/authorize
```

Returns an authorization id. This is the hold. Nothing has been captured yet.

## 3. Capture

```
POST /v2/payments/authorizations/{auth_id}/capture
```

Money moves. Capture twice and it complains, which is why every capture needs an idempotency key.

## 4. Void

```
POST /v2/payments/authorizations/{auth_id}/void
```

Money returns to the buyer. This is the stop path.

## The mistake to avoid

It is not `POST /v2/checkout/orders/{id}/capture` when the intent is `AUTHORIZE`. Capture happens on the authorization id, not the order id.

## Rules

- Sandbox only.
- Never log the client secret.
- Always void explicitly instead of waiting for the hold to lapse.
- Store the order id and the authorization id against the same payment record.
