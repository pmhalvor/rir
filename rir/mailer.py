import smtplib
import ssl
from email.message import EmailMessage
from html import escape


def pick_articles(articles, count, rng):
    return rng.sample(articles, min(count, len(articles)))


def build_message(articles, sender, recipients):
    text = ["Your weekly Random Internet Readings:", ""]
    html = ["<h2>Your weekly Random Internet Readings</h2><ul>"]
    for a in articles:
        tags = ", ".join(a["tags"]) or "no tags yet"
        text.append(f"- {a['title']} [{tags}]\n  {a['url']}")
        html.append(
            f"<li><a href=\"{escape(a['url'])}\">{escape(a['title'])}</a>"
            f" <small>({escape(tags)})</small></li>"
        )
    footer = (
        "Re-read the article, add your commentary, "
        "or check that the right tags are assigned."
    )
    text += ["", footer]
    html.append(f"</ul><p>{footer}</p>")
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
