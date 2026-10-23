import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from html import escape

from rir import charts

SECTIONS = [
    ("untagged", "Untagged", "Fresh, interesting pages that haven't been reviewed or tagged."),
    ("not_read", "Not started", "Saved but not yet digested."),
    ("to_reread", "To be re-read", "Read but little engaged with. Time to revisit?"),
    ("to_opinion", "To be opinionated", "Read and commented on; time to form an opinion!"),
]


def categorize(articles):
    """Split articles into disjoint sections, in priority order."""
    groups = {key: [] for key, _, _ in SECTIONS}
    for a in articles:
        if not a["tags"]:
            groups["untagged"].append(a)
        elif a["status"] == "Not started":
            groups["not_read"].append(a)
        elif a["status"] == "Read" and not a["commented"]:
            groups["to_reread"].append(a)
        elif a["status"] == "Re-read" or (a["status"] == "Read" and a["commented"]):
            groups["to_opinion"].append(a)
    return groups


def pick_articles(articles, count, rng):
    return rng.sample(articles, min(count, len(articles)))


# (background, text) approximating Notion's tag palette.
TAG_COLORS = {
    "default": ("#E3E2E0", "#32302C"),
    "gray": ("#E3E2E0", "#32302C"),
    "brown": ("#EEE0DA", "#442A1E"),
    "orange": ("#FADEC9", "#49290E"),
    "yellow": ("#FDECC8", "#402C1B"),
    "green": ("#DBEDDB", "#1C3829"),
    "blue": ("#D3E5EF", "#183347"),
    "purple": ("#E8DEEE", "#412454"),
    "pink": ("#F5E0E9", "#4C2337"),
    "red": ("#FFE2DD", "#5D1715"),
}


def tag_pill(name, color="default"):
    bg, fg = TAG_COLORS.get(color, TAG_COLORS["default"])
    return (
        f'<span style="display:inline-block;margin:0 4px 2px 0;padding:2px 10px;'
        f'border-radius:999px;background:{bg};color:{fg};font-size:12px;">{escape(name)}</span>'
    )


def capsule(pills, count=None, note=None):
    """Grey wrapper grouping one or more tag pills with their count and an optional note line."""
    label = f' <small style="color:#666;">({escape(str(count))})</small>' if count is not None else ""
    note_html = f'<br><small style="color:#666;">{escape(note)}</small>' if note else ""
    return (
        '<div style="display:inline-block;margin:0 0 6px 0;padding:4px 10px;'
        'border-radius:16px;background:#F1F1EF;line-height:1.5;">'
        f'{pills}{label}{note_html}</div><br>'
    )


WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
TAGGED_SECTIONS = ("not_read", "to_reread", "to_opinion")


PLOT_MAX_WIDTH = 1000

# Pale Bauhaus palette: (background, heading accent).
QUADRANT_COLORS = {
    "untagged": ("#FFF3C4", "#8A6D00"),
    "not_read": ("#DCE8F7", "#1F4E8C"),
    "to_reread": ("#F9DAD7", "#9B2C23"),
    "to_opinion": ("#E6E6E4", "#444444"),
}


# Mid-tone versions of the quadrant colors, keyed by Notion status.
STATUS_COLORS = {
    "Not started": "#6A9BD8",
    "Read": "#E07A70",
    "Re-read": "#8C8C88",
    None: "#E8C547",
}


def _img(images, cid, png, alt, width="100%"):
    images.append((cid, png))
    return (
        f'<div style="text-align:center;"><img src="cid:{cid}" alt="{escape(alt)}" '
        f'style="width:{width};max-width:{PLOT_MAX_WIDTH}px;display:inline-block;"></div>'
    )


def _quadrant(key, heading, blurb, articles, colors):
    bg, accent = QUADRANT_COLORS[key]
    items = []
    for a in articles:
        a_colors = {**colors, **a.get("tag_colors", {})}
        pills = "".join(tag_pill(t, a_colors.get(t, "default")) for t in a["tags"])
        items.append(
            f'<li style="margin-bottom:8px"><a href="{escape(a["url"])}">{escape(a["title"])}</a>'
            f'<br>{pills or "<small>no tags yet</small>"}</li>'
        )
    body = f'<ul style="margin:0;padding-left:20px;">{"".join(items)}</ul>' if items else "<i>Nothing here this week.</i>"
    return (
        f'<td style="vertical-align:top;width:50%;padding:16px;border-radius:20px;background:{bg};">'
        f'<h2 style="margin:0 0 4px 0;color:{accent};">{escape(heading)}</h2>'
        f'<p style="margin:0 0 10px 0;color:#555;"><small>{escape(blurb)}</small></p>{body}</td>'
    )


