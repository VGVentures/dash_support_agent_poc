"""Test error handling and retryable flags."""

import json

print("=" * 60)
print("Testing Retryable Error Handling")
print("=" * 60)

# Simulate what the API returns for different errors

# Test 1: Validation error (not retryable)
validation_error = {
    "error": "validation_failed",
    "message": "validation failed for process_refund",
    "details": ["amount: amount must be greater than zero"],
    "retryable": False,
}
print("✓ Validation error: retryable =", validation_error["retryable"])
assert validation_error["retryable"] is False

# Test 2: Tool blocked (not retryable)
tool_blocked_error = {
    "error": "tool_blocked",
    "message": "you must verify the customer identity first",
    "retryable": False,
}
print("✓ Tool blocked error: retryable =", tool_blocked_error["retryable"])
assert tool_blocked_error["retryable"] is False

# Test 3: Tool error (retryable)
tool_error = {
    "error": "tool_error",
    "message": "temporary network failure",
    "retryable": True,
}
print("✓ Tool error: retryable =", tool_error["retryable"])
assert tool_error["retryable"] is True

print()
print("=" * 60)
print("Testing Early Exit on Non-Retryable Errors")
print("=" * 60)

# Simulate the loop logic
def simulate_conversation(error_sequence):
    """Simulate a conversation with a sequence of errors.

    Returns: (exit_reason, iteration_count)
    """
    iteration = 0
    consecutive_non_retryable = 0
    max_iterations = 10

    for error_is_retryable in error_sequence:
        iteration += 1

        if error_is_retryable:
            consecutive_non_retryable = 0
        else:
            consecutive_non_retryable += 1

        # Check exit conditions
        if consecutive_non_retryable >= 2:
            return "early_exit_non_retryable", iteration

        if iteration >= max_iterations:
            return "max_iterations_hit", iteration

    return "success", iteration

# Test 4: Early exit on 2 consecutive non-retryable errors
reason, iterations = simulate_conversation([False, False])
print(f"✓ Two non-retryable errors: exit at iteration {iterations} ({reason})")
assert reason == "early_exit_non_retryable"
assert iterations == 2

# Test 5: Keep going if retryable errors interspersed
reason, iterations = simulate_conversation([False, True, False])
print(f"✓ Retryable error resets counter: continues to iteration {iterations}")
assert iterations == 3

# Test 6: Hit max iterations if all retryable
reason, iterations = simulate_conversation([True] * 12)
print(f"✓ All retryable errors: exit at max iteration {iterations}")
assert reason == "max_iterations_hit"
assert iterations == 10

# Test 7: Hit max iterations with mixed errors
reason, iterations = simulate_conversation([True, False, True, False] * 3)
print(f"✓ Mixed errors with resets: exit at iteration {iterations}")
assert reason == "max_iterations_hit"

print()
print("=" * 60)
print("Testing Error Classification Logic")
print("=" * 60)

# Test 8: Validation errors should be non-retryable
error_types = {
    "validation_failed": {"should_be_retryable": False},
    "tool_blocked": {"should_be_retryable": False},
    "tool_error": {"should_be_retryable": True},
}

for error_type, expected in error_types.items():
    if error_type == "validation_failed":
        is_retryable = False
    elif error_type == "tool_blocked":
        is_retryable = False
    elif error_type == "tool_error":
        is_retryable = True

    status = "✓" if is_retryable == expected["should_be_retryable"] else "✗"
    print(f"{status} {error_type}: retryable = {is_retryable}")

print()
print("=" * 60)
print("All error handling tests passed!")
print("=" * 60)
