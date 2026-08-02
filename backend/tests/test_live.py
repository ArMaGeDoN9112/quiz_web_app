import asyncio
from uuid import uuid4

from app.core.live import ScoreboardHub


class FakeWebSocket:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def accept(self) -> None:
        return None

    async def send_json(self, message: dict[str, object]) -> None:
        self.messages.append(message)


def test_participant_updates_are_sent_only_to_organizers() -> None:
    hub = ScoreboardHub()
    session_id = uuid4()
    organizer_socket = FakeWebSocket()
    participant_socket = FakeWebSocket()

    async def run() -> None:
        await hub.connect(session_id, organizer_socket, is_organizer=True)
        await hub.connect(session_id, participant_socket, is_organizer=False)
        await hub.broadcast_to_organizers(session_id, {"type": "participants.updated"})

    asyncio.run(run())

    assert organizer_socket.messages == [{"type": "participants.updated"}]
    assert participant_socket.messages == []
