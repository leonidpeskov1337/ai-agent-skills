"""Summarize finite numeric samples by series; p95 here is over time samples."""
import argparse
import json
import math
import statistics
from common import MAX_BYTES, emit


def summarize(envelope, above=None):
    if above is not None and not math.isfinite(above):
        raise ValueError("finite threshold required")
    data = envelope.get("response", envelope).get("data", {})
    if data.get("resultType") not in ("matrix", "vector"):
        raise ValueError("matrix/vector required")
    summaries = []
    for series in data.get("result", []):
        samples = series.get("values", [series["value"]] if "value" in series else [])
        numeric = [(float(t), float(v)) for t, v in samples
                   if math.isfinite(float(t)) and math.isfinite(float(v))]
        values = [v for _, v in numeric]
        if not values:
            summary = {"metric": series.get("metric", {}), "finite_samples": 0,
                       "dropped_samples": len(samples), "peak": None, "peak_at": None}
            if above is not None:
                summary.update(above=above, samples_above=0, first_above=None, last_above=None)
            summaries.append(summary)
            continue
        numeric.sort()
        ordered = sorted(values)
        span = numeric[-1][0] - numeric[0][0]
        peak_at, peak = max(numeric, key=lambda sample: sample[1])
        summary = {"metric": series.get("metric", {}), "finite_samples": len(values),
                          "dropped_samples": len(samples) - len(values),
                          "start": numeric[0][0], "end": numeric[-1][0],
                          "mean": statistics.fmean(values), "peak": peak, "peak_at": peak_at,
                          "sample_p95": ordered[math.ceil(.95 * len(ordered)) - 1],
                          "change": numeric[-1][1] - numeric[0][1],
                          "change_per_second": (numeric[-1][1] - numeric[0][1]) / span if span else None}
        if above is not None:
            hits = [t for t, value in numeric if value > above]
            summary.update(above=above, samples_above=len(hits),
                           first_above=hits[0] if hits else None,
                           last_above=hits[-1] if hits else None)
        summaries.append(summary)
    return {"series": summaries, "warnings": envelope.get("response", envelope).get("warnings", []),
            "infos": envelope.get("response", envelope).get("infos", []),
            "caution": "Unweighted sample mean/p95; gaps and uneven intervals can bias these. "
            "Not request latency percentiles. Apply rate() to counters before analysis. "
            "Compare baseline separately, retaining matching labels and units. "
            "Timestamps are UTC Unix seconds; peak_at is the earliest tied sampled peak. "
            "Threshold counts and first/last hits describe observed samples only, not duration "
            "or a continuous incident interval."}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", help="JSON response saved from query_metrics.py")
    p.add_argument("--above", type=float, help="Count observed samples strictly above a finite value")
    a = p.parse_args()
    with open(a.input, "rb") as f:
        payload = f.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        p.error("input byte budget exceeded")
    emit(summarize(json.loads(payload), a.above))
