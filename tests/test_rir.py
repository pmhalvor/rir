import random

from rir import mailer, notion


def page(status=None, tags=("ml",)):
    props = {
        "Name": {"type": "title", "title": [{"plain_text": "Hi"}]},
        "Tags": {"type": "multi_select", "multi_select": [{"name": t} for t in tags]},
    }
    if status:
        props["Status"] = {"type": "status", "status": {"name": status}}
    return {"id": "ab-cd", "url": "https://notion.so/x", "properties": props}


def test_parse_page():
    assert notion.parse_page(page("Read")) == {
        "id": "ab-cd", "title": "Hi", "tags": ["ml"], "url": "https://notion.so/x",
        "status": "Read", "commented": False,
    }
    assert notion.parse_page(page(), "https://site/rir/")["url"] == "https://site/rir/abcd"


def test_fetch_articles_checks_blocks_only_for_read(monkeypatch):
    pages = [page("Read"), page("Not Read"), page("Read")]
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


def art(status, tags=("ml",), commented=False):
    return {"id": status, "title": status, "tags": list(tags), "url": "http://u",
            "status": status, "commented": commented}


def test_categorize():
    groups = mailer.categorize([
        art("Not Read", tags=()), art("Not Read"), art("Currently Reading"),
        art("Read"), art("Read", commented=True), art("Reread"),
    ])
    assert [a["status"] for a in groups["untagged"]] == ["Not Read"]
    assert [a["status"] for a in groups["not_read"]] == ["Not Read"]
    assert [a["status"] for a in groups["to_reread"]] == ["Read", "Reread"]
    assert groups["to_reread"][0]["commented"]


def test_pick_and_message():
    arts = [art("Not Read") for _ in range(10)]
    chosen = mailer.pick_articles(arts, 4, random.Random(1))
    assert len(chosen) == 4
    assert len(mailer.pick_articles(arts[:2], 4, random.Random())) == 2
    msg = mailer.build_message({"not_read": chosen}, "a@b.c", ["d@e.f"])
    body = msg.get_body(("plain",)).get_content()
    assert "Not Read" in body and "Untagged" not in body


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
