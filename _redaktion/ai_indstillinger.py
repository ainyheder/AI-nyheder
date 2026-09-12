"""Fælles DeepSeek-politik for alle tekst- og værktøjskald."""
DEEPSEEK_REASONING = "max"
DEEPSEEK_TIMEOUT = 600


def deepseek_parametre(max_tokens):
    # Budgettet omfatter både tænkning og det synlige svar. De gamle
    # 400-4000 tokens gav ikke plads til begge dele ved maksimal tænkning.
    return {"thinking": {"type": "enabled"},
            "reasoning_effort": DEEPSEEK_REASONING,
            "max_tokens": max(32768, max_tokens)}
