---
applyTo: "**/*{cart,checkout,order,payment,inventory,product,price,refund,commission,seller}*.py,**/commerce/**"
---

# Marketplace commerce invariants

- Server-side state is authoritative for prices, discounts, taxes, shipping, stock,
  payment state, commissions, refunds, and order transitions.
- Recalculate totals server-side; never trust client-supplied totals.
- Use idempotency for payment, webhook, order submission, and settlement operations.
- Use atomic transactions and explicit state machines for critical commerce flows.
- Record auditable state transitions and reconcile asynchronous provider events.
- Prevent sellers and customers from reading or mutating each other's private data.
- Add race-condition, duplicate-event, retry, and partial-failure tests.
