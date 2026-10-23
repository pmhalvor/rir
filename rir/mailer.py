import smtplib
import ssl
from email.message import EmailMessage
from html import escape

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


def build_message(sections, sender, recipients):
    """sections maps a SECTIONS key to the list of chosen articles."""
    text = ["Your weekly Random Internet Readings:"]
    html = ["<h1>Your weekly Random Internet Readings</h1>"]
    for key, heading, blurb in SECTIONS:
        articles = sections.get(key) or []
        if not articles:
            continue
        text += ["", f"== {heading} ==", blurb]
        html.append(f"<h2>{escape(heading)}</h2><p>{escape(blurb)}</p><ul>")
        for a in articles:
            tags = ", ".join(a["tags"]) or "no tags yet"
            text.append(f"- {a['title']} [{tags}]\n  {a['url']}")
            html.append(
                f"<li><a href=\"{escape(a['url'])}\">{escape(a['title'])}</a>"
                f" <small>({escape(tags)})</small></li>"
            )
        html.append("</ul>")
    msg = EmailMessage()
    msg["Subject"] = "Your weekly RIR digest"
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content("\n".join(text))
    msg.add_alternative("".join(html), subtype="html")
    return msg


def send(msg, host, port, user, password):
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        if user:
            smtp.login(user, password)
        smtp.send_message(msg)
