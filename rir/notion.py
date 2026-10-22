import json
import urllib.request

NOTION_VERSION = "2022-06-28"


def _request(token, url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": "Bearer " + token,
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def parse_page(page, public_base=None):
    props = page.get("properties", {})
    title, tags = "Untitled", []
    for prop in props.values():
        if prop.get("type") == "title":
            title = "".join(t.get("plain_text", "") for t in prop["title"]) or title
        elif prop.get("type") == "multi_select" and not tags:
            tags = [o["name"] for o in prop["multi_select"]]
    if public_base:
        url = public_base.rstrip("/") + "/" + page["id"].replace("-", "")
    else:
        url = page.get("public_url") or page.get("url", "")
    return {"id": page["id"], "title": title, "tags": tags, "url": url}


def fetch_articles(token, database_id, public_base=None):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    articles, cursor = [], None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        data = _request(token, url, payload)
        articles += [parse_page(p, public_base) for p in data["results"]]
        if not data.get("has_more"):
            return articles
        cursor = data["next_cursor"]