def _render_stats(stats, images):
    colors = stats["colors"]
    headings = {key: heading for key, heading, _ in SECTIONS}

    def pills(items):
        return "".join(
            capsule(tag_pill(t, colors.get(t, "default")), n) for t, n in items
        ) or "<i>none</i>"

    def pill(tag):
        return tag_pill(tag, colors.get(tag, "default"))

    def plain(items):
        return ", ".join(f"{t} ({n})" for t, n in items) or "none"

    text, html = ["", "== Stats =="], ["<h2>Stats</h2>"]

    text.append("Tags per section:")
    html.append("<h3>Tags per section</h3>")
    cells = []
    for key in TAGGED_SECTIONS:
        items = stats["per_section"].get(key) or []
        counts = stats["section_counts"].get(key) or {}
        if not items:
            continue
        text.append(f"  {headings[key]}: {plain(items)}")
        cell = f"<b>{escape(headings[key])}</b><br>{pills(items)}"
        cell += _img(images, f"pie-{key}", charts.pie(counts, headings[key], charts.SECTION_COLORS.get(key)),
                     f"{headings[key]} tags")
        cells.append(f'<td style="vertical-align:top;width:33%;padding:0 6px;">{cell}</td>')
    if cells:
        html.append(f'<table role="presentation" style="width:100%;border-collapse:collapse;"><tr>{"".join(cells)}</tr></table>')
    radar = charts.radar(
        {k: stats["section_counts"].get(k) or {} for k in TAGGED_SECTIONS}, headings
    )
    if radar:
        html.append(_img(images, "radar", radar, "Top tags by section", "70%"))

    pairs, newest, least = stats["pairs"], stats["newest"], stats["least_used"]
    text.append("Popular pairings: " + (", ".join(f"{a} + {b} ({n})" for a, b, n in pairs) or "none"))
    text.append("Newest tags: " + (", ".join(f"{t} (since {d})" for t, d, _ in newest) or "none"))
    text.append("Least used tags: " + (", ".join(f"{t} ({n})" for t, _, n in least) or "none"))
    columns = [
        ("Popular pairings", "".join(
            capsule(f"{pill(a)} + {pill(b)}", n) for a, b, n in pairs)),
        ("Newest tags", "".join(
            capsule(pill(t), n, f"first seen {d}") for t, d, n in newest)),
        ("Least used tags", "".join(
            capsule(pill(t), n, f"first seen {d}") for t, d, n in least)),
    ]
    cells = "".join(
        f'<td style="vertical-align:top;width:33%;padding:0 6px;"><h3>{title}</h3>{body or "<i>none</i>"}</td>'
        for title, body in columns
    )
    html.append(f'<table role="presentation" style="width:100%;border-collapse:collapse;"><tr>{cells}</tr></table>')

    series = stats.get("timeseries", {}).get("series")
    if series:
        html.append("<h3>Tags over time</h3>")
        html.append(_img(images, "tagchart", charts.tags_over_time(stats["timeseries"]), "Tags over time"))

    activity = stats.get("activity")
    if activity and any(activity["weekday"]):
        html.append("<h3>When articles are added</h3>")
        hours = [f"{h:02d}" for h in range(24)]
        months = activity["month"]
        status = activity["status"]
        status_colors = [STATUS_COLORS.get(s, STATUS_COLORS[None]) for s in status]
        plots = [
            _img(images, "weekday", charts.bars(WEEKDAYS, activity["weekday"], "Articles added by day of week"), "By weekday"),
            _img(images, "hour", charts.bars(hours, activity["hour"], "Articles added by hour of day", "#8E6CC8"), "By hour"),
            _img(images, "months", charts.bars(list(months), list(months.values()), "Articles added per month", "#43A047", rotate=True), "Per month"),
            _img(images, "status", charts.bars(list(status), list(status.values()), "Articles per status", status_colors, horizontal=True), "Status"),
        ]
        cells = [
            f'<td style="width:50%;vertical-align:top;background:#FAFAF8;border-radius:20px;padding:10px;">{p}</td>'
            for p in plots
        ]
        html.append(
            '<table role="presentation" style="width:100%;border-collapse:separate;border-spacing:12px;table-layout:fixed;">'
            f"<tr>{cells[0]}{cells[1]}</tr><tr>{cells[2]}{cells[3]}</tr></table>"
        )
        busiest = WEEKDAYS[max(range(7), key=activity["weekday"].__getitem__)]
        text.append(f"Most articles are added on {busiest}; see the HTML version for charts.")
    return text, html


def build_message(sections, sender, recipients, stats=None):
    """sections maps a SECTIONS key to the list of chosen articles."""
    colors = (stats or {}).get("colors", {})
    images = []
    text = ["Random Internet Readings Briefing &#127760; "]
    html = [f"<h1>&#127760; Random Internet Readings Briefing &#127760;</h1>"]
    html.append(f"<h3>({datetime.now().strftime('%Y-%m-%d')}  Week {datetime.now().isocalendar()[1]})</h3>")
    cells = []
    for key, heading, blurb in SECTIONS:
        articles = sections.get(key) or []
        cells.append(_quadrant(key, heading, blurb, articles, colors))
        if not articles:
            continue
        text += ["", f"== {heading} ==", blurb]
        for a in articles:
            tags = ", ".join(a["tags"]) or "no tags yet"
            text.append(f"- {a['title']} [{tags}]\n  {a['url']}")
    html.append(
        '<table role="presentation" style="width:100%;border-collapse:separate;border-spacing:12px;">'
        f'<tr>{cells[0]}{cells[1]}</tr><tr>{cells[2]}{cells[3]}</tr></table>'
    )
    if stats:
        stats_text, stats_html = _render_stats(stats, images)
        text += stats_text
        html += stats_html
    msg = EmailMessage()
    msg["Subject"] = f"RIR Briefing ({datetime.now().isocalendar()[0]} W{datetime.now().isocalendar()[1]})"
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content("\n".join(text))
    msg.add_alternative("".join(html), subtype="html")
    body = msg.get_body(("html",))
    for cid, png in images:
        body.add_related(png, "image", "png", cid=f"<{cid}>")  # type: ignore
    return msg


def send(msg, host, port, user, password):
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        if user:
            smtp.login(user, password)
        smtp.send_message(msg)

