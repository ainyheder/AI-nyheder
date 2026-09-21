"""Fælles DeepSeek-politik for alle tekst- og værktøjskald."""
DEEPSEEK_REASONING = "high"
DEEPSEEK_TIMEOUT = 600


def deepseek_parametre(max_tokens, thinking=None):
    # Budgettet omfatter både tænkning og det synlige svar. De gamle
    # 400-4000 tokens gav ikke plads til begge dele til både tænkning og svar.
    if thinking == "disabled":
        return {"thinking": {"type": "disabled"}, "max_tokens": max(32768, max_tokens)}
    if thinking not in (None, "low", "high", "max"):
        raise ValueError("Ugyldigt DeepSeek-niveau")
    return {"thinking": {"type": "enabled"},
            "reasoning_effort": thinking or DEEPSEEK_REASONING,
            "max_tokens": max(32768, max_tokens)}


# Samme dokumenterede regler sendes til modelmenuen i kommandocentralen.
import json
import re
from pathlib import Path
REASONING_CATALOG = json.loads(Path(__file__).with_name("reasoning.json").read_text())


def reasoning_rule(model):
    return next((r for r in REASONING_CATALOG["rules"] if re.fullmatch(r["pattern"], model or "")), {})


def validate_thinking(model, thinking):
    if thinking in (None, ""):
        return None
    rule = reasoning_rule(model)
    if isinstance(thinking, str) and thinking.startswith("budget:") and rule.get("kind") == "budget":
        value = thinking.removeprefix("budget:")
        if value.isdigit() and rule["minimum"] <= int(value) <= rule["maximum"]:
            return thinking
    elif thinking in rule.get("levels", []) and thinking != "budget":
        return thinking
    raise ValueError("Ræsonnementet understøttes ikke af " + model)


def gemini_thinking(model, thinking):
    thinking = validate_thinking(model, thinking)
    if not thinking:
        return {}
    if reasoning_rule(model).get("kind") == "budget":
        value = -1 if thinking == "dynamic" else 0 if thinking == "disabled" else int(thinking.split(":")[1])
        return {"thinkingConfig": {"thinkingBudget": value}}
    return {"thinkingConfig": {"thinkingLevel": thinking}}
