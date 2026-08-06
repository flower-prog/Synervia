from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai import FunctionToolCallEvent, FunctionToolResultEvent
from pydantic_ai.messages import ToolCallPart, ToolReturnPart

from app.services.agent_session import AgentSession


@pytest.mark.anyio
async def test_stream_tool_events_forwards_and_collects_tool_result():
    websocket = MagicMock()
    session = AgentSession(websocket=websocket, user=MagicMock())
    collected_tool_calls: list[dict[str, object]] = []
    emitted_events: list[tuple[str, dict[str, object]]] = []

    async def handle_stream():
        yield FunctionToolCallEvent(
            part=ToolCallPart(
                tool_name="search_knowledge_base",
                args={"query": "emergency supplies"},
                tool_call_id="call-1",
            )
        )
        yield FunctionToolResultEvent(
            part=ToolReturnPart(
                tool_name="search_knowledge_base",
                content='{"matches": []}',
                tool_call_id="call-1",
            )
        )

    async def capture_event(_websocket, event_type, data):
        emitted_events.append((event_type, dict(data)))
        return True

    with patch("app.services.agent_session.send_event", new=capture_event):
        await session._stream_tool_events(handle_stream(), collected_tool_calls)

    assert collected_tool_calls == [
        {
            "tool_call_id": "call-1",
            "tool_name": "search_knowledge_base",
            "args": {"query": "emergency supplies"},
            "result": '{"matches": []}',
        },
    ]
    assert emitted_events == [
        (
            "tool_call",
            {
                "tool_call_id": "call-1",
                "tool_name": "search_knowledge_base",
                "args": {"query": "emergency supplies"},
            },
        ),
        (
            "tool_result",
            {"tool_call_id": "call-1", "content": '{"matches": []}'},
        ),
    ]
