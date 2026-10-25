import json
import urllib.request
from urllib.parse import urlencode

NOTION_VERSION = "2022-06-28"


def _request(token, url, payload=None, method="POST"):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={
            "Authorization": "Bearer " + token,
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def has_content(token, page_id, min_blocks=1):
    query = urlencode({"page_size": min_blocks})
    url = f"https://api.notion.com/v1/blocks/{page_id}/children?{query}"
    data = _request(token, url, method="GET")
    return len(data["results"]) >= min_blocks


def parse_page(page, public_base=None):
    props = page.get("properties", {})

    title, tags, tag_colors, status, source_url = "Untitled", [], {}, "", ""

    for name, prop in props.items():
        kind = prop.get("type")
        if name.lower() == "url" and kind == "url":
            source_url = prop.get("url") or ""
        elif kind == "title":
            title = "".join(t.get("plain_text", "") for t in prop["title"]) or title
        elif name == "Status" and kind in ("status", "select"):
            status = (prop.get(kind) or {}).get("name", "")
        elif kind == "multi_select" and not tags:
            tags = [o["name"] for o in prop["multi_select"]]
            tag_colors = {o["name"]: o.get("color", "default") for o in prop["multi_select"]}

    if public_base:
        url = public_base.rstrip("/") + "/" + page["id"].replace("-", "")
    else:
        url = page.get("public_url") or page.get("url", "")
    return {
        "id": page["id"],
        "title": title,
        "tags": tags,
        "tag_colors": tag_colors,
        "created": page.get("created_time", ""),
        "url": url,
        "source_url": source_url,
        "edit_url": page.get("url", ""),
        "status": status,
        "commented": False,
    }


def fetch_articles(token, database_id, public_base=None, min_blocks=1):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    articles, cursor = [], None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        data = _request(token, url, payload)

        for p in data["results"]:
            article = parse_page(p, public_base)
            # Only "Read" pages need a block check to tell if they were commented on.
            if article["status"] == "Read":
                article["commented"] = has_content(token, p["id"], min_blocks)
            articles.append(article)
        
        print(f"Fetched {len(articles)} articles so far...")

        if not data.get("has_more"):
            return articles
        
        cursor = data["next_cursor"]

