import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import WebSocketDisconnect

from app.models import QuizSession, SessionParticipant, SessionStatus, User, UserRole
from app.services import session_websocket


class FakeResult:
    def __init__(self, value: object | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object | None:
        return self.value


class FakeSession:
    def __init__(self, results: list[object | None]) -> None:
        self.results = results

    async def execute(self, _: object) -> FakeResult:
        return FakeResult(self.results.pop(0))


class SessionContext:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def __aenter__(self) -> FakeSession:
        return self.session

    async def __aexit__(self, *_: object) -> None:
        return None


class SessionFactory:
    def __init__(self, sessions: list[FakeSession]) -> None:
        self.sessions = sessions

    def __call__(self) -> SessionContext:
        return SessionContext(self.sessions.pop(0))


class FakeHub:
    def __init__(self) -> None:
        self.connected: list[tuple[object, object]] = []
        self.disconnected: list[tuple[object, object]] = []

    async def connect(self, session_id: object, websocket: object) -> None:
        self.connected.append((session_id, websocket))

    def disconnect(self, session_id: object, websocket: object) -> None:
        self.disconnected.append((session_id, websocket))


class FakeWebSocket:
    def __init__(self, message: dict[str, object]) -> None:
        self.query_params = {"token": "token"}
        self.message = message
        self.sent: list[dict[str, object]] = []
        self.closed: list[int] = []
        self._received = False

    async def receive_json(self) -> dict[str, object]:
        if self._received:
            raise WebSocketDisconnect()
        self._received = True
        return self.message

    async def send_json(self, message: dict[str, object]) -> None:
        self.sent.append(message)

    async def close(self, code: int) -> None:
        self.closed.append(code)


def test_websocket_handler_authorizes_dispatches_and_broadcasts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organizer = User(email="organizer@example.com", password_hash="hash", role=UserRole.ORGANIZER)
    organizer.id = uuid4()
    quiz_session = QuizSession(
        quiz_id=uuid4(), organizer_id=organizer.id, room_code="ROOM42", status=SessionStatus.ACTIVE
    )
    quiz_session.id = uuid4()
    request_id = uuid4()
    websocket = FakeWebSocket({"type": "session.end", "request_id": str(request_id)})
    hub = FakeHub()
    dispatched: list[tuple[object, object, object]] = []
    broadcasts: list[object] = []

    async def dispatch(session: object, user: object, session_id: object, command: object) -> object:
        dispatched.append((session, user, session_id))
        return SimpleNamespace(request_id=request_id)

    async def broadcast(session_id: object) -> None:
        broadcasts.append(session_id)

    command_session = FakeSession([])
    monkeypatch.setattr(
        session_websocket,
        "AsyncSessionLocal",
        SessionFactory([FakeSession([organizer, quiz_session]), command_session]),
    )
    monkeypatch.setattr(session_websocket, "scoreboard_hub", hub)
    monkeypatch.setattr(session_websocket, "verify_access_token", lambda _: {"sub": str(organizer.id)})
    monkeypatch.setattr(
        session_websocket,
        "session_update_payload",
        lambda _: asyncio.sleep(0, result={"type": "session.updated"}),
    )
    monkeypatch.setattr(session_websocket, "dispatch_session_command", dispatch)
    monkeypatch.setattr(session_websocket, "broadcast_session_update", broadcast)

    asyncio.run(session_websocket.session_websocket_handler(websocket, " room42 "))

    assert websocket.closed == []
    assert websocket.sent == [
        {"type": "session.updated"},
        {"type": "command.accepted", "request_id": str(request_id)},
    ]
    assert dispatched == [(command_session, organizer, quiz_session.id)]
    assert broadcasts == [quiz_session.id]
    assert hub.disconnected == [(quiz_session.id, websocket)]
