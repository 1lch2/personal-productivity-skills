def calculate_discount(amount: float, tier: str) -> float:
    rates = {"silver": 0.15, "gold": 0.25}
    if tier not in rates:
        raise ValueError(f"unknown tier: {tier}")
    return round(amount * (1 - rates[tier]), 2)
