"""Test the enhancements: validation, state enforcement, error handling."""

import json
from backend.agent.tools import (
    GetCustomerInput,
    LookupOrderInput,
    GetOrdersInput,
    ProcessRefundInput,
    EscalateToHumanInput,
)
from backend.agent.hooks import pre_hook, post_hook, ToolBlocked
from pydantic import ValidationError

print("=" * 60)
print("Testing Pydantic Validation")
print("=" * 60)

# Test 1: Valid inputs pass
try:
    customer = GetCustomerInput(identifier="C-1001")
    print("✓ GetCustomerInput: valid input accepted")
except ValidationError as e:
    print(f"✗ GetCustomerInput: {e}")

# Test 2: Empty identifier fails
try:
    customer = GetCustomerInput(identifier="")
    print("✗ GetCustomerInput: should reject empty identifier")
except ValidationError:
    print("✓ GetCustomerInput: empty identifier rejected")

# Test 3: Invalid refund amount fails
try:
    refund = ProcessRefundInput(order_id="O-5001", amount=-50, reason="test")
    print("✗ ProcessRefundInput: should reject negative amount")
except ValidationError:
    print("✓ ProcessRefundInput: negative amount rejected")

# Test 4: NaN amount fails
try:
    refund = ProcessRefundInput(order_id="O-5001", amount=float('nan'), reason="test")
    print("✗ ProcessRefundInput: should reject NaN")
except ValidationError:
    print("✓ ProcessRefundInput: NaN amount rejected")

# Test 5: Invalid priority fails
try:
    escalate = EscalateToHumanInput(summary="Help!", priority="urgent")
    print("✗ EscalateToHumanInput: should reject invalid priority")
except ValidationError:
    print("✓ EscalateToHumanInput: invalid priority rejected")

print()
print("=" * 60)
print("Testing Conversation State Enforcement")
print("=" * 60)

# Test 6: Refund blocked without customer verification
ctx = {"user_id": "test_user"}
try:
    pre_hook(
        "process_refund",
        {"order_id": "O-5001", "amount": 50, "reason": "test"},
        ctx,
    )
    print("✗ pre_hook: refund should be blocked without customer_verified")
except ToolBlocked as e:
    if "customer" in str(e).lower():
        print("✓ pre_hook: refund blocked until customer verified")
    else:
        print(f"✗ pre_hook: wrong error: {e}")

# Test 7: Customer verification sets state
ctx = {"user_id": "test_user"}
result = {"found": True, "customer": {"id": "C-1001"}}
post_hook("get_customer", {"identifier": "C-1001"}, result, ctx)
if ctx.get("customer_verified"):
    print("✓ post_hook: get_customer sets customer_verified=True")
else:
    print("✗ post_hook: customer_verified not set")

# Test 8: Refund allowed after customer verification
ctx = {"user_id": "test_user", "customer_verified": True}
try:
    safe_input = pre_hook(
        "process_refund",
        {"order_id": "O-5001", "amount": 50, "reason": "test"},
        ctx,
    )
    print("✓ pre_hook: refund allowed after customer_verified=True")
except ToolBlocked:
    print("✗ pre_hook: refund should be allowed when customer_verified=True")

print()
print("=" * 60)
print("Testing Order Sorting")
print("=" * 60)

# Test 9: Orders are sorted by date, most recent first
from backend.agent.tools import get_orders

result = get_orders("C-1001", max_items=10)
if result["found"]:
    orders = result["orders"]
    dates = [o["placed_at"] for o in orders]
    if dates == sorted(dates, reverse=True):
        print("✓ get_orders: orders sorted by date (most recent first)")
    else:
        print(f"✗ get_orders: dates not sorted: {dates}")
else:
    print("✗ get_orders: customer not found")

print()
print("=" * 60)
print("All tests completed!")
print("=" * 60)
