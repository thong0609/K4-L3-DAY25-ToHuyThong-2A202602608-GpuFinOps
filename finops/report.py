"""Report assembly — the lab's deliverable: baseline vs optimized + savings chart."""
from __future__ import annotations


def build_report(baseline_usd: float, optimized_usd: float, levers: dict,
                 sustainability: dict | None = None, period: str = "monthly") -> str:
    """Return a markdown cost-optimization report."""
    savings = baseline_usd - optimized_usd
    pct = (savings / baseline_usd * 100.0) if baseline_usd > 0 else 0.0
    lines = [
        "# NimbusAI — GPU Cost Optimization Report",
        "",
        f"**Period:** {period}",
        "",
        f"**Baseline spend:** ${baseline_usd:,.2f}",
        "",
        f"**Optimized spend:** ${optimized_usd:,.2f}",
        "",
        f"**Projected savings:** ${savings:,.2f}  (**{pct:.0f}%**; detailed: {pct:.2f}%)",
        "",
        "## Savings by lever",
        "",
        "| Lever | Savings (USD) |",
        "|---|---|",
    ]
    for name, amount in levers.items():
        lines.append(f"| {name} | ${amount:,.2f} |")
    if sustainability:
        lines += [
            "",
            "## Sustainability",
            "",
            f"- Energy per query: {sustainability.get('wh_per_query', 0):.2f} Wh",
            f"- Carbon per query: {sustainability.get('carbon_g', 0):.3f} gCO2e",
            f"- Cleanest region: {sustainability.get('best_region', 'n/a')}",
            "- Cheapest electricity region in the lab catalog: us-east-wa",
        ]
    lines += ["", "_Figures are June-2026 as-of snapshots; re-baseline before acting._"]
    return "\n".join(lines)


def savings_waterfall(levers: dict, path: str, baseline: float | None = None) -> str:
    """Write a sequential waterfall with baseline and final spend."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return ""
    names = list(levers.keys())
    vals = [levers[n] for n in names]
    fig, ax = plt.subplots(figsize=(12, 6))
    if baseline is None:
        ax.bar(names, vals, color="#2e548a")
    else:
        names = ["Baseline"] + names + ["Optimized"]
        current = baseline
        ax.bar(0, baseline, color="#2e548a")
        ax.text(0, baseline, f"${baseline:,.0f}", ha="center", va="bottom")
        for i, value in enumerate(vals, 1):
            ax.plot([i-1, i], [current, current], color="gray", linestyle="--", linewidth=0.8)
            ax.bar(i, value, bottom=current-value, color="#209580")
            ax.text(i, current, f"-${value:,.0f}", ha="center", va="bottom")
            current -= value
        ax.bar(len(names)-1, current, color="#2e548a")
        ax.text(len(names)-1, current, f"${current:,.0f}", ha="center", va="bottom")
        ax.set_xticks(range(len(names)), names)
        ax.set_ylim(0, baseline * 1.15)
    ax.set_ylabel("USD / month (lab scenario)")
    ax.set_title("NimbusAI: projected savings by four FinOps levers")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path
