# Backend Enhancements for POC

## Summary of Changes

This document outlines the improvements made to the backend to increase robustness and user experience.

---

## 1. Pydantic Input Validation

**What:** Added Pydantic models for all tool inputs with strict validation.

**Files:**
- `backend/app/tools.py`: Added `GetCustomerInput`, `LookupOrderInput`, `GetOrdersInput`, `ProcessRefundInput`, `EscalateToHumanInput`

**Benefits:**
- Empty strings are trimmed and rejected
- Numeric ranges enforced (amounts > 0, max_items 1-100)
- Invalid enum values rejected (priority must be low/normal/high)
- Special float cases caught (NaN, Infinity)

**Example:**
```python
# This now fails validation instead of causing a silent error
ProcessRefundInput(order_id="", amount=-50, reason="")
# ValidationError: identifier cannot be empty
```

---

## 2. Structured Error Responses

**What:** All tool errors now return JSON with explicit error types.

**Files:**
- `backend/app/main.py`: Added `_validate_tool_input()` and updated error handling

**Error Types:**
- `validation_failed`: Input validation failed (includes field-level details)
- `tool_blocked`: Pre-hook blocked the tool (policy violation)
- `tool_error`: Tool crashed (rare, includes message)

**Example:**
```json
{
  "error": "validation_failed",
  "message": "validation failed for process_refund",
  "details": ["amount: amount must be greater than zero"]
}
```

Claude can now parse these and retry with different inputs instead of being confused.

---

## 3. Conversation State Enforcement

**What:** Refunds are blocked until a customer is verified via `get_customer`.

**Files:**
- `backend/app/hooks.py`: Pre-hook checks `ctx["customer_verified"]`, post-hook sets it
- `backend/app/main.py`: Context dict passed through the loop

**Behavior:**
1. `get_customer` call succeeds → sets `customer_verified=True` in context
2. Any `process_refund` call before that → blocked with a clear message
3. `process_refund` after verification → allowed

**Why:** Ensures Claude follows the correct flow: identify customer first, then refund.

---

## 4. Infinite Loop Guard

**What:** Added a maximum iteration limit to prevent runaway loops.

**Files:**
- `backend/app/main.py`: Loop now checks `iteration < max_iterations` (10 max)

**Behavior:**
- If Claude makes 10 tool calls without completing, the loop exits
- Returns a message suggesting escalation to human

**Why:** Protects against Claude getting stuck in a retry loop or hitting edge cases.

---

## 5. Order Sorting

**What:** `get_orders` now returns orders sorted by date, most recent first.

**Files:**
- `backend/app/tools.py`: Updated `get_orders()` to sort by `placed_at`

**Before:**
```python
orders = [order for order in _ORDERS.values() if ...]
orders_limited = orders[-max_items:]  # insertion order, unreliable
```

**After:**
```python
orders = sorted([...], key=lambda x: x["placed_at"], reverse=True)
orders_limited = orders[:max_items]  # guaranteed most recent first
```

---

## 6. Float Validation

**What:** `process_refund` now validates refund amounts against NaN and infinity.

**Files:**
- `backend/app/tools.py`: Added `validate_amount()` in `ProcessRefundInput`

**Why:** Catches edge cases where Claude might generate invalid floats.

---

## Testing

Run the test suite:
```bash
python test_enhancements.py
```

All tests should pass:
- ✓ Validation models reject invalid inputs
- ✓ Conversation state blocks refunds until customer verified
- ✓ Orders sorted by date
- ✓ NaN and Infinity rejected

---

## Next Steps (When Scaling)

When this moves beyond POC:
1. **Audit logging**: Move from in-memory to persistent database
2. **Auth**: Add actual user authentication instead of just `user_id`
3. **Error codes**: Expand error types for better Claude recovery strategies
4. **Idempotency**: Make refunds idempotent (check receipt exists before reprocessing)
5. **Timeouts**: Add timeout on tool calls themselves (not just loop iterations)
