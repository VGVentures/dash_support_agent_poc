"""Hooks that wrap every tool call.

pre_hook runs before a tool and can block, validate, or flag.
post_hook runs after a tool and handles audit and logging.
"""

import logging
from typing import Optional
from pydantic import ValidationError

log = logging.getLogger("dash.hooks")

REFUND_LIMIT = 200.0

# In-memory audit trail. Replace with your datastore.
AUDIT: list[dict] = []


class ToolBlocked(Exception):
    """Raised by a pre-hook to stop a tool before it runs."""


class ValidationFailed(Exception):
    """Raised when input validation fails."""

    def __init__(self, message: str, errors: Optional[list] = None):
        self.message = message
        self.errors = errors or []
        super().__init__(self.message)


def pre_hook(tool_name: str, tool_input: dict, ctx: dict) -> dict:
    if not ctx.get("user_id"):
        raise ToolBlocked("unauthenticated request")

    if tool_name == "process_refund":
        if not ctx.get("customer_verified"):
            raise ToolBlocked(
                "you must verify the customer identity first by calling get_customer, "
                "then confirm the order with lookup_order before processing a refund"
            )

        amount = float(tool_input.get("amount", 0))
        if amount > REFUND_LIMIT:
            raise ToolBlocked(
                f"refund of {amount} is over the {REFUND_LIMIT} limit, "
                "escalate to a human instead"
            )

    log.info(
        "tool_start name=%s user=%s input=%s",
        tool_name,
        ctx.get("user_id"),
        tool_input,
    )
    return tool_input


def post_hook(tool_name: str, tool_input: dict, result: dict, ctx: dict) -> dict:
    log.info("tool_end name=%s result=%s", tool_name, result)

    if tool_name == "get_customer" and result.get("found"):
        ctx["customer_verified"] = True
        log.info("customer_verified user=%s", ctx.get("user_id"))

    if tool_name == "process_refund" and result.get("status") == "refunded":
        AUDIT.append(
            {
                "user_id": ctx.get("user_id"),
                "action": "refund",
                "order_id": result.get("order_id"),
                "amount": result.get("amount"),
                "receipt_id": result.get("receipt_id"),
            }
        )

    return result
