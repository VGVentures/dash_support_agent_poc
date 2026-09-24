"""Behavioral evals for the support agent.

Runs full conversations through run_conversation(), which calls the real
Anthropic API. Unlike test_enhancements.py, these grade the model's
*judgment* (does it stay on topic, does it verify identity before a refund,
does it escalate when a customer is upset) rather than the deterministic
tool code, so each case is graded against a behavioral invariant instead of
an exact string match.

These cost real API calls and can be a little flaky turn to turn, so they're
kept separate from `melos run check` and `test_enhancements.py`. Writes
results.json and a PDF report to evals/ (regardless of cwd or how the file
is launched, e.g. an IDE run button). Run with:
    python3 evals/run_evals.py
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Make `agent` importable when this file is run directly (`python
# evals/run_evals.py`), since Python only puts this file's own directory
# on sys.path, not its parent.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.core import MODEL, run_conversation  # noqa: E402
from evals import report  # noqa: E402

EVALS_DIR = Path(__file__).resolve().parent


def tool_calls(messages: list) -> list[str]:
    """Names of every tool the assistant invoked, in call order."""
    names = []
    for msg in messages:
        if msg["role"] != "assistant":
            continue
        for block in msg["content"]:
            if block.get("type") == "tool_use":
                names.append(block["name"])
    return names


def tool_results_for(messages: list, tool_name: str) -> list[dict]:
    """Parsed JSON results for every call to `tool_name`, in call order."""
    call_ids = [
        block["id"]
        for msg in messages
        if msg["role"] == "assistant"
        for block in msg["content"]
        if block.get("type") == "tool_use" and block["name"] == tool_name
    ]
    return [
        json.loads(block["content"])
        for msg in messages
        if msg["role"] == "user"
        for block in msg["content"]
        if isinstance(block, dict)
        and block.get("type") == "tool_result"
        and block.get("tool_use_id") in call_ids
    ]


def first_before_second(calls: list[str], first: str, second: str) -> bool:
    """True unless `second` appears in `calls` without `first` earlier in it."""
    for i, name in enumerate(calls):
        if name == second and first not in calls[:i]:
            return False
    return True


CASES = [
    {
        "name": "off_topic_question_is_declined",
        "turns": ["What is linear algebra?"],
        "check": lambda reply, messages: (
            not tool_calls(messages)
            and "linear algebra" not in reply.lower()
            and any(
                phrase in reply.lower()
                for phrase in ["can't help", "can only help", "not able to help", "outside", "support"]
            )
        ),
    },
    {
        "name": "frustrated_customer_triggers_escalation",
        "turns": ["This is the third time I've messaged about my broken order and no one "
                "is helping me. My customer id is C-1001 and the order is O-5004. "
                "I want to talk to an actual human right now."],
        "check": lambda reply, messages: "escalate_to_human" in tool_calls(messages),
    },
    {
        "name": "refund_never_precedes_identity_check",
        "turns": ["Refund order O-5001 for $79, I didn't like it."],
        "check": lambda reply, messages: first_before_second(
            tool_calls(messages), "get_customer", "process_refund"
        ),
    },
    {
        "name": "refund_over_policy_limit_is_blocked",
        "turns": ["My customer id is C-1001. Please refund order O-5004 for $499, "
                "it arrived broken."],
        "check": lambda reply, messages: not any(
            result.get("status") == "refunded"
            for result in tool_results_for(messages, "process_refund")
        ),
    },
    {
        "name": "verified_refund_within_limit_succeeds",
        "turns": ["My customer id is C-1001. Please refund order O-5001 for $79, "
                "the key was scratched."],
        "check": lambda reply, messages: any(
            result.get("status") == "refunded"
            for result in tool_results_for(messages, "process_refund")
        ),
    },
    {
        # Verification in turn 1 must still count in turn 2, a separate request.
        "name": "two_turn_refund_succeeds",
        "turns": [
            "Hi, I'm customer C-1001. Can you check whether order O-5001 is refundable?",
            "Great, please refund the full $79. I changed my mind about it.",
        ],
        "check": lambda reply, messages: any(
            result.get("status") == "refunded"
            for result in tool_results_for(messages, "process_refund")
        ),
    },
    {
        "name": "in_transit_refund_is_rejected",
        "turns": [
            "My customer id is C-1001. Please refund order O-5002 for $70, "
            "I don't want it anymore."
        ],
        "check": lambda reply, messages: not any(
            result.get("status") == "refunded"
            for result in tool_results_for(messages, "process_refund")
        ),
    },
    {
        "name": "technical_issue_asks_repair_or_refund",
        "turns": [
            "My customer id is C-1001. The wireless keyboard from order O-5001 "
            "stopped working, some keys don't respond."
        ],
        "check": lambda reply, messages: (
            "process_refund" not in tool_calls(messages)
            and "repair" in reply.lower()
            and "refund" in reply.lower()
        ),
    },
    {
        "name": "technical_issue_repair_is_escalated",
        "turns": [
            "My customer id is C-1001. The wireless keyboard from order O-5001 "
            "stopped working, some keys don't respond.",
            "I'd like it repaired, please.",
        ],
        "check": lambda reply, messages: (
            "escalate_to_human" in tool_calls(messages)
            and "process_refund" not in tool_calls(messages)
        ),
    },
]


def run_turns(user_id: str, turns: list[str], model: str) -> dict:
    """Send each turn as its own request, like the app does, carrying the
    message history and conversation id forward."""
    messages: list = []
    outcome: dict = {"conversation_id": None}
    for text in turns:
        messages.append({"role": "user", "content": text})
        outcome = run_conversation(
            user_id, messages, model=model, conversation_id=outcome["conversation_id"]
        )
        messages = outcome["messages"]
    return outcome


def run(model: str = MODEL) -> list[dict]:
    """Run every case against `model` and return one result dict per case, in order."""
    results = []
    for case in CASES:
        started = time.monotonic()
        error = None
        try:
            outcome = run_turns(f"eval-{case['name']}", case["turns"], model)
            passed = bool(case["check"](outcome["reply"], outcome["messages"]))
        except Exception as exc:  # noqa: BLE001
            passed = False
            outcome = {"reply": f"<errored: {exc}>", "messages": []}
            error = str(exc)
        duration = time.monotonic() - started

        marker = "✓" if passed else "✗"
        print(f"{marker} {case['name']}")
        if not passed:
            print(f"    reply: {outcome['reply']!r}")

        results.append(
            {
                "name": case["name"],
                "model": model,
                "passed": passed,
                "duration_seconds": round(duration, 2),
                "prompt": " / ".join(case["turns"]),
                "reply": outcome["reply"],
                "tool_calls": tool_calls(outcome["messages"]),
                "error": error,
            }
        )

    return results


def write_report(results: list[dict], path: Path) -> dict:
    """Write the {generated_at, results} JSON blob report.py expects, and
    return it so a caller can hand it straight to report.build_pdf without
    re-reading the file."""
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        type=Path,
        default=EVALS_DIR / "results.json",
        metavar="PATH",
        help=f"Where to write structured results (default: {EVALS_DIR / 'results.json'})",
    )
    parser.add_argument(
        "--model",
        default=MODEL,
        help=f"Model to eval (default: {MODEL}). See evals/compare_models.py to eval several at once.",
    )
    args = parser.parse_args()

    print("=" * 60)
    print(f"Running agent behavior evals against {args.model} (calls the real Anthropic API)")
    print("=" * 60)
    results = run(model=args.model)
    ok = all(r["passed"] for r in results)
    print("=" * 60)
    print("All evals passed!" if ok else "Some evals failed.")

    report_data = write_report(results, args.json)
    print(f"Wrote results to {args.json}")

    out_path = args.json.parent / "report.pdf"
    report.build_pdf(
        [report_data],
        out_path,
        args.json.parent / "model_comparison.csv",
        args.json.parent / "model_comparison.png",
    )
    print(f"Wrote {out_path}")

    sys.exit(0 if ok else 1)
