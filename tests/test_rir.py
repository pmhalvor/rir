import random
from datetime import datetime, timezone

from rir import mailer, notion, stats


def page(status=None, tags=("ml",)):
    props = {
        "Name": {"type": "title", "title": [{"plain_text": "Hi"}]},
        "Tags": {"type": "multi_select", "multi_select": [{"name": t} for t in tags]},
    }
    if status:
        props["Status"] = {"type": "status", "status": {"name": status}}
    return {"id": "ab-cd", "url": "https://notion.so/x", "properties": props}


def test_parse_page():
    p = page("Read")
    p["created_time"] = "2026-01-02T03:04:05.000Z"
    p["properties"]["Tags"]["multi_select"][0]["color"] = "blue"
    assert notion.parse_page(p) == {
        "id": "ab-cd", "title": "Hi", "tags": ["ml"], "tag_colors": {"ml": "blue"},
        "created": "2026-01-02T03:04:05.000Z", "url": "https://notion.so/x",
        "status": "Read", "commented": False,
    }
    assert notion.parse_page(page(), "https://site/rir/")["url"] == "https://site/rir/abcd"


def test_fetch_articles_checks_blocks_only_for_read(monkeypatch):
    pages = [page("Read"), page("Not started"), page("Read")]
    pages[2]["id"] = "empty"
    calls = []

    def request(_token, url, payload=None, method="POST"):
        if method == "POST":
            return {"results": pages, "has_more": False}
        calls.append(url)
        return {"results": [] if "empty" in url else [{"id": "b"}]}

    monkeypatch.setattr(notion, "_request", request)
    got = notion.fetch_articles("t", "db")
    assert [a["commented"] for a in got] == [True, False, False]
    assert len(calls) == 2


def art(status, tags=("ml",), commented=False, created="2026-01-01T00:00:00Z", colors=None):
    return {"id": status, "title": status, "tags": list(tags), "url": "http://u",
            "status": status, "commented": commented, "created": created,
            "tag_colors": colors or {}}


def test_categorize():
    groups = mailer.categorize([
        art("Not started", tags=()), art("Not started"), art("Currently Reading"),
        art("Read"), art("Read", commented=True), art("Re-read"),
    ])
    assert len(groups["untagged"]) == 1
    assert len(groups["not_read"]) == 1
    assert len(groups["to_reread"]) == 1
    assert [a["status"] for a in groups["to_opinion"]] == ["Read", "Re-read"]


def test_stats():
    now = datetime(2026, 3, 1, tzinfo=timezone.utc)
    arts = [
        art("Read", ("a", "b"), created="2026-02-20T00:00:00Z", colors={"a": "red"}),
        art("Read", ("a", "b"), created="2026-02-10T00:00:00Z"),
        art("Read", ("a", "c"), created="2026-01-10T00:00:00Z"),
        art("Read", ("old",), created="2025-01-01T00:00:00Z"),
    ]
    s = stats.compute_stats(arts, mailer.categorize(arts), now=now)
    assert s["pairs"][0] == ("a", "b", 2)
    assert s["newest"][0] == ("b", "2026-02-10", 2)
    assert [t for t, _, _ in s["least_used"][:2]] == ["old", "c"]  # fewest articles, then oldest
    ts = s["timeseries"]
    assert ts["series"]["a"][-1] == 3 and ts["series"]["a"][0] == 0
    assert list(ts["series"])[0] == "a" and len(ts["dates"]) == len(ts["series"]["a"])
    assert s["colors"]["a"] == "red"
    assert dict(s["per_section"]["to_reread"])["a"] == 3


def test_pick_and_message():
    arts = [art("Not started", colors={"ml": "blue"}) for _ in range(10)]
    chosen = mailer.pick_articles(arts, 4, random.Random(1))
    assert len(chosen) == 4
    assert len(mailer.pick_articles(arts[:2], 4, random.Random())) == 2
    s = stats.compute_stats(arts, mailer.categorize(arts))
    msg = mailer.build_message({"not_read": chosen}, "a@b.c", ["d@e.f"], s)
    assert "Not started" in msg.get_body(("plain",)).get_content()
    assert "== Stats ==" in msg.get_body(("plain",)).get_content()
    html = msg.get_body(("html",)).get_content()
    assert "border-radius:999px" in html and "#D3E5EF" in html
    assert msg.get_body(("html",)) is not None


def test_chart_images_and_activity():
    arts = [art("Read", ("a", "b"), created="2026-02-20T23:30:00Z", commented=True),
            art("Not started", ("a",), created="2026-01-10T00:00:00Z"),
            art("Re-read", ("a", "c", "d"), created="2026-01-11T12:00:00Z")]
    s = stats.compute_stats(arts, mailer.categorize(arts), now=datetime(2026, 3, 1, tzinfo=timezone.utc),
                            tz="Europe/Oslo")
    act = s["activity"]
    assert act["weekday"][5] == 2 and act["hour"][0] == 1  # 23:30Z on Fri is 00:30 Sat in Oslo
    assert list(act["month"]) == ["2026-01", "2026-02"]
    msg = mailer.build_message({"to_opinion": arts}, "a@b.c", ["d@e.f"], s)
    kinds = [p.get_content_type() for p in msg.walk()]
    assert kinds.count("image/png") >= 7
    assert "text/html" in kinds and not any(p.get_filename() for p in msg.walk())
    html = msg.get_body(("html",)).get_content()
    assert "Least used tags" in html and "first seen" in html
    assert "cid:pie-to_opinion" in html and "cid:radar" in html and "cid:weekday" in html

def test_load_dotenv(tmp_path, monkeypatch):
    from rir.env import load_dotenv
    f = tmp_path / ".env"
    f.write_text('# c\nA_KEY="x y"\nexport B_KEY=2\nC_KEY=keep\n')
    monkeypatch.delenv("A_KEY", raising=False)
    monkeypatch.delenv("B_KEY", raising=False)
    monkeypatch.setenv("C_KEY", "real")
    load_dotenv(str(f))
    import os
    assert os.environ["A_KEY"] == "x y" and os.environ["B_KEY"] == "2" and os.environ["C_KEY"] == "real"
    monkeypatch.delenv("A_KEY"); monkeypatch.delenv("B_KEY")





