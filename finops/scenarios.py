"""Measured-input scenarios for reasoning budgets and carbon-aware scheduling.

Energy values are estimates under the lab's constants, not power measurements.
"""
from __future__ import annotations

import math
from finops import pricing, sustainability


def reasoning_budget(rows, model_prices, cap_fraction=0.10):
    """Keep the longest reasoning requests, downgrade excess to ordinary output.

    The generator multiplies reasoning output by six. The counterfactual undoes
    that multiplier, retains input/model/cache/batch, and removes the 80x energy
    multiplier. Length is a deterministic proxy, not a measured quality score.
    """
    if not 0 <= cap_fraction <= 1:
        raise ValueError("cap_fraction must be between 0 and 1")
    rows = list(rows)
    reasoning = [i for i, r in enumerate(rows) if int(r["is_reasoning"])]
    keep = set(sorted(reasoning, key=lambda i: (-int(rows[i]["output_tokens"]), i))[
        :math.floor(len(rows) * cap_fraction)])
    groups = {name: {"requests": 0, "tokens": 0, "cost_usd": 0.0, "energy_wh": 0.0}
              for name in ("reasoning", "ordinary")}
    after_cost = after_wh = 0.0
    for i, r in enumerate(rows):
        is_reasoning = bool(int(r["is_reasoning"]))
        inp, out = int(r["input_tokens"]), int(r["output_tokens"])
        pin, pout = model_prices[r["route_tier"]]
        kwargs = {"cached_in": int(r["cached_input_tokens"]), "batch": bool(int(r["is_batch"]))}
        group = groups["reasoning" if is_reasoning else "ordinary"]
        group["requests"] += 1
        group["tokens"] += inp + out
        group["cost_usd"] += pricing.request_cost(inp, out, pin, pout, **kwargs)
        group["energy_wh"] += sustainability.wh_per_query(inp + out, is_reasoning=is_reasoning)
        downgrade = is_reasoning and i not in keep
        new_out = max(1, out // 6) if downgrade else out
        after_cost += pricing.request_cost(inp, new_out, pin, pout, **kwargs)
        after_wh += sustainability.wh_per_query(inp + new_out, is_reasoning=is_reasoning and not downgrade)
    cost = sum(g["cost_usd"] for g in groups.values())
    wh = sum(g["energy_wh"] for g in groups.values())
    return {"groups": groups, "cap_fraction": cap_fraction,
            "downgraded_requests": len(reasoning) - len(keep),
            "reasoning_after": len(keep), "cost_before_usd": cost, "cost_after_usd": after_cost,
            "energy_before_wh": wh, "energy_after_wh": after_wh,
            "savings_usd": round(cost - after_cost, 12) + 0.0,
            "savings_wh": round(wh - after_wh, 8) + 0.0}


def carbon_schedule(jobs, catalog, baseline_region="us-east-1"):
    """Compare all lab regions using actual job days and catalog power.

    Assumes identical hardware/runtime, PUE=1, no transfer costs or spot rework.
    Electricity is a component estimate, not an additional cloud invoice item.
    Balanced score gives equal weight to cost and carbon normalized to baseline.
    """
    cleanest = min(sustainability.REGION_CARBON, key=sustainability.REGION_CARBON.get)
    cheapest = min(sustainability.REGION_PRICE_KWH, key=sustainability.REGION_PRICE_KWH.get)
    records = []
    for j in jobs:
        if not int(j["interruptible"]):
            continue
        hours = float(j["hours_per_day"]) * float(j["days"]) * int(j["num_gpus"])
        wh = hours * float(catalog[j["gpu_type"]]["watts"])
        before = sustainability.carbon_g(wh, baseline_region)
        after = sustainability.carbon_g(wh, cleanest)
        records.append({"job_id": j["job_id"], "gpu_hours": hours, "energy_wh": wh,
                        "carbon_before_g": before, "carbon_after_g": after,
                        "carbon_saved_g": before - after})
    total_wh = sum(r["energy_wh"] for r in records)
    regions = []
    for region, intensity in sustainability.REGION_CARBON.items():
        price = sustainability.REGION_PRICE_KWH[region]
        score = 0.5 * (price / sustainability.REGION_PRICE_KWH[baseline_region]
                       + intensity / sustainability.REGION_CARBON[baseline_region])
        regions.append({"region": region, "usd_kwh": price, "g_kwh": intensity,
                        "electricity_usd": sustainability.energy_cost_usd(total_wh, region),
                        "carbon_g": sustainability.carbon_g(total_wh, region), "balanced_score": score})
    return {"jobs": records, "regions": regions, "energy_wh": total_wh,
            "baseline_region": baseline_region, "cheapest": cheapest, "cleanest": cleanest,
            "balanced": min(regions, key=lambda r: r["balanced_score"])["region"],
            "carbon_saved_g": sum(r["carbon_saved_g"] for r in records)}
