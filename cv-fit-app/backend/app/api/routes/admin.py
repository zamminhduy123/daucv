"""
Admin-only routes — LLMOps metrics and observability.
"""

import json

from fastapi import APIRouter

from app.core.config import LOGS_DIR

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/metrics")
async def admin_metrics():
    """
    Aggregate LLM request metrics from all daily JSONL log files.

    Returns success rates, per-provider latency, fallback frequency,
    JSON parse failure rates, and total token usage.
    """
    log_files = sorted(LOGS_DIR.glob("*.jsonl"))

    empty_response = {
        "total_requests": 0,
        "success_rate_pct": 0.0,
        "avg_latency_by_provider": {},
        "fallback_count": 0,
        "json_failure_rate_by_provider": {},
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_tokens": 0,
        "requests_by_feature": {},
        "requests_by_provider": {},
    }

    if not log_files:
        return empty_response

    records: list[dict] = []
    for fpath in log_files:
        with open(fpath, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # skip malformed lines

    total = len(records)
    if total == 0:
        return empty_response

    # --- Aggregate stats ------------------------------------------------
    successes = sum(1 for r in records if r.get("success"))
    fallback_count = sum(1 for r in records if r.get("fallback_used"))
    total_input_tokens = sum(r.get("input_tokens", 0) for r in records)
    total_output_tokens = sum(r.get("output_tokens", 0) for r in records)

    # Per-provider latency
    provider_latencies: dict[str, list[int]] = {}
    # Per-provider JSON failure tracking
    provider_json_total: dict[str, int] = {}
    provider_json_failures: dict[str, int] = {}
    # Per-feature request count
    feature_counts: dict[str, int] = {}
    # Per-provider request count
    provider_counts: dict[str, int] = {}

    for r in records:
        prov = r.get("provider", "unknown")
        feat = r.get("feature", "unknown")

        # Latency
        provider_latencies.setdefault(prov, []).append(r.get("latency_ms", 0))

        # JSON validity
        provider_json_total[prov] = provider_json_total.get(prov, 0) + 1
        if not r.get("json_valid", True):
            provider_json_failures[prov] = provider_json_failures.get(prov, 0) + 1

        # Feature counts
        feature_counts[feat] = feature_counts.get(feat, 0) + 1

        # Provider counts
        provider_counts[prov] = provider_counts.get(prov, 0) + 1

    avg_latency_by_provider = {
        prov: round(sum(lats) / len(lats), 1)
        for prov, lats in provider_latencies.items()
    }

    json_failure_rate_by_provider = {
        prov: round(
            (provider_json_failures.get(prov, 0) / provider_json_total[prov]) * 100, 2
        )
        for prov in provider_json_total
    }

    return {
        "total_requests": total,
        "success_rate_pct": round((successes / total) * 100, 2),
        "avg_latency_by_provider": avg_latency_by_provider,
        "fallback_count": fallback_count,
        "json_failure_rate_by_provider": json_failure_rate_by_provider,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
        "requests_by_feature": feature_counts,
        "requests_by_provider": provider_counts,
    }
