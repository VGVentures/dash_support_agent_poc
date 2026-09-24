"""The support agent.

Holds the Anthropic key, runs the tool-use loop, and applies the hooks.
Knows nothing about HTTP — the API layer calls run_conversation().
"""

import json
import logging
import os

import anthropic
from dotenv import load_dotenv
from pydantic import ValidationError

from .hooks import ToolBlocked, ValidationFailed, post_hook, pre_hook
from .tools import (
    TOOLS,
    run_tool,
    GetCustomerInput,
    LookupOrderInput,
    GetOrdersInput,
    ProcessRefundInput,
    EscalateToHumanInput,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("dash.backend")

# Load ANTHROPIC_API_KEY and CLAUDE_MODEL from a .env file for local dev.
# Existing shell exports take priority and are not overwritten.
load_dotenv()

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
SYSTEM = (
    "You are a support agent for Dash. Be concise and friendly. "
    "Identify the customer first, confirm an order exists before refunding, "
    "and escalate to a human when a request is out of policy. "
    "When a user expresses frustration, demands to speak with someone else, "
    "or clearly wants escalation (regardless of how they phrase it), gather essential info "
    "(customer id and order id if relevant) then call escalate_to_human immediately. "
    "Only help with Dash customer support topics: orders, refunds, and accounts. "
    "If asked about anything else (general knowledge, other companies, coding help, "
    "math, etc.), briefly decline and steer the conversation back to what you can "
    "help with. Never answer the off-topic question itself."
)

# Reads ANTHROPIC_API_KEY from the environment.
client = anthropic.Anthropic()


def _validate_tool_input(tool_name: str, tool_input: dict) -> dict:
    """Validate tool input using Pydantic models."""
    validators = {
        "get_customer": GetCustomerInput,
        "lookup_order": LookupOrderInput,
        "get_orders": GetOrdersInput,
        "process_refund": ProcessRefundInput,
        "escalate_to_human": EscalateToHumanInput,
    }

    if tool_name not in validators:
        raise ValueError(f"unknown tool: {tool_name}")

    try:
        model = validators[tool_name](**tool_input)
        return model.model_dump()
    except ValidationError as e:
        errors = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
        raise ValidationFailed(f"validation failed for {tool_name}", errors)


def run_conversation(user_id: str, messages: list, model: str = MODEL) -> dict:
    ctx = {"user_id": user_id}
    max_iterations = 10
    iteration = 0
    consecutive_non_retryable = 0

    while iteration < max_iterations:
        iteration += 1
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )
        messages.append(
            {
                "role": "assistant",
                "content": [block.model_dump() for block in response.content],
            }
        )

        if response.stop_reason != "tool_use":
            reply = "".join(b.text for b in response.content if b.type == "text")
            return {"reply": reply, "messages": messages}

        tool_results = []

        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                validated_input = _validate_tool_input(block.name, dict(block.input))
                safe_input = pre_hook(block.name, validated_input, ctx)
                raw = run_tool(block.name, safe_input)
                result = post_hook(block.name, safe_input, raw, ctx)
                content = json.dumps(result)
                is_error = False
                consecutive_non_retryable = 0
            except ValidationFailed as validation_err:
                content = json.dumps({
                    "error": "validation_failed",
                    "message": validation_err.message,
                    "details": validation_err.errors,
                    "retryable": False,
                })
                is_error = True
                consecutive_non_retryable += 1
                log.warning("validation failed: %s errors=%s", block.name, validation_err.errors)
            except ToolBlocked as blocked:
                content = json.dumps({
                    "error": "tool_blocked",
                    "message": str(blocked),
                    "retryable": False,
                })
                is_error = True
                consecutive_non_retryable += 1
                log.warning("tool blocked: %s reason=%s", block.name, blocked)
            except Exception as error:  # noqa: BLE001
                log.exception("tool failed: %s", block.name)
                content = json.dumps({
                    "error": "tool_error",
                    "message": str(error),
                    "retryable": True,
                })
                is_error = True
                consecutive_non_retryable = 0

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                    "is_error": is_error,
                }
            )

        messages.append({"role": "user", "content": tool_results})

        if consecutive_non_retryable >= 2:
            reply = (
                "I've encountered issues that cannot be resolved automatically. "
                "Please escalate this to a human agent for further assistance."
            )
            return {"reply": reply, "messages": messages}

    return {
        "reply": "I've reached the maximum number of tool calls. Please escalate this conversation to a human agent.",
        "messages": messages,
    }
