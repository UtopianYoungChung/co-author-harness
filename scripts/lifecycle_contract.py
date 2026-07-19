#!/usr/bin/env python3
"""Load and query the canonical lifecycle transition contract."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "references" / "lifecycle_transitions.v1.json"


@lru_cache(maxsize=1)
def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    errors = contract_coherence_errors(contract)
    if errors:
        raise ValueError("invalid lifecycle contract: " + "; ".join(errors))
    return contract


def contract_coherence_errors(contract: dict[str, Any]) -> list[str]:
    """Return structural errors, including downgrade/exemption drift."""
    errors: list[str] = []
    state_rows = contract.get("states", [])
    state_ids = [row.get("id") for row in state_rows if isinstance(row, dict)]
    if len(state_ids) != len(set(state_ids)):
        errors.append("duplicate lifecycle state id")
    order = {state: index for index, state in enumerate(state_ids)}
    transitions = contract.get("transitions", [])
    transition_ids: set[str] = set()
    downward_triggers: set[str] = set()
    for rule in transitions:
        if not isinstance(rule, dict):
            errors.append("transition row is not an object")
            continue
        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or not rule_id:
            errors.append("transition id is required")
        elif rule_id in transition_ids:
            errors.append(f"duplicate transition id: {rule_id}")
        else:
            transition_ids.add(rule_id)
        trigger = rule.get("trigger")
        for previous in rule.get("from", []):
            if previous is not None and previous not in order:
                errors.append(f"{rule_id}: unknown source state {previous!r}")
            targets: list[object] = []
            if "to_by_from" in rule:
                mapping = rule["to_by_from"]
                if not isinstance(mapping, dict) or previous not in mapping:
                    errors.append(f"{rule_id}: missing to_by_from target for {previous!r}")
                    continue
                targets = [mapping[previous]]
            else:
                targets = rule.get("to", [])
            for target in targets:
                if target == "$same":
                    target = previous
                if target == "$lower":
                    downward_triggers.add(trigger)
                    continue
                if target is not None and target not in order:
                    errors.append(f"{rule_id}: unknown target state {target!r}")
                    continue
                if previous in order and target in order and order[target] < order[previous]:
                    downward_triggers.add(trigger)
    declared = set(contract.get("monotonicity_exemptions", []))
    if downward_triggers != declared:
        errors.append(
            "monotonicity exemptions disagree with downward transition triggers: "
            f"declared={sorted(declared)} actual={sorted(downward_triggers)}"
        )
    return errors


def states() -> list[str]:
    return [row["id"] for row in load_contract()["states"]]


def monotonicity_exemptions() -> set[str]:
    return set(load_contract()["monotonicity_exemptions"])


def known_triggers() -> set[str]:
    return {row["trigger"] for row in load_contract()["transitions"]}


def transition_allowed(trigger: object, previous: object, new: object) -> bool:
    if not isinstance(trigger, str):
        return False
    contract = load_contract()
    for rule in contract["transitions"]:
        if rule["trigger"] != trigger or previous not in rule["from"]:
            continue
        if "to_by_from" in rule:
            if rule["to_by_from"].get(previous) == new:
                return True
            continue
        targets = rule.get("to", [])
        if "$same" in targets and previous == new:
            return True
        if "$lower" in targets:
            order = states()
            if previous in order and new in order and order.index(new) < order.index(previous):
                return True
            continue
        if new in targets:
            return True
    return False
