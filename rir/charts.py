import io
import math

import matplotlib.pyplot as plt  # noqa: E402

plt.switch_backend("Agg")

SECTION_COLORS = {
    "not_read": "#4C8BF5",
    "to_reread": "#F5A623",
    "to_opinion": "#43A047",
}


def _png(fig):
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def tags_over_time(timeseries, top=10):
    """Cumulative articles for the most used tags."""
    dates, series = timeseries["dates"], timeseries["series"]
    fig, ax = plt.subplots(figsize=(7, 3.5), dpi=110)
    for tag, counts in list(series.items())[:top]:
        ax.plot(dates, counts, label=tag, linewidth=1.8)
    ax.set_title(f"Top {min(top, len(series))} tags over time (cumulative articles)", fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, loc="upper left", ncol=2, frameon=False)
    fig.autofmt_xdate()
    return _png(fig)


def pie(counts, title, color=None, top=10):
    """counts: {tag: n}. Smaller tags are folded into 'other'."""
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    shown, rest = ranked[:top], sum(n for _, n in ranked[top:])
    if rest:
        # shown.append(("other", rest))
        pass # currently skip "other"
    fig, ax = plt.subplots(figsize=(3, 3), dpi=110)
    palette = plt.get_cmap("tab10").colors  # type: ignore
    wedge_colors = ["#D9D9D9" if t == "other" else palette[i % 10] for i, (t, _) in enumerate(shown)]
    ax.pie(
        [n for _, n in shown], labels=[t for t, _ in shown], startangle=90, colors=wedge_colors,
        counterclock=False, textprops={"fontsize": 7}, wedgeprops={"linewidth": 1, "edgecolor": "white"},
    )
    ax.set_title(title, fontsize=9, color=color or "black")
    return _png(fig)


def radar(counts_by_section, headings, top=10):
    """One filled layer per section; the overall most used tags are the spokes."""
    totals = {}
    for counts in counts_by_section.values():
        for tag, n in counts.items():
            totals[tag] = totals.get(tag, 0) + n
    tags = [t for t, _ in sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))[:top]]
    if len(tags) < 3:
        return None
    angles = [2 * math.pi * i / len(tags) for i in range(len(tags))]
    fig, ax = plt.subplots(figsize=(5, 4.5), dpi=110, subplot_kw={"polar": True})
    for key, counts in counts_by_section.items():
        values = [counts.get(t, 0) for t in tags]
        color = SECTION_COLORS.get(key)
        ax.plot(angles + angles[:1], values + values[:1], color=color, linewidth=1.8,
                label=headings.get(key, key))
        ax.fill(angles + angles[:1], values + values[:1], color=color, alpha=0.15)
    ax.set_xticks(angles)
    ax.set_xticklabels(tags, fontsize=8)
    ax.tick_params(axis="y", labelsize=6)
    ax.set_title("Top tags by section", fontsize=10, pad=14)
    ax.legend(fontsize=7, loc="upper right", bbox_to_anchor=(1.25, 1.1), frameon=False)
    return _png(fig)


def bars(labels, values, title, color: str|list[str]="#4C8BF5", rotate=False, horizontal=False):
    fig, ax = plt.subplots(figsize=(7, 2.8), dpi=110)
    if horizontal:
        ax.barh(labels, values, color=color)
        ax.invert_yaxis()
    else:
        ax.bar(labels, values, color=color)
        if rotate:
            fig.autofmt_xdate()
    ax.set_title(title, fontsize=10)
    ax.grid(alpha=0.3, axis="x" if horizontal else "y")
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=8)
    return _png(fig)
