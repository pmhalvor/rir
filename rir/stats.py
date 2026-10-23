from collections import Counter
from datetime import datetime, timedelta, timezone
from itertools import combinations
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _parse(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def compute_timeseries(articles, now=None):
    """Weekly cumulative article count per tag, using article creation dates."""
    now = now or datetime.now(timezone.utc)
    dated = [(c, a["tags"]) for a in articles if (c := _parse(a.get("created"))) and a["tags"]]
    if not dated:
        return {"dates": [], "series": {}}

    start = min(c for c, _ in dated).date()
    start -= timedelta(days=start.weekday())
    weeks = (now.date() - start).days // 7 + 1
    dates = [start + timedelta(weeks=i) for i in range(weeks)]

    added = {}
    for created, tags in dated:
        index = min((created.date() - start).days // 7, weeks - 1)
        for tag in set(tags):
            added.setdefault(tag, [0] * weeks)[index] += 1

    series = {}
    for tag, counts in added.items():
        total, cumulative = 0, []
        for n in counts:
            total += n
            cumulative.append(total)
        series[tag] = cumulative
    # Most used tags first, so charts and legends lead with the important ones.
    series = dict(sorted(series.items(), key=lambda kv: (-kv[1][-1], kv[0])))
    return {"dates": dates, "series": series}


def _activity(articles, tz):
    """Distribution of article creation times: weekday, hour of day, and month."""
    weekday, hour, month, status = [0] * 7, [0] * 24, Counter(), Counter()
    for a in articles:
        status[a.get("status") or "No status"] += 1
        created = _parse(a.get("created"))
        if not created:
            continue
        local = created.astimezone(tz)
        weekday[local.weekday()] += 1
        hour[local.hour] += 1
        month[local.strftime("%Y-%m")] += 1
    if month:
        first = min(month)
        y, m = map(int, first.split("-"))
        last = max(month)
        keys = []
        while f"{y:04d}-{m:02d}" <= last:
            keys.append(f"{y:04d}-{m:02d}")
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        month = {k: month.get(k, 0) for k in keys}
    return {"weekday": weekday, "hour": hour, "month": dict(month), "status": dict(status)}


def _timezone(name):
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.utc


def compute_stats(articles, groups, now=None, top=5, tz="UTC"):
    section_counts = {
        key: Counter(t for a in group for t in a["tags"]) for key, group in groups.items()
    }
    per_section = {key: c.most_common(top) for key, c in section_counts.items()}

    pairs, tag_counts = Counter(), Counter()
    first_seen = {}
    for a in articles:
        pairs.update(combinations(sorted(set(a["tags"])), 2))
        tag_counts.update(set(a["tags"]))
        created = _parse(a.get("created"))
        if not created:
            continue
        for tag in set(a["tags"]):
            if tag not in first_seen or created < first_seen[tag]:
                first_seen[tag] = created

    # A tag's first appearance is proxied by the oldest article carrying it.
    newest = sorted(first_seen.items(), key=lambda kv: kv[1], reverse=True)[:top]
    # Fewest articles first; among equals, the tag that has been around longest.
    least_used = sorted(first_seen.items(), key=lambda kv: (tag_counts[kv[0]], kv[1], kv[0]))[:top]

    return {
        "colors": {t: c for a in articles for t, c in a.get("tag_colors", {}).items()},
        "per_section": per_section,
        "section_counts": {k: dict(c) for k, c in section_counts.items()},
        "pairs": [(a, b, n) for (a, b), n in pairs.most_common(top + top//2)],
        "newest": [(t, d.date().isoformat(), tag_counts[t]) for t, d in newest],
        "least_used": [(t, d.date().isoformat(), tag_counts[t]) for t, d in least_used],
        "timeseries": compute_timeseries(articles, now),
        "activity": _activity(articles, _timezone(tz)),
    }
