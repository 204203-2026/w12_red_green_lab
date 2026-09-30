def test_home_is_green(client):
    assert client.get("/").json()["app"] == "Red Before Green"


def test_seeded_cards_are_green(client):
    assert len(client.get("/cards").json()) == 4
