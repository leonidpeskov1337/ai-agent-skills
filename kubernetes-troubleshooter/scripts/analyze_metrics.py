"""Summarize finite numeric samples by series; p95 here is over time samples."""
import argparse
import json
import math
import statistics
from common import MAX_BYTES, emit


def summarize(envelope):
    data = envelope.get("response", envelope).get("data", {})
    if data.get("resultType") not in ("matrix", "vector"):
        raise ValueError("matrix/vector required")
    summaries = []
    for series in data.get("result", []):
        samples = series.get("values", [series["value"]] if "value" in series else [])
        numeric = [(float(t), float(v)) for t, v in samples if math.isfinite(float(v))]
        values = [v for _, v in numeric]
        if not values:
            summaries.append({"metric": series.get("metric", {}), "finite_samples": 0,
                              "dropped_samples": len(samples)})
            continue
        numeric.sort()
        ordered = sorted(values)
        span = numeric[-1][0] - numeric[0][0]
        summaries.append({"metric": series.get("metric", {}), "finite_samples": len(values),
                          "dropped_samples": len(samples) - len(values),
                          "start": numeric[0][0], "end": numeric[-1][0],
                          "mean": statistics.fmean(values), "peak": max(values),
                          "sample_p95": ordered[math.ceil(.95 * len(ordered)) - 1],
                          "change": numeric[-1][1] - numeric[0][1],
                          "change_per_second": (numeric[-1][1] - numeric[0][1]) / span if span else None})
    return {"series": summaries, "warnings": envelope.get("response", envelope).get("warnings", []),
            "caution": "Unweighted sample mean/p95; gaps and uneven intervals can bias these. "
            "Not request latency percentiles. Apply rate() to counters before analysis. "
            "Compare baseline separately, retaining matching labels and units."}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", help="JSON response saved from query_metrics.py")
    a = p.parse_args()
    with open(a.input, "rb") as f:
        payload = f.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        p.error("input byte budget exceeded")
    emit(summarize(json.loads(payload)))
