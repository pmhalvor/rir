import random

from rir import mailer, notion


def test_parse_page():
    page = {"id": "ab-cd", "url": "https://notion.so/x", "properties": {
        "Name": {"type": "title", "title": [{"plain_text": "Hi"}]},
        "Tags": {"type": "multi_select", "multi_select": [{"name": "ml"}]}}}
    assert notion.parse_page(page) == {"id": "ab-cd", "title": "Hi", "tags": ["ml"], "url": "https://notion.so/x"}
    assert notion.parse_page(page, "https://site/rir/")["url"] == "https://site/rir/abcd"


def test_pick_and_message():
    arts = [{"id": str(i), "title": f"T{i}", "tags": [], "url": f"http://u/{i}"} for i in range(10)]
    chosen = mailer.pick_articles(arts, 4, random.Random(1))
    assert len(chosen) == 4
    msg = mailer.build_message(chosen, "a@b.c", ["d@e.f"])
    assert chosen[0]["url"] in msg.get_body(("plain",)).get_content()
    assert len(mailer.pick_articles(arts[:2], 4, random.Random())) == 2
