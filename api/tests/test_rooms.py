"""Tests for Phase 7: rooms (REST + WebSocket realtime), notes, playground."""

from __future__ import annotations

import starlette.websockets
import pytest
from fastapi.testclient import TestClient

from tests.conftest import signup


def _user(
    client: TestClient, email: str = "user@example.com", name: str = "User"
) -> dict:
    """Sign up a user and return headers + token + id."""
    body = signup(client, email=email, name=name)
    return {
        "headers": {"Authorization": f"Bearer {body['token']}"},
        "token": body["token"],
        "id": body["user"]["id"],
    }


def _create_room(client: TestClient, user: dict, *, public: bool = True, name: str = "Room") -> dict:
    r = client.post(
        "/api/v1/rooms",
        json={"name": name, "description": "desc", "is_public": public},
        headers=user["headers"],
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------- rooms


def test_create_room_makes_owner_member(client: TestClient) -> None:
    a = _user(client)
    room = _create_room(client, a)
    assert room["name"] == "Room"
    assert room["role"] == "owner"
    assert room["is_member"] is True
    assert room["member_count"] == 1


def test_private_room_hidden_from_others(client: TestClient) -> None:
    a = _user(client, "a@example.com")
    room = _create_room(client, a, public=False)

    b = _user(client, "b@example.com")
    r = client.get("/api/v1/rooms", headers=b["headers"])
    assert r.status_code == 200
    assert all(x["id"] != room["id"] for x in r.json())

    r = client.get(f"/api/v1/rooms/{room['id']}", headers=b["headers"])
    assert r.status_code == 403


def test_public_room_visible_and_joinable(client: TestClient) -> None:
    a = _user(client, "a@example.com")
    room = _create_room(client, a, public=True)

    b = _user(client, "b@example.com")
    r = client.get("/api/v1/rooms", headers=b["headers"])
    assert r.status_code == 200
    mine = next(x for x in r.json() if x["id"] == room["id"])
    assert mine["is_member"] is False

    r = client.post(f"/api/v1/rooms/{room['id']}/join", headers=b["headers"])
    assert r.status_code == 200
    assert r.json()["is_member"] is True
    assert r.json()["role"] == "member"

    # join is idempotent
    r = client.post(f"/api/v1/rooms/{room['id']}/join", headers=b["headers"])
    assert r.status_code == 200


def test_private_room_join_denied_owner_can_add(client: TestClient) -> None:
    a = _user(client, "a@example.com")
    room = _create_room(client, a, public=False)

    b = _user(client, "b@example.com")
    r = client.post(f"/api/v1/rooms/{room['id']}/join", headers=b["headers"])
    assert r.status_code == 403

    r = client.post(
        f"/api/v1/rooms/{room['id']}/members", json={"user_id": b["id"]}, headers=a["headers"]
    )
    assert r.status_code == 201
    assert r.json()["role"] == "member"

    # member can now view the private room
    r = client.get(f"/api/v1/rooms/{room['id']}", headers=b["headers"])
    assert r.status_code == 200
    assert r.json()["is_member"] is True

    # members list contains owner + b
    r = client.get(f"/api/v1/rooms/{room['id']}/members", headers=b["headers"])
    assert r.status_code == 200
    assert {m["user_id"] for m in r.json()} == {a["id"], b["id"]}

    # non-owner cannot add members
    c = _user(client, "c@example.com")
    r = client.post(
        f"/api/v1/rooms/{room['id']}/members",
        json={"user_id": c["id"]},
        headers=b["headers"],
    )
    assert r.status_code == 403


def test_add_member_by_email(client: TestClient) -> None:
    a = _user(client, "a@example.com")
    room = _create_room(client, a, public=False)
    b = _user(client, "b@example.com")

    r = client.post(
        f"/api/v1/rooms/{room['id']}/members",
        json={"email": "B@example.com"},  # case-insensitive
        headers=a["headers"],
    )
    assert r.status_code == 201
    assert r.json()["user_id"] == b["id"]

    # unknown email → 404
    r = client.post(
        f"/api/v1/rooms/{room['id']}/members",
        json={"email": "nobody@example.com"},
        headers=a["headers"],
    )
    assert r.status_code == 404

    # neither id nor email → 400
    r = client.post(f"/api/v1/rooms/{room['id']}/members", json={}, headers=a["headers"])
    assert r.status_code == 400


def test_role_change_and_owner_guards(client: TestClient) -> None:
    a = _user(client, "a@example.com")
    room = _create_room(client, a, public=True)
    b = _user(client, "b@example.com")
    client.post(f"/api/v1/rooms/{room['id']}/join", headers=b["headers"])

    # member cannot update/delete the room
    assert client.patch(f"/api/v1/rooms/{room['id']}", json={"name": "hijack"}, headers=b["headers"]).status_code == 403
    assert client.delete(f"/api/v1/rooms/{room['id']}", headers=b["headers"]).status_code == 403

    # owner promotes b; b can now update the room
    r = client.patch(
        f"/api/v1/rooms/{room['id']}/members/{b['id']}", json={"role": "owner"}, headers=a["headers"]
    )
    assert r.status_code == 200
    r = client.patch(f"/api/v1/rooms/{room['id']}", json={"name": "renamed"}, headers=b["headers"])
    assert r.status_code == 200
    assert r.json()["name"] == "renamed"

    # the original creator cannot be demoted
    r = client.patch(
        f"/api/v1/rooms/{room['id']}/members/{a['id']}", json={"role": "member"}, headers=b["headers"]
    )
    assert r.status_code == 400


def test_leave_room_rules(client: TestClient) -> None:
    a = _user(client, "a@example.com")
    room = _create_room(client, a, public=True)
    b = _user(client, "b@example.com")
    client.post(f"/api/v1/rooms/{room['id']}/join", headers=b["headers"])

    # owner cannot leave
    r = client.post(f"/api/v1/rooms/{room['id']}/leave", headers=a["headers"])
    assert r.status_code == 400

    r = client.post(f"/api/v1/rooms/{room['id']}/leave", headers=b["headers"])
    assert r.status_code == 200
    assert client.get(f"/api/v1/rooms/{room['id']}/messages", headers=b["headers"]).status_code == 403


def test_room_messages_and_pagination(client: TestClient) -> None:
    a = _user(client, "a@example.com")
    room = _create_room(client, a, public=True)

    for i in range(5):
        r = client.post(
            f"/api/v1/rooms/{room['id']}/messages", json={"content": f"msg {i}"}, headers=a["headers"]
        )
        assert r.status_code == 201

    r = client.get(f"/api/v1/rooms/{room['id']}/messages", headers=a["headers"])
    assert r.status_code == 200
    rows = r.json()
    assert [m["content"] for m in rows] == ["msg 0", "msg 1", "msg 2", "msg 3", "msg 4"]
    assert all(m["name"] for m in rows)

    # before_id pagination: rows before the 4th message = first 3
    r = client.get(
        f"/api/v1/rooms/{room['id']}/messages?before_id={rows[3]['id']}&limit=10",
        headers=a["headers"],
    )
    assert [m["content"] for m in r.json()] == ["msg 0", "msg 1", "msg 2"]

    # non-member cannot post
    b = _user(client, "b@example.com")
    r = client.post(f"/api/v1/rooms/{room['id']}/messages", json={"content": "intrude"}, headers=b["headers"])
    assert r.status_code == 403

    # blank content rejected
    r = client.post(f"/api/v1/rooms/{room['id']}/messages", json={"content": "   "}, headers=a["headers"])
    assert r.status_code == 400


def test_message_delete_permissions(client: TestClient) -> None:
    a = _user(client, "a@example.com")
    room = _create_room(client, a, public=True)
    b = _user(client, "b@example.com")
    client.post(f"/api/v1/rooms/{room['id']}/join", headers=b["headers"])
    c = _user(client, "c@example.com")
    client.post(f"/api/v1/rooms/{room['id']}/join", headers=c["headers"])

    r = client.post(f"/api/v1/rooms/{room['id']}/messages", json={"content": "mine"}, headers=b["headers"])
    msg_id = r.json()["id"]

    # owner can delete another member's message
    assert client.delete(f"/api/v1/rooms/{room['id']}/messages/{msg_id}", headers=a["headers"]).status_code == 200

    r = client.post(f"/api/v1/rooms/{room['id']}/messages", json={"content": "again"}, headers=b["headers"])
    msg_id = r.json()["id"]
    # plain member cannot delete another member's message
    assert client.delete(f"/api/v1/rooms/{room['id']}/messages/{msg_id}", headers=c["headers"]).status_code == 403
    # the author can delete their own
    assert client.delete(f"/api/v1/rooms/{room['id']}/messages/{msg_id}", headers=b["headers"]).status_code == 200


def test_room_404(client: TestClient) -> None:
    a = _user(client)
    assert client.get("/api/v1/rooms/nope", headers=a["headers"]).status_code == 404
    assert client.delete("/api/v1/rooms/nope", headers=a["headers"]).status_code == 404


# ---------------------------------------------------------------- notes


def test_notes_crud(client: TestClient) -> None:
    a = _user(client)
    r = client.post("/api/v1/notes", json={"title": "Plan", "content": "# todo"}, headers=a["headers"])
    assert r.status_code == 201
    note_id = r.json()["id"]
    assert r.json()["title"] == "Plan"

    r = client.get("/api/v1/notes", headers=a["headers"])
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.patch(f"/api/v1/notes/{note_id}", json={"content": "# updated"}, headers=a["headers"])
    assert r.status_code == 200
    assert r.json()["content"] == "# updated"

    other = _user(client, "other@example.com")
    assert client.get(f"/api/v1/notes/{note_id}", headers=other["headers"]).status_code == 404
    assert client.patch(f"/api/v1/notes/{note_id}", json={"title": "x"}, headers=other["headers"]).status_code == 404

    assert client.delete(f"/api/v1/notes/{note_id}", headers=a["headers"]).status_code == 200
    assert client.get("/api/v1/notes", headers=a["headers"]).json() == []


def test_note_default_title(client: TestClient) -> None:
    a = _user(client)
    r = client.post("/api/v1/notes", json={"title": "", "content": "body"}, headers=a["headers"])
    assert r.status_code == 201
    assert r.json()["title"] == "Untitled"


# ---------------------------------------------------------------- playground


def test_playground_requires_auth(client: TestClient) -> None:
    r = client.post(
        "/api/v1/playground/completions",
        json={"model": "m", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 401


def test_playground_validation(client: TestClient) -> None:
    a = _user(client)
    r = client.post(
        "/api/v1/playground/completions",
        json={"model": "m", "messages": [{"role": "user", "content": "   "}]},
        headers=a["headers"],
    )
    assert r.status_code == 400

    r = client.post(
        "/api/v1/playground/completions",
        json={
            "model": "m",
            "messages": [{"role": "user", "content": "hi"}],
            "provider": "bogus",
        },
        headers=a["headers"],
    )
    assert r.status_code == 422


def test_playground_streams_completion(client: TestClient) -> None:
    """Happy path against the local mock Ollama: start → delta → done."""
    a = _user(client)
    r = client.post(
        "/api/v1/playground/completions",
        json={
            "model": "mock-model",
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "hello"},
            ],
        },
        headers=a["headers"],
    )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    assert "event: start" in r.text
    assert "event: delta" in r.text
    assert '"content"' in r.text
    assert "event: done" in r.text
    assert "event: error" not in r.text


# ---------------------------------------------------------------- websocket


def test_rooms_websocket_realtime_flow(client: TestClient) -> None:
    """Two clients join a room; presence + message events fan out live."""
    a = _user(client, "a@example.com")
    room = _create_room(client, a, public=True)
    room_id = room["id"]
    b = _user(client, "b@example.com")
    client.post(f"/api/v1/rooms/{room_id}/join", headers=b["headers"])

    with client.websocket_connect(f"/api/v1/rooms/ws?token={a['token']}") as wa, \
         client.websocket_connect(f"/api/v1/rooms/ws?token={b['token']}") as wb:
        wa.send_json({"op": "join", "room_id": room_id})
        ev = wa.receive_json()
        assert ev["type"] == "members"
        # members = live presence: only A is subscribed so far
        assert {u["user_id"] for u in ev["users"]} == {a["id"]}

        wb.send_json({"op": "join", "room_id": room_id})
        ev = wb.receive_json()
        assert ev["type"] == "members"
        assert {u["user_id"] for u in ev["users"]} == {a["id"], b["id"]}
        # A hears about B joining
        while True:
            ev = wa.receive_json()
            if ev["type"] == "presence" and ev["action"] == "joined":
                assert ev["user"]["id"] == b["id"]
                break

        # A sends a message; B receives it live
        wa.send_json({"op": "message", "room_id": room_id, "content": "hello room"})
        ev = wb.receive_json()
        assert ev["type"] == "message"
        assert ev["message"]["content"] == "hello room"
        assert ev["message"]["name"] == "User"

        # typing event fans out to B
        wa.send_json({"op": "typing", "room_id": room_id, "typing": True})
        ev = wb.receive_json()
        assert ev["type"] == "typing"
        assert ev["typing"] is True

        # leaving fires presence to the others
        wb.send_json({"op": "leave", "room_id": room_id})
        while True:
            ev = wa.receive_json()
            if ev["type"] == "presence" and ev["action"] == "left":
                assert ev["user"]["id"] == b["id"]
                break

    # message was persisted (REST sees it)
    r = client.get(f"/api/v1/rooms/{room_id}/messages", headers=a["headers"])
    assert [m["content"] for m in r.json()] == ["hello room"]


def test_rooms_websocket_rejects_non_member(client: TestClient) -> None:
    a = _user(client, "a@example.com")
    room = _create_room(client, a, public=False)  # private room

    b = _user(client, "b@example.com")
    with client.websocket_connect(f"/api/v1/rooms/ws?token={b['token']}") as ws:
        ws.send_json({"op": "join", "room_id": room["id"]})
        ev = ws.receive_json()
        assert ev["type"] == "error"
        assert "not a member" in ev["message"]


def test_rooms_websocket_requires_auth(client: TestClient) -> None:
    with pytest.raises(starlette.websockets.WebSocketDisconnect) as exc:
        with client.websocket_connect("/api/v1/rooms/ws"):
            pass
    assert exc.value.code == 4401
