import os
import random
import sys
import time

from rir import mailer, notion, stats
from rir.env import load_dotenv


def main():
    start_time = time.time()
    print(f"RIR briefing process started at {time.ctime(start_time)}")

    load_dotenv(os.environ.get("RIR_ENV_FILE", ".env"))
    env = os.environ

    articles = notion.fetch_articles(
        env["NOTION_TOKEN"],
        env["NOTION_DATABASE_ID"],
        env.get("NOTION_PUBLIC_BASE_URL"),
        int(env.get("RIR_MIN_BLOCKS", "1")),
    )

    if not articles:
        print("No articles found; nothing to send.")
        return 0

    count = int(env.get("RIR_ARTICLE_COUNT", "4"))
    rng = random.Random()
    groups = mailer.categorize(articles)
    sections = {key: mailer.pick_articles(group, count, rng) for key, group in groups.items()}
    total = sum(len(group) for group in sections.values())
    if not total:
        print("No articles in any section; nothing to send.")
        return 0

    recipients = [r.strip() for r in env["RIR_RECIPIENTS"].split(",") if r.strip()]
    msg = mailer.build_message(
        sections,
        env.get("SMTP_FROM", env.get("SMTP_USER", "")),
        recipients,
        stats.compute_stats(articles, groups, tz=env.get("RIR_TIMEZONE", "Europe/Oslo")),
    )

    if env.get("RIR_DRY_RUN"):
        print(msg)
        return 0

    mailer.send(
        msg,
        env["SMTP_HOST"],
        int(env.get("SMTP_PORT", "587")),
        env.get("SMTP_USER"),
        env.get("SMTP_PASSWORD"),
    )

    end_time = time.time()

    print(f"Sent {total} articles to {len(recipients)} recipient(s).")
    print(f"RIR briefing process ended at {time.ctime(end_time)}")
    print(f"Elapsed time: {end_time - start_time}") 
    return 0


if __name__ == "__main__":
    sys.exit(main())
