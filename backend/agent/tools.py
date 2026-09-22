"""Support assistant tools for the Claude tool-use loop.

Five custom tools: get_customer, lookup_order, get_orders, process_refund, escalate_to_human.

Each tool has two parts:
  1. A schema in TOOLS, sent to the Anthropic API so Claude knows when to call it.
  2. A Python function in TOOL_IMPL that the backend runs when Claude asks for it.

The MOCK STORE section is a stand-in so this file runs on its own. Replace the
marked spots with your real database, payment provider, and help desk.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# --------------------------------------------------------------------------
# MOCK STORE  (replace with your real systems)
# --------------------------------------------------------------------------

_CUSTOMERS = {
    "C-1001": {
        "id": "C-1001",
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "tier": "gold",
        "since": "2021-03-12",
    },
    "C-1002": {
        "id": "C-1002",
        "name": "Alan Turing",
        "email": "alan@example.com",
        "tier": "standard",
        "since": "2023-08-01",
    },
}

_ORDERS = {
    "O-5001": {
        "id": "O-5001",
        "customer_id": "C-1001",
        "status": "delivered",
        "items": [{"name": "Wireless keyboard", "qty": 1, "price": 79.0}],
        "total": 79.0,
        "placed_at": "2024-11-02",
        "delivered_at": "2024-11-05",
        "refundable": True,
    },
    "O-5002": {
        "id": "O-5002",
        "customer_id": "C-1001",
        "status": "shipped",
        "items": [{"name": "USB-C hub", "qty": 2, "price": 35.0}],
        "total": 70.0,
        "placed_at": "2025-01-10",
        "delivered_at": None,
        "refundable": False,
    },
    "O-5003": {
        "id": "O-5003",
        "customer_id": "C-1002",
        "status": "delivered",
        "items": [{"name": "Laptop stand", "qty": 1, "price": 42.0}],
        "total": 42.0,
        "placed_at": "2025-02-18",
        "delivered_at": "2025-02-21",
        "refundable": True,
    },
    "O-5004": {
        "id": "O-5004",
        "customer_id": "C-1001",
        "status": "delivered",
        "items": [{"name": "Premium monitor 4K", "qty": 1, "price": 499.0}],
        "total": 499.0,
        "placed_at": "2025-03-01",
        "delivered_at": "2025-03-05",
        "refundable": True,
    },
}

_REFUNDS: list[dict] = []
_TICKETS: list[dict] = []


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _find_customer(identifier: str) -> dict | None:
    ident = identifier.strip().lower()
    for cust in _CUSTOMERS.values():
        if cust["id"].lower() == ident or cust["email"].lower() == ident:
            return cust
    return None


# --------------------------------------------------------------------------
# PYDANTIC INPUT MODELS (validation)
# --------------------------------------------------------------------------

class GetCustomerInput(BaseModel):
    identifier: str = Field(..., description="Customer id (e.g. C-1001) or email address.")

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("identifier cannot be empty")
        return v.strip()


class LookupOrderInput(BaseModel):
    order_id: str = Field(..., description="Order id, e.g. O-5001.")
    customer_id: Optional[str] = Field(None, description="Optional. Confirm the order belongs to this customer.")

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("order_id cannot be empty")
        return v.strip()

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return v.strip()
        return None


class GetOrdersInput(BaseModel):
    customer_id: str = Field(..., description="Customer id, e.g. C-1001.")
    max_items: int = Field(5, ge=1, le=100, description="Maximum number of orders to return. Defaults to 5.")

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("customer_id cannot be empty")
        return v.strip()


class ProcessRefundInput(BaseModel):
    order_id: str = Field(..., description="Order id, e.g. O-5001.")
    amount: float = Field(..., gt=0, description="Refund amount in the order currency.")
    reason: str = Field(..., description="Short reason for the refund.")

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("order_id cannot be empty")
        return v.strip()

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("amount must be a valid number")
        if v <= 0:
            raise ValueError("amount must be greater than zero")
        return v

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("reason cannot be empty")
        return v.strip()


class EscalateToHumanInput(BaseModel):
    summary: str = Field(..., description="What the human needs to know.")
    priority: str = Field("normal", description="Priority level for the ticket.")
    customer_id: Optional[str] = Field(None, description="Optional customer id.")

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("summary cannot be empty")
        return v.strip()

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in ["low", "normal", "high"]:
            raise ValueError("priority must be one of: low, normal, high")
        return v

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return v.strip()
        return None


# --------------------------------------------------------------------------
# TOOL IMPLEMENTATIONS
# --------------------------------------------------------------------------

def get_customer(identifier: str) -> dict:
    """Look up a customer by id or email. Returns the profile or a not_found marker."""
    customer = _find_customer(identifier)          # replace: db.find_customer(identifier)
    if customer is None:
        return {"found": False, "identifier": identifier}
    return {"found": True, "customer": customer}


def lookup_order(order_id: str, customer_id: str | None = None) -> dict:
    """Fetch one order by id. If customer_id is given, confirm the order belongs to them."""
    order = _ORDERS.get(order_id.strip())           # replace: db.get_order(order_id)
    if order is None:
        return {"found": False, "order_id": order_id}
    if customer_id is not None and order["customer_id"] != customer_id:
        return {"found": False, "order_id": order_id, "reason": "does not belong to customer"}
    return {"found": True, "order": order}


def get_orders(customer_id: str, max_items: int = 10) -> dict:
    """Fetch orders for a customer with a limit. Returns the most recent orders or not_found."""
    cust_id = customer_id.strip()
    if cust_id not in _CUSTOMERS:
        return {"found": False, "customer_id": cust_id}
    orders = sorted(
        [order for order in _ORDERS.values() if order["customer_id"] == cust_id],
        key=lambda x: x["placed_at"],
        reverse=True,
    )
    orders_limited = orders[:max_items]
    total_count = len(orders)
    return {
        "found": True,
        "customer_id": cust_id,
        "orders": orders_limited,
        "total_count": total_count,
        "showing": len(orders_limited),
    }


def process_refund(order_id: str, amount: float, reason: str) -> dict:
    """Issue a refund for an order. Validates the order exists, is refundable, and the
    amount does not exceed the order total. Money side effects live here."""
    order = _ORDERS.get(order_id.strip())
    if order is None:
        return {"status": "rejected", "reason": "order not found", "order_id": order_id}
    if not order["refundable"]:
        return {"status": "rejected", "reason": "order is not refundable", "order_id": order_id}
    if amount <= 0 or amount > order["total"]:
        return {
            "status": "rejected",
            "reason": "amount must be greater than zero and at most the order total",
            "order_id": order_id,
            "order_total": order["total"],
        }

    receipt_id = f"R-{len(_REFUNDS) + 9001}"        # replace: payments.refund(order_id, amount)
    record = {
        "receipt_id": receipt_id,
        "order_id": order_id,
        "amount": amount,
        "reason": reason,
        "refunded_at": _now(),
    }
    _REFUNDS.append(record)                          # replace: db.write_refund(record)
    return {"status": "refunded", "order_id": order_id, "amount": amount, "receipt_id": receipt_id}


def escalate_to_human(summary: str, priority: str = "normal", customer_id: str | None = None) -> dict:
    """Hand the conversation to a human agent. Creates a ticket in the help desk."""
    ticket_id = f"T-{len(_TICKETS) + 1029}"          # replace: helpdesk.create_ticket(...)
    ticket = {
        "ticket_id": ticket_id,
        "summary": summary,
        "priority": priority,
        "customer_id": customer_id,
        "status": "queued",
        "created_at": _now(),
    }
    _TICKETS.append(ticket)
    return {"ticket_id": ticket_id, "status": "queued", "priority": priority}


# --------------------------------------------------------------------------
# TOOL SCHEMAS  (sent to the Anthropic API)
# --------------------------------------------------------------------------

TOOLS = [
    {
        "name": "get_customer",
        "description": (
            "Look up a customer account by their customer id or email address. "
            "Use this first to confirm who you are talking to before acting on an order."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "identifier": {
                    "type": "string",
                    "description": "Customer id (e.g. C-1001) or email address.",
                }
            },
            "required": ["identifier"],
        },
    },
    {
        "name": "lookup_order",
        "description": (
            "Fetch the details and status of a single order by its order id. "
            "Pass customer_id to verify the order belongs to that customer."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order id, e.g. O-5001."},
                "customer_id": {
                    "type": "string",
                    "description": "Optional. Confirm the order belongs to this customer.",
                },
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "get_orders",
        "description": (
            "Fetch orders for a customer by their customer id. "
            "Returns the most recent orders up to the max_items limit. "
            "Use this to see a customer's order history."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer id, e.g. C-1001."},
                "max_items": {
                    "type": "integer",
                    "description": "Maximum number of orders to return. Defaults to 5.",
                    "default": 5,
                },
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "process_refund",
        "description": (
            "Issue a refund for an order. Only call after confirming the order exists, "
            "is refundable, and the amount is at most the order total."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "amount": {"type": "number", "description": "Refund amount in the order currency."},
                "reason": {"type": "string", "description": "Short reason for the refund."},
            },
            "required": ["order_id", "amount", "reason"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": (
            "Hand the conversation to a human agent when the issue is out of policy, "
            "the customer is upset, or you cannot resolve it with the other tools."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "What the human needs to know."},
                "priority": {"type": "string", "enum": ["low", "normal", "high"]},
                "customer_id": {"type": "string", "description": "Optional customer id."},
            },
            "required": ["summary"],
        },
    },
]


# --------------------------------------------------------------------------
# REGISTRY + DISPATCH
# --------------------------------------------------------------------------

TOOL_IMPL = {
    "get_customer": get_customer,
    "lookup_order": lookup_order,
    "get_orders": get_orders,
    "process_refund": process_refund,
    "escalate_to_human": escalate_to_human,
}


def run_tool(name: str, tool_input: dict) -> dict:
    """Run a tool by name. The orchestration loop wraps this with pre and post hooks."""
    if name not in TOOL_IMPL:
        raise KeyError(f"unknown tool: {name}")
    return TOOL_IMPL[name](**tool_input)


if __name__ == "__main__":
    # Quick manual check of a typical chain.
    cust = get_customer("ada@example.com")
    print(cust)
    cid = cust["customer"]["id"]
    print(lookup_order("O-5001", customer_id=cid))
    print(process_refund("O-5001", 79.0, "Arrived with a scratched key"))
    print(escalate_to_human("Customer wants a refund on a non-refundable order", "high", cid))
