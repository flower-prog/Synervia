"""AI Agent WebSocket routes with streaming support (PydanticAI)."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic_ai import (
    Agent,
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
    ToolCallPartDelta,
)
from pydantic_ai.messages import BinaryContent, TextPart

from app.agents.assistant import Deps, get_agent
from app.api.deps import get_conversation_service, get_current_user_ws
from app.core.config import settings
from app.db.models.user import User
from app.db.session import get_db_context
from app.services.agent import (
    AgentConnectionManager,
    build_message_history,
    persist_assistant_turn,
    persist_user_turn,
    resolve_kb_collections,
)
from app.services.file_storage import get_file_storage

logger = logging.getLogger(__name__)

router = APIRouter()

manager = AgentConnectionManager()


@router.get("/agent/models")
async def list_models() -> dict[str, Any]:
    """Return available LLM models and the current default."""
    return {
        "default": settings.AI_MODEL,
        "models": settings.AI_AVAILABLE_MODELS,
    }


async def _build_multimodal_input(user_message: str, file_ids: list[Any]) -> str | list[Any]:
    """Fold attached images and parsed file text into the user message.

    Images are attached as ``BinaryContent``; non-image files contribute their parsed
    content as a fenced text block appended to the message.
    """
    if not file_ids:
        return user_message

    storage = get_file_storage()
    image_parts: list[BinaryContent] = []
    file_context_parts: list[str] = []
    async with get_db_context() as file_db:
        attached_files = await get_conversation_service(file_db).list_attached_files(file_ids)
        for chat_file in attached_files:
            try:
                if chat_file.file_type == "image":
                    file_data = await storage.load(chat_file.storage_path)
                    image_parts.append(
                        BinaryContent(data=file_data, media_type=chat_file.mime_type)
                    )
                elif chat_file.parsed_content:
                    file_context_parts.append(
                        f"\n---\nAttached file: {chat_file.filename}\n```\n{chat_file.parsed_content}\n```"
                    )
            except Exception as e:
                logger.warning(f"Failed to load file {chat_file.id}: {e}")

    full_text = user_message + "".join(file_context_parts)
    if image_parts:
        return [full_text, *image_parts]
    return full_text


async def _stream_request_events(websocket: WebSocket, request_stream: Any) -> None:
    """Forward model-request events (text/tool deltas + final-result start) to the client."""
    async for event in request_stream:
        if isinstance(event, PartStartEvent):
            await manager.send_event(
                websocket,
                "part_start",
                {"index": event.index, "part_type": type(event.part).__name__},
            )
            if isinstance(event.part, TextPart) and event.part.content:
                await manager.send_event(
                    websocket,
                    "text_delta",
                    {"index": event.index, "content": event.part.content},
                )
        elif isinstance(event, PartDeltaEvent):
            if isinstance(event.delta, TextPartDelta):
                await manager.send_event(
                    websocket,
                    "text_delta",
                    {"index": event.index, "content": event.delta.content_delta},
                )
            elif isinstance(event.delta, ToolCallPartDelta):
                await manager.send_event(
                    websocket,
                    "tool_call_delta",
                    {"index": event.index, "args_delta": event.delta.args_delta},
                )
        elif isinstance(event, FinalResultEvent):
            await manager.send_event(
                websocket,
                "final_result_start",
                {"tool_name": event.tool_name},
            )


async def _stream_tool_events(
    websocket: WebSocket,
    handle_stream: Any,
    collected_tool_calls: list[dict[str, Any]],
) -> None:
    """Forward tool-call/result events; collect tool calls (with results) for persistence."""
    pending: dict[str, dict[str, Any]] = {}
    async for tool_event in handle_stream:
        if isinstance(tool_event, FunctionToolCallEvent):
            tc = {
                "tool_call_id": tool_event.part.tool_call_id,
                "tool_name": tool_event.part.tool_name,
                "args": tool_event.part.args,
            }
            collected_tool_calls.append(tc)
            pending[tool_event.part.tool_call_id] = tc
            await manager.send_event(websocket, "tool_call", tc)
        elif isinstance(tool_event, FunctionToolResultEvent):
            tc = pending.get(tool_event.tool_call_id)
            if tc is not None:
                tc["result"] = str(tool_event.result.content)
            await manager.send_event(
                websocket,
                "tool_result",
                {
                    "tool_call_id": tool_event.tool_call_id,
                    "content": str(tool_event.result.content),
                },
            )


async def _stream_agent_run(
    websocket: WebSocket,
    agent_run: Any,
    user_message: str,
    collected_tool_calls: list[dict[str, Any]],
) -> None:
    """Drive the agent_run iterator, dispatching each node to its streaming helper."""
    async for node in agent_run:
        if Agent.is_user_prompt_node(node):
            prompt_text = node.user_prompt if isinstance(node.user_prompt, str) else user_message
            await manager.send_event(websocket, "user_prompt_processed", {"prompt": prompt_text})
        elif Agent.is_model_request_node(node):
            await manager.send_event(websocket, "model_request_start", {})
            async with node.stream(agent_run.ctx) as request_stream:
                await _stream_request_events(websocket, request_stream)
        elif Agent.is_call_tools_node(node):
            await manager.send_event(websocket, "call_tools_start", {})
            async with node.stream(agent_run.ctx) as handle_stream:
                await _stream_tool_events(websocket, handle_stream, collected_tool_calls)
        elif Agent.is_end_node(node) and agent_run.result is not None:
            await manager.send_event(websocket, "final_result", {"output": agent_run.result.output})


async def _process_message(
    websocket: WebSocket,
    user: User,
    data: dict[str, Any],
    deps: Deps,
    conversation_history: list[dict[str, str]],
    current_conversation_id: str | None,
) -> str | None:
    """Process one user turn: persist input, run the agent, stream events, persist output.

    Returns the (possibly updated) ``current_conversation_id`` to carry into the next turn.
    """
    user_message = data.get("message", "")
    file_ids = data.get("file_ids", [])

    if not user_message and not file_ids:
        await manager.send_event(websocket, "error", {"message": "Empty message"})
        return current_conversation_id
    current_conversation_id, newly_created = await persist_user_turn(
        user,
        user_message,
        file_ids,
        requested_conversation_id=data.get("conversation_id"),
        current_conversation_id=current_conversation_id,
    )
    if newly_created and current_conversation_id:
        await manager.send_event(
            websocket,
            "conversation_created",
            {"conversation_id": current_conversation_id},
        )

    await manager.send_event(websocket, "user_prompt", {"content": user_message})

    try:
        assistant = get_agent(
            model_name=data.get("model"),
            thinking_effort=data.get("thinking_effort"),
        )
        model_history = build_message_history(conversation_history)
        user_input = await _build_multimodal_input(user_message, file_ids)
        deps.kb_collection_names = await resolve_kb_collections(
            current_conversation_id,
            user.id,
        )

        collected_tool_calls: list[dict[str, Any]] = []
        async with assistant.agent.iter(
            user_input, deps=deps, message_history=model_history
        ) as agent_run:
            await _stream_agent_run(websocket, agent_run, user_message, collected_tool_calls)

        # Update in-memory history only after a complete agent run
        if agent_run.result is not None:
            conversation_history.append({"role": "user", "content": user_message})
            conversation_history.append({"role": "assistant", "content": agent_run.result.output})
        assistant_msg_id: str | None = None
        if current_conversation_id and agent_run.result is not None:
            assistant_msg_id = await persist_assistant_turn(
                current_conversation_id,
                agent_run.result.output,
                getattr(assistant, "model_name", None),
                collected_tool_calls,
            )

        if assistant_msg_id:
            await manager.send_event(
                websocket,
                "message_saved",
                {
                    "message_id": assistant_msg_id,
                    "conversation_id": current_conversation_id,
                },
            )

        await manager.send_event(
            websocket, "complete", {"conversation_id": current_conversation_id}
        )
    except WebSocketDisconnect:
        raise
    except Exception as e:
        logger.exception(f"Error processing agent request: {e}")
        await manager.send_event(websocket, "error", {"message": str(e)})
    return current_conversation_id


@router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
    user: User = Depends(get_current_user_ws),
) -> None:
    """WebSocket endpoint for AI agent with full event streaming.

    Streams all PydanticAI agent events to the client:
    - user_prompt / user_prompt_processed: input received and accepted
    - model_request_start / part_start / text_delta / tool_call_delta: streaming output
    - tool_call / tool_result: tool execution
    - final_result / message_saved / complete: end-of-turn signals
    - error: unrecoverable error during processing

    Expected input message format::

        {
            "message": "user message here",
            "file_ids": ["..."],
            "conversation_id": "optional-uuid-to-continue-existing-conversation",
            "model": "optional-model-override",
            "thinking_effort": "optional"
        }

    Authentication: handled by ``get_current_user_ws`` (JWT).

    Persistence: pass ``conversation_id`` to continue an existing conversation; otherwise
    a new one is created and its id is returned via the ``conversation_created`` event.
    """
    if user is None:
        return

    await manager.connect(websocket)

    conversation_history: list[dict[str, str]] = []
    deps = Deps()
    current_conversation_id: str | None = None

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break

            try:
                current_conversation_id = await _process_message(
                    websocket,
                    user,
                    data,
                    deps,
                    conversation_history,
                    current_conversation_id,
                )
            except WebSocketDisconnect:
                logger.info("Client disconnected during agent processing")
                break
    finally:
        manager.disconnect(websocket)
