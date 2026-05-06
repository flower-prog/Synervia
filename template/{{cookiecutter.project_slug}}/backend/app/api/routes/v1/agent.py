{%- if cookiecutter.use_pydantic_ai %}
"""AI Agent WebSocket routes with streaming support (PydanticAI)."""

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect{%- if cookiecutter.websocket_auth_jwt %}, Depends{%- endif %}{%- if cookiecutter.websocket_auth_api_key %}, Query{%- endif %}

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
from app.core.config import settings
from app.services.agent import (
    AgentConnectionManager,
    build_message_history,
{%- if cookiecutter.use_database %}
    persist_assistant_turn,
    persist_user_turn,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
    resolve_kb_collections,
{%- endif %}
)
{%- if cookiecutter.websocket_auth_jwt %}
from app.api.deps import get_current_user_ws
from app.db.models.user import User
{%- endif %}
{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
from app.db.session import get_db_context{% if cookiecutter.use_sqlite %}, get_db_session
from contextlib import contextmanager{% endif %}
from app.api.deps import get_conversation_service
from app.services.file_storage import get_file_storage
{%- endif %}

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

{%- if cookiecutter.websocket_auth_api_key %}


async def verify_api_key(api_key: str) -> bool:
    """Verify the API key for WebSocket authentication."""
    return api_key == settings.API_KEY
{%- endif %}

{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}


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

{%- if cookiecutter.use_postgresql %}
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
{%- else %}
    with contextmanager(get_db_session)() as file_db:
        attached_files = get_conversation_service(file_db).list_attached_files(file_ids)
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
{%- endif %}

    full_text = user_message + "".join(file_context_parts)
    if image_parts:
        return [full_text, *image_parts]
    return full_text
{%- endif %}

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
            prompt_text = (
                node.user_prompt if isinstance(node.user_prompt, str) else user_message
            )
            await manager.send_event(
                websocket, "user_prompt_processed", {"prompt": prompt_text}
            )
        elif Agent.is_model_request_node(node):
            await manager.send_event(websocket, "model_request_start", {})
            async with node.stream(agent_run.ctx) as request_stream:
                await _stream_request_events(websocket, request_stream)
        elif Agent.is_call_tools_node(node):
            await manager.send_event(websocket, "call_tools_start", {})
            async with node.stream(agent_run.ctx) as handle_stream:
                await _stream_tool_events(websocket, handle_stream, collected_tool_calls)
        elif Agent.is_end_node(node) and agent_run.result is not None:
            await manager.send_event(
                websocket, "final_result", {"output": agent_run.result.output}
            )


async def _process_message(
    websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
    user: User,
{%- endif %}
    data: dict[str, Any],
    deps: Deps,
    conversation_history: list[dict[str, str]],
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None,
) -> str | None:
{%- else %}
) -> None:
{%- endif %}
    """Process one user turn: persist input, run the agent, stream events, persist output.
{%- if cookiecutter.use_database %}

    Returns the (possibly updated) ``current_conversation_id`` to carry into the next turn.
{%- endif %}
    """
    user_message = data.get("message", "")
    file_ids = data.get("file_ids", [])

    if not user_message and not file_ids:
        await manager.send_event(websocket, "error", {"message": "Empty message"})
{%- if cookiecutter.use_database %}
        return current_conversation_id
{%- else %}
        return
{%- endif %}

{%- if cookiecutter.use_database %}
    current_conversation_id, newly_created = await persist_user_turn(
{%- if cookiecutter.websocket_auth_jwt %}
        user,
{%- endif %}
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
{%- endif %}

    await manager.send_event(websocket, "user_prompt", {"content": user_message})

    try:
        assistant = get_agent(
            model_name=data.get("model"),
            thinking_effort=data.get("thinking_effort"),
        )
        model_history = build_message_history(conversation_history)
{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
        user_input = await _build_multimodal_input(user_message, file_ids)
{%- else %}
        user_input = user_message
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
        deps.kb_collection_names = await resolve_kb_collections(
{%- if cookiecutter.use_database %}
            current_conversation_id,
{%- else %}
            None,
{%- endif %}
{%- if cookiecutter.websocket_auth_jwt %}
{%- if cookiecutter.use_postgresql %}
            user.id,
{%- else %}
            str(user.id),
{%- endif %}
{%- endif %}
        )
{%- endif %}

        collected_tool_calls: list[dict[str, Any]] = []
        async with assistant.agent.iter(
            user_input, deps=deps, message_history=model_history
        ) as agent_run:
            await _stream_agent_run(
                websocket, agent_run, user_message, collected_tool_calls
            )

        # Update in-memory history only after a complete agent run
        if agent_run.result is not None:
            conversation_history.append({"role": "user", "content": user_message})
            conversation_history.append(
                {"role": "assistant", "content": agent_run.result.output}
            )

{%- if cookiecutter.use_database %}
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
{%- else %}
        await manager.send_event(websocket, "complete", {})
{%- endif %}
    except WebSocketDisconnect:
        raise
    except Exception as e:
        logger.exception(f"Error processing agent request: {e}")
        await manager.send_event(websocket, "error", {"message": str(e)})

{%- if cookiecutter.use_database %}
    return current_conversation_id
{%- endif %}


@router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
    user: User = Depends(get_current_user_ws),
{%- elif cookiecutter.websocket_auth_api_key %}
    api_key: str = Query(..., alias="api_key"),
{%- endif %}
) -> None:
    """WebSocket endpoint for AI agent with full event streaming.

    Streams all PydanticAI agent events to the client:
    - user_prompt / user_prompt_processed: input received and accepted
    - model_request_start / part_start / text_delta / tool_call_delta: streaming output
    - tool_call / tool_result: tool execution
    - final_result{% if cookiecutter.use_database %} / message_saved{% endif %} / complete: end-of-turn signals
    - error: unrecoverable error during processing

    Expected input message format::

        {
            "message": "user message here",
            "file_ids": ["..."]{% if cookiecutter.use_database %},
            "conversation_id": "optional-uuid-to-continue-existing-conversation"{% endif %},
            "model": "optional-model-override",
            "thinking_effort": "optional"
        }
{%- if cookiecutter.websocket_auth_jwt %}

    Authentication: handled by ``get_current_user_ws`` (JWT).
{%- elif cookiecutter.websocket_auth_api_key %}

    Authentication: pass ``api_key`` as a query parameter.
    Example: ws://localhost:{{ cookiecutter.backend_port }}/api/v1/ws/agent?api_key=your-api-key
{%- endif %}
{%- if cookiecutter.use_database %}

    Persistence: pass ``conversation_id`` to continue an existing conversation; otherwise
    a new one is created and its id is returned via the ``conversation_created`` event.
{%- endif %}
    """
{%- if cookiecutter.websocket_auth_api_key %}
    if not await verify_api_key(api_key):
        await websocket.close(code=4001, reason="Invalid API key")
        return
{%- elif cookiecutter.websocket_auth_jwt %}
    if user is None:
        return
{%- endif %}

    await manager.connect(websocket)

    conversation_history: list[dict[str, str]] = []
    deps = Deps()
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None = None
{%- endif %}

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break

            try:
{%- if cookiecutter.use_database %}
                current_conversation_id = await _process_message(
                    websocket,
{%- if cookiecutter.websocket_auth_jwt %}
                    user,
{%- endif %}
                    data,
                    deps,
                    conversation_history,
                    current_conversation_id,
                )
{%- else %}
                await _process_message(
                    websocket,
{%- if cookiecutter.websocket_auth_jwt %}
                    user,
{%- endif %}
                    data,
                    deps,
                    conversation_history,
                )
{%- endif %}
            except WebSocketDisconnect:
                logger.info("Client disconnected during agent processing")
                break
    finally:
        manager.disconnect(websocket)
{%- elif cookiecutter.use_langchain %}
"""AI Agent WebSocket routes with streaming support (LangChain)."""

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect{%- if cookiecutter.websocket_auth_jwt %}, Depends{%- endif %}{%- if cookiecutter.websocket_auth_api_key %}, Query{%- endif %}

from langchain.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from app.agents.langchain_assistant import AgentContext, get_agent
from app.core.config import settings
from app.services.agent import (
    AgentConnectionManager,
    build_message_history,
{%- if cookiecutter.use_database %}
    persist_assistant_turn,
    persist_user_turn,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
    resolve_kb_collections,
{%- endif %}
)
{%- if cookiecutter.websocket_auth_jwt %}
from app.api.deps import get_current_user_ws
from app.db.models.user import User
{%- endif %}

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

{%- if cookiecutter.websocket_auth_api_key %}


async def verify_api_key(api_key: str) -> bool:
    """Verify the API key for WebSocket authentication."""
    return api_key == settings.API_KEY
{%- endif %}


async def _stream_message_chunk(
    websocket: WebSocket,
    token: AIMessageChunk,
    seen_tool_call_ids: set[str],
) -> str:
    """Emit text deltas + partial tool_call events from a streaming AIMessageChunk.

    Returns the text content that was forwarded (so the caller can accumulate the
    final output).
    """
    text_content = ""
    if token.content:
        if isinstance(token.content, str):
            text_content = token.content
        elif isinstance(token.content, list):
            for block in token.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_content += block.get("text", "")
                elif isinstance(block, str):
                    text_content += block
        if text_content:
            await manager.send_event(websocket, "text_delta", {"content": text_content})

    if token.tool_call_chunks:
        for tc_chunk in token.tool_call_chunks:
            tc_id = tc_chunk.get("id")
            tc_name = tc_chunk.get("name")
            if tc_id and tc_name and tc_id not in seen_tool_call_ids:
                seen_tool_call_ids.add(tc_id)
                await manager.send_event(
                    websocket,
                    "tool_call",
                    {"tool_name": tc_name, "args": {}, "tool_call_id": tc_id},
                )
    return text_content


async def _stream_update_event(
    websocket: WebSocket,
    update_data: dict[str, Any],
    seen_tool_call_ids: set[str],
    pending: dict[str, dict[str, Any]],
    collected_tool_calls: list[dict[str, Any]],
) -> None:
    """Process ``updates`` stream events: tool execution results + canonical tool calls."""
    for node_name, update in update_data.items():
        if node_name == "tools":
            for msg in update.get("messages", []):
                if isinstance(msg, ToolMessage):
                    tc = pending.get(msg.tool_call_id)
                    if tc is not None:
                        tc["result"] = str(msg.content)
                    await manager.send_event(
                        websocket,
                        "tool_result",
                        {"tool_call_id": msg.tool_call_id, "content": msg.content},
                    )
        elif node_name == "model":
            for msg in update.get("messages", []):
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for tc_in in msg.tool_calls:
                        tc_id = tc_in.get("id", "")
                        if not tc_id:
                            continue
                        # Always record canonical tool call for persistence
                        tc = {
                            "tool_call_id": tc_id,
                            "tool_name": tc_in.get("name", ""),
                            "args": tc_in.get("args", {}),
                        }
                        pending[tc_id] = tc
                        collected_tool_calls.append(tc)
                        if tc_id not in seen_tool_call_ids:
                            seen_tool_call_ids.add(tc_id)
                            await manager.send_event(websocket, "tool_call", tc)


async def _stream_agent_response(
    websocket: WebSocket,
    assistant: Any,
    model_history: list[Any],
    context: AgentContext,
    collected_tool_calls: list[dict[str, Any]],
) -> str:
    """Run ``assistant.agent.astream`` and forward all events; return accumulated text."""
    final_output = ""
    seen_tool_call_ids: set[str] = set()
    pending: dict[str, dict[str, Any]] = {}

    await manager.send_event(websocket, "model_request_start", {})

    async for stream_mode, data in assistant.agent.astream(
        {"messages": model_history},
        stream_mode=["messages", "updates"],
        config={"configurable": context} if context else None,
    ):
        if stream_mode == "messages":
            token, _metadata = data
            if isinstance(token, AIMessageChunk):
                final_output += await _stream_message_chunk(
                    websocket, token, seen_tool_call_ids
                )
        elif stream_mode == "updates":
            await _stream_update_event(
                websocket, data, seen_tool_call_ids, pending, collected_tool_calls
            )

    await manager.send_event(websocket, "final_result", {"output": final_output})
    return final_output


async def _process_message(
    websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
    user: User,
{%- endif %}
    data: dict[str, Any],
    context: AgentContext,
    conversation_history: list[dict[str, str]],
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None,
) -> str | None:
{%- else %}
) -> None:
{%- endif %}
    """Process one user turn: persist input, run the agent, stream events, persist output."""
    user_message = data.get("message", "")
    file_ids = data.get("file_ids", [])

    if not user_message and not file_ids:
        await manager.send_event(websocket, "error", {"message": "Empty message"})
{%- if cookiecutter.use_database %}
        return current_conversation_id
{%- else %}
        return
{%- endif %}

{%- if cookiecutter.use_database %}
    current_conversation_id, newly_created = await persist_user_turn(
{%- if cookiecutter.websocket_auth_jwt %}
        user,
{%- endif %}
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
{%- endif %}

    await manager.send_event(websocket, "user_prompt", {"content": user_message})

    try:
        assistant = get_agent(
            model_name=data.get("model"),
            thinking_effort=data.get("thinking_effort"),
        )
        model_history = build_message_history(conversation_history)
        model_history.append(HumanMessage(content=user_message))

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
        from app.agents.tools.rag_tool import _active_kb_collections
        kb_names = await resolve_kb_collections(
{%- if cookiecutter.use_database %}
            current_conversation_id,
{%- else %}
            None,
{%- endif %}
{%- if cookiecutter.websocket_auth_jwt %}
{%- if cookiecutter.use_postgresql %}
            user.id,
{%- else %}
            str(user.id),
{%- endif %}
{%- endif %}
        )
        kb_token = _active_kb_collections.set(kb_names)
        try:
            collected_tool_calls: list[dict[str, Any]] = []
            final_output = await _stream_agent_response(
                websocket, assistant, model_history, context, collected_tool_calls
            )
        finally:
            _active_kb_collections.reset(kb_token)
{%- else %}
        collected_tool_calls: list[dict[str, Any]] = []
        final_output = await _stream_agent_response(
            websocket, assistant, model_history, context, collected_tool_calls
        )
{%- endif %}

        # Update in-memory history only after the agent produced output
        if final_output:
            conversation_history.append({"role": "user", "content": user_message})
            conversation_history.append({"role": "assistant", "content": final_output})

{%- if cookiecutter.use_database %}
        assistant_msg_id: str | None = None
        if current_conversation_id and final_output:
            assistant_msg_id = await persist_assistant_turn(
                current_conversation_id,
                final_output,
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
{%- else %}
        await manager.send_event(websocket, "complete", {})
{%- endif %}
    except WebSocketDisconnect:
        raise
    except Exception as e:
        logger.exception(f"Error processing agent request: {e}")
        await manager.send_event(websocket, "error", {"message": str(e)})

{%- if cookiecutter.use_database %}
    return current_conversation_id
{%- endif %}


@router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
    user: User = Depends(get_current_user_ws),
{%- elif cookiecutter.websocket_auth_api_key %}
    api_key: str = Query(..., alias="api_key"),
{%- endif %}
) -> None:
    """WebSocket endpoint for AI agent with streaming support (LangChain).

    Streams agent events to the client:
    - user_prompt / model_request_start / text_delta: input + streaming output
    - tool_call / tool_result: tool execution
    - final_result{% if cookiecutter.use_database %} / message_saved{% endif %} / complete: end-of-turn signals
    - error: unrecoverable error during processing
    """
{%- if cookiecutter.websocket_auth_api_key %}
    if not await verify_api_key(api_key):
        await websocket.close(code=4001, reason="Invalid API key")
        return
{%- elif cookiecutter.websocket_auth_jwt %}
    if user is None:
        return
{%- endif %}

    await manager.connect(websocket)

    conversation_history: list[dict[str, str]] = []
    context: AgentContext = {}
{%- if cookiecutter.websocket_auth_jwt %}
    context["user_id"] = str(user.id) if user else None
    context["user_name"] = user.email if user else None
{%- endif %}
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None = None
{%- endif %}

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break

            try:
{%- if cookiecutter.use_database %}
                current_conversation_id = await _process_message(
                    websocket,
{%- if cookiecutter.websocket_auth_jwt %}
                    user,
{%- endif %}
                    data,
                    context,
                    conversation_history,
                    current_conversation_id,
                )
{%- else %}
                await _process_message(
                    websocket,
{%- if cookiecutter.websocket_auth_jwt %}
                    user,
{%- endif %}
                    data,
                    context,
                    conversation_history,
                )
{%- endif %}
            except WebSocketDisconnect:
                logger.info("Client disconnected during agent processing")
                break
    finally:
        manager.disconnect(websocket)
{%- elif cookiecutter.use_langgraph %}
"""AI Agent WebSocket routes with streaming support (LangGraph ReAct Agent)."""

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect{%- if cookiecutter.websocket_auth_jwt %}, Depends{%- endif %}{%- if cookiecutter.websocket_auth_api_key %}, Query{%- endif %}

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from app.agents.langgraph_assistant import AgentContext, get_agent
from app.core.config import settings
from app.services.agent import (
    AgentConnectionManager,
{%- if cookiecutter.use_database %}
    persist_assistant_turn,
    persist_user_turn,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
    resolve_kb_collections,
{%- endif %}
)
{%- if cookiecutter.websocket_auth_jwt %}
from app.api.deps import get_current_user_ws
from app.db.models.user import User
{%- endif %}

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

{%- if cookiecutter.websocket_auth_api_key %}


async def verify_api_key(api_key: str) -> bool:
    """Verify the API key for WebSocket authentication."""
    return api_key == settings.API_KEY
{%- endif %}


async def _stream_message_chunk(
    websocket: WebSocket,
    chunk: AIMessageChunk,
    seen_tool_call_ids: set[str],
) -> str:
    """Emit text deltas + partial tool_call events from a streaming AIMessageChunk."""
    text_content = ""
    if chunk.content:
        if isinstance(chunk.content, str):
            text_content = chunk.content
        elif isinstance(chunk.content, list):
            for block in chunk.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_content += block.get("text", "")
                elif isinstance(block, str):
                    text_content += block
        if text_content:
            await manager.send_event(websocket, "text_delta", {"content": text_content})

    if chunk.tool_call_chunks:
        for tc_chunk in chunk.tool_call_chunks:
            tc_id = tc_chunk.get("id")
            tc_name = tc_chunk.get("name")
            if tc_id and tc_name and tc_id not in seen_tool_call_ids:
                seen_tool_call_ids.add(tc_id)
                await manager.send_event(
                    websocket,
                    "tool_call",
                    {"tool_name": tc_name, "args": {}, "tool_call_id": tc_id},
                )
    return text_content


async def _stream_update_event(
    websocket: WebSocket,
    update_data: dict[str, Any],
    seen_tool_call_ids: set[str],
    pending: dict[str, dict[str, Any]],
    collected_tool_calls: list[dict[str, Any]],
) -> None:
    """Process LangGraph ``updates`` events: tool results + canonical tool calls."""
    for node_name, update in update_data.items():
        if node_name == "tools":
            for msg in update.get("messages", []):
                if isinstance(msg, ToolMessage):
                    tc = pending.get(msg.tool_call_id)
                    if tc is not None:
                        tc["result"] = str(msg.content)
                    await manager.send_event(
                        websocket,
                        "tool_result",
                        {"tool_call_id": msg.tool_call_id, "content": msg.content},
                    )
        elif node_name == "agent":
            for msg in update.get("messages", []):
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for tc_in in msg.tool_calls:
                        tc_id = tc_in.get("id", "")
                        if not tc_id:
                            continue
                        tc = {
                            "tool_call_id": tc_id,
                            "tool_name": tc_in.get("name", ""),
                            "args": tc_in.get("args", {}),
                        }
                        pending[tc_id] = tc
                        collected_tool_calls.append(tc)
                        if tc_id not in seen_tool_call_ids:
                            seen_tool_call_ids.add(tc_id)
                            await manager.send_event(websocket, "tool_call", tc)


async def _stream_agent_response(
    websocket: WebSocket,
    assistant: Any,
    user_message: str,
    conversation_history: list[dict[str, str]],
    context: AgentContext,
    collected_tool_calls: list[dict[str, Any]],
) -> str:
    """Run the LangGraph agent stream and forward all events; return accumulated text."""
    final_output = ""
    seen_tool_call_ids: set[str] = set()
    pending: dict[str, dict[str, Any]] = {}

    await manager.send_event(websocket, "model_request_start", {})

    async for stream_mode, data in assistant.stream(
        user_message, history=conversation_history, context=context
    ):
        if stream_mode == "messages":
            chunk, _metadata = data
            if isinstance(chunk, AIMessageChunk):
                final_output += await _stream_message_chunk(
                    websocket, chunk, seen_tool_call_ids
                )
        elif stream_mode == "updates":
            await _stream_update_event(
                websocket, data, seen_tool_call_ids, pending, collected_tool_calls
            )

    await manager.send_event(websocket, "final_result", {"output": final_output})
    return final_output


async def _process_message(
    websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
    user: User,
{%- endif %}
    data: dict[str, Any],
    context: AgentContext,
    conversation_history: list[dict[str, str]],
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None,
) -> str | None:
{%- else %}
) -> None:
{%- endif %}
    """Process one user turn: persist input, run the agent, stream events, persist output."""
    user_message = data.get("message", "")
    file_ids = data.get("file_ids", [])

    if not user_message and not file_ids:
        await manager.send_event(websocket, "error", {"message": "Empty message"})
{%- if cookiecutter.use_database %}
        return current_conversation_id
{%- else %}
        return
{%- endif %}

{%- if cookiecutter.use_database %}
    current_conversation_id, newly_created = await persist_user_turn(
{%- if cookiecutter.websocket_auth_jwt %}
        user,
{%- endif %}
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
{%- endif %}

    await manager.send_event(websocket, "user_prompt", {"content": user_message})

    try:
        assistant = get_agent(
            model_name=data.get("model"),
            thinking_effort=data.get("thinking_effort"),
        )

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
        from app.agents.tools.rag_tool import _active_kb_collections
        kb_names = await resolve_kb_collections(
{%- if cookiecutter.use_database %}
            current_conversation_id,
{%- else %}
            None,
{%- endif %}
{%- if cookiecutter.websocket_auth_jwt %}
{%- if cookiecutter.use_postgresql %}
            user.id,
{%- else %}
            str(user.id),
{%- endif %}
{%- endif %}
        )
        kb_token = _active_kb_collections.set(kb_names)
        try:
            collected_tool_calls: list[dict[str, Any]] = []
            final_output = await _stream_agent_response(
                websocket,
                assistant,
                user_message,
                conversation_history,
                context,
                collected_tool_calls,
            )
        finally:
            _active_kb_collections.reset(kb_token)
{%- else %}
        collected_tool_calls: list[dict[str, Any]] = []
        final_output = await _stream_agent_response(
            websocket,
            assistant,
            user_message,
            conversation_history,
            context,
            collected_tool_calls,
        )
{%- endif %}

        # Update in-memory history only after the agent produced output
        if final_output:
            conversation_history.append({"role": "user", "content": user_message})
            conversation_history.append({"role": "assistant", "content": final_output})

{%- if cookiecutter.use_database %}
        assistant_msg_id: str | None = None
        if current_conversation_id and final_output:
            assistant_msg_id = await persist_assistant_turn(
                current_conversation_id,
                final_output,
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
{%- else %}
        await manager.send_event(websocket, "complete", {})
{%- endif %}
    except WebSocketDisconnect:
        raise
    except Exception as e:
        logger.exception(f"Error processing agent request: {e}")
        await manager.send_event(websocket, "error", {"message": str(e)})

{%- if cookiecutter.use_database %}
    return current_conversation_id
{%- endif %}


@router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
    user: User = Depends(get_current_user_ws),
{%- elif cookiecutter.websocket_auth_api_key %}
    api_key: str = Query(..., alias="api_key"),
{%- endif %}
) -> None:
    """WebSocket endpoint for LangGraph ReAct agent with streaming support."""
{%- if cookiecutter.websocket_auth_api_key %}
    if not await verify_api_key(api_key):
        await websocket.close(code=4001, reason="Invalid API key")
        return
{%- elif cookiecutter.websocket_auth_jwt %}
    if user is None:
        return
{%- endif %}

    await manager.connect(websocket)

    conversation_history: list[dict[str, str]] = []
    context: AgentContext = {}
{%- if cookiecutter.websocket_auth_jwt %}
    context["user_id"] = str(user.id) if user else None
    context["user_name"] = user.email if user else None
{%- endif %}
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None = None
{%- endif %}

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break

            try:
{%- if cookiecutter.use_database %}
                current_conversation_id = await _process_message(
                    websocket,
{%- if cookiecutter.websocket_auth_jwt %}
                    user,
{%- endif %}
                    data,
                    context,
                    conversation_history,
                    current_conversation_id,
                )
{%- else %}
                await _process_message(
                    websocket,
{%- if cookiecutter.websocket_auth_jwt %}
                    user,
{%- endif %}
                    data,
                    context,
                    conversation_history,
                )
{%- endif %}
            except WebSocketDisconnect:
                logger.info("Client disconnected during agent processing")
                break
    finally:
        manager.disconnect(websocket)
{%- elif cookiecutter.use_crewai %}
"""AI Agent WebSocket routes with streaming support (CrewAI Multi-Agent)."""

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect{%- if cookiecutter.websocket_auth_jwt %}, Depends{%- endif %}{%- if cookiecutter.websocket_auth_api_key %}, Query{%- endif %}

from app.agents.crewai_assistant import CrewContext, get_crew
from app.core.config import settings
from app.services.agent import (
    AgentConnectionManager,
{%- if cookiecutter.use_database %}
    persist_assistant_turn,
    persist_user_turn,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
    resolve_kb_collections,
{%- endif %}
)
{%- if cookiecutter.websocket_auth_jwt %}
from app.api.deps import get_current_user_ws
from app.db.models.user import User
{%- endif %}

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

{%- if cookiecutter.websocket_auth_api_key %}


async def verify_api_key(api_key: str) -> bool:
    """Verify the API key for WebSocket authentication."""
    return api_key == settings.API_KEY
{%- endif %}


async def _stream_crew_response(
    websocket: WebSocket,
    crew_assistant: Any,
    user_message: str,
    conversation_history: list[dict[str, str]],
    context: CrewContext,
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None,
{%- endif %}
) -> str:
    """Run the CrewAI crew stream and forward all events to the WebSocket.

    Each ``agent_completed`` event is also persisted as its own assistant message so the
    frontend can show per-agent contributions. Returns the final crew output.
    """
    final_output = ""

    await manager.send_event(
        websocket,
        "crew_start",
        {"crew_name": crew_assistant.config.name, "process": crew_assistant.config.process},
    )

    async for event in crew_assistant.stream(
        user_message, history=conversation_history, context=context
    ):
        event_type = event.get("type", "unknown")

        if event_type == "crew_started":
            await manager.send_event(
                websocket,
                "crew_started",
                {"crew_name": event.get("crew_name", ""), "crew_id": event.get("crew_id", "")},
            )
        elif event_type == "agent_started":
            await manager.send_event(
                websocket,
                "agent_started",
                {"agent": event.get("agent", ""), "task": event.get("task", "")},
            )
        elif event_type == "agent_completed":
            agent_name = event.get("agent", "")
            agent_output = event.get("output", "")
            await manager.send_event(
                websocket,
                "agent_completed",
                {"agent": agent_name, "output": agent_output},
            )
{%- if cookiecutter.use_database %}
            if current_conversation_id and agent_output:
                await persist_assistant_turn(
                    current_conversation_id,
                    f"✅ **{agent_name}**\n\n{agent_output}",
                    None,
                    [],
                )
{%- endif %}
        elif event_type == "task_started":
            await manager.send_event(
                websocket,
                "task_started",
                {
                    "task_id": event.get("task_id", ""),
                    "description": event.get("description", ""),
                    "agent": event.get("agent", ""),
                },
            )
        elif event_type == "task_completed":
            await manager.send_event(
                websocket,
                "task_completed",
                {
                    "task_id": event.get("task_id", ""),
                    "output": event.get("output", ""),
                    "agent": event.get("agent", ""),
                },
            )
        elif event_type == "tool_started":
            await manager.send_event(
                websocket,
                "tool_started",
                {
                    "tool_name": event.get("tool_name", ""),
                    "tool_args": event.get("tool_args", ""),
                    "agent": event.get("agent", ""),
                },
            )
        elif event_type == "tool_finished":
            await manager.send_event(
                websocket,
                "tool_finished",
                {
                    "tool_name": event.get("tool_name", ""),
                    "tool_result": event.get("tool_result", ""),
                    "agent": event.get("agent", ""),
                },
            )
        elif event_type == "llm_started":
            await manager.send_event(
                websocket, "llm_started", {"agent": event.get("agent", "")}
            )
        elif event_type == "llm_completed":
            await manager.send_event(
                websocket,
                "llm_completed",
                {"agent": event.get("agent", ""), "response": event.get("response", "")},
            )
        elif event_type == "crew_complete":
            final_output = event.get("result", "")
            await manager.send_event(
                websocket, "final_result", {"output": final_output}
            )
        elif event_type == "error":
            await manager.send_event(
                websocket, "error", {"message": event.get("error", "Unknown error")}
            )

    return final_output


async def _process_message(
    websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
    user: User,
{%- endif %}
    data: dict[str, Any],
    context: CrewContext,
    conversation_history: list[dict[str, str]],
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None,
) -> str | None:
{%- else %}
) -> None:
{%- endif %}
    """Process one user turn: persist input, run the crew, stream events."""
    user_message = data.get("message", "")
    file_ids = data.get("file_ids", [])

    if not user_message and not file_ids:
        await manager.send_event(websocket, "error", {"message": "Empty message"})
{%- if cookiecutter.use_database %}
        return current_conversation_id
{%- else %}
        return
{%- endif %}

{%- if cookiecutter.use_database %}
    current_conversation_id, newly_created = await persist_user_turn(
{%- if cookiecutter.websocket_auth_jwt %}
        user,
{%- endif %}
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
{%- endif %}

    await manager.send_event(websocket, "user_prompt", {"content": user_message})

    try:
        crew_assistant = get_crew()

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
        from app.agents.tools.rag_tool import _active_kb_collections
        kb_names = await resolve_kb_collections(
{%- if cookiecutter.use_database %}
            current_conversation_id,
{%- else %}
            None,
{%- endif %}
{%- if cookiecutter.websocket_auth_jwt %}
{%- if cookiecutter.use_postgresql %}
            user.id,
{%- else %}
            str(user.id),
{%- endif %}
{%- endif %}
        )
        kb_token = _active_kb_collections.set(kb_names)
        try:
            final_output = await _stream_crew_response(
                websocket,
                crew_assistant,
                user_message,
                conversation_history,
                context,
{%- if cookiecutter.use_database %}
                current_conversation_id,
{%- endif %}
            )
        finally:
            _active_kb_collections.reset(kb_token)
{%- else %}
        final_output = await _stream_crew_response(
            websocket,
            crew_assistant,
            user_message,
            conversation_history,
            context,
{%- if cookiecutter.use_database %}
            current_conversation_id,
{%- endif %}
        )
{%- endif %}

        # Update in-memory history only after the crew produced output
        if final_output:
            conversation_history.append({"role": "user", "content": user_message})
            conversation_history.append({"role": "assistant", "content": final_output})

        await manager.send_event(websocket, "complete", {
{%- if cookiecutter.use_database %}
            "conversation_id": current_conversation_id,
{%- endif %}
        })
    except WebSocketDisconnect:
        raise
    except Exception as e:
        logger.exception(f"Error processing agent request: {e}")
        await manager.send_event(websocket, "error", {"message": str(e)})

{%- if cookiecutter.use_database %}
    return current_conversation_id
{%- endif %}


@router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
    user: User = Depends(get_current_user_ws),
{%- elif cookiecutter.websocket_auth_api_key %}
    api_key: str = Query(..., alias="api_key"),
{%- endif %}
) -> None:
    """WebSocket endpoint for CrewAI multi-agent with streaming support."""
{%- if cookiecutter.websocket_auth_api_key %}
    if not await verify_api_key(api_key):
        await websocket.close(code=4001, reason="Invalid API key")
        return
{%- elif cookiecutter.websocket_auth_jwt %}
    if user is None:
        return
{%- endif %}

    await manager.connect(websocket)

    conversation_history: list[dict[str, str]] = []
    context: CrewContext = {}
{%- if cookiecutter.websocket_auth_jwt %}
    context["user_id"] = str(user.id) if user else None
    context["user_name"] = user.email if user else None
{%- endif %}
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None = None
{%- endif %}

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break

            try:
{%- if cookiecutter.use_database %}
                current_conversation_id = await _process_message(
                    websocket,
{%- if cookiecutter.websocket_auth_jwt %}
                    user,
{%- endif %}
                    data,
                    context,
                    conversation_history,
                    current_conversation_id,
                )
{%- else %}
                await _process_message(
                    websocket,
{%- if cookiecutter.websocket_auth_jwt %}
                    user,
{%- endif %}
                    data,
                    context,
                    conversation_history,
                )
{%- endif %}
            except WebSocketDisconnect:
                logger.info("Client disconnected during agent processing")
                break
    finally:
        manager.disconnect(websocket)
{%- elif cookiecutter.use_deepagents %}
"""AI Agent WebSocket routes with streaming and human-in-the-loop support (DeepAgents)."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect{%- if cookiecutter.websocket_auth_jwt %}, Depends{%- endif %}{%- if cookiecutter.websocket_auth_api_key %}, Query{%- endif %}

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from app.agents.deepagents_assistant import AgentContext, Decision, InterruptData, get_agent
from app.core.config import settings
from app.services.agent import (
    AgentConnectionManager,
{%- if cookiecutter.use_database %}
    persist_assistant_turn,
    persist_user_turn,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
    resolve_kb_collections,
{%- endif %}
)
{%- if cookiecutter.websocket_auth_jwt %}
from app.api.deps import get_current_user_ws
from app.db.models.user import User
{%- endif %}
{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
from app.db.session import get_db_context{% if cookiecutter.use_sqlite %}, get_db_session
from contextlib import contextmanager{% endif %}
from app.api.deps import get_conversation_service
{%- endif %}

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/agent/models")
async def list_models() -> dict[str, Any]:
    """Return available LLM models and the current default."""
    return {
        "default": settings.AI_MODEL,
        "models": settings.AI_AVAILABLE_MODELS,
    }


manager = AgentConnectionManager()

{%- if cookiecutter.websocket_auth_api_key %}


async def verify_api_key(api_key: str) -> bool:
    """Verify the API key for WebSocket authentication."""
    return api_key == settings.API_KEY
{%- endif %}


async def _stream_message_chunk(
    websocket: WebSocket,
    chunk: AIMessageChunk,
    seen_tool_call_ids: set[str],
) -> str:
    """Emit text deltas + partial tool_call events from a streaming AIMessageChunk."""
    text_content = ""
    if chunk.content:
        if isinstance(chunk.content, str):
            text_content = chunk.content
        elif isinstance(chunk.content, list):
            for block in chunk.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_content += block.get("text", "")
                elif isinstance(block, str):
                    text_content += block
        if text_content:
            await manager.send_event(websocket, "text_delta", {"content": text_content})

    if chunk.tool_call_chunks:
        for tc_chunk in chunk.tool_call_chunks:
            tc_id = tc_chunk.get("id")
            tc_name = tc_chunk.get("name")
            if tc_id and tc_name and tc_id not in seen_tool_call_ids:
                seen_tool_call_ids.add(tc_id)
                await manager.send_event(
                    websocket,
                    "tool_call",
                    {"tool_name": tc_name, "args": {}, "tool_call_id": tc_id},
                )
    return text_content


async def _stream_update_event(
    websocket: WebSocket,
    update_data: dict[str, Any],
    seen_tool_call_ids: set[str],
    pending: dict[str, dict[str, Any]],
    collected_tool_calls: list[dict[str, Any]],
) -> None:
    """Process LangGraph ``updates`` events: tool results + canonical tool calls."""
    for node_name, update in update_data.items():
        if node_name == "tools":
            for msg in update.get("messages", []):
                if isinstance(msg, ToolMessage):
                    tc = pending.get(msg.tool_call_id)
                    if tc is not None:
                        tc["result"] = str(msg.content)
                    await manager.send_event(
                        websocket,
                        "tool_result",
                        {"tool_call_id": msg.tool_call_id, "content": msg.content},
                    )
        elif node_name == "agent":
            for msg in update.get("messages", []):
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for tc_in in msg.tool_calls:
                        tc_id = tc_in.get("id", "")
                        if not tc_id:
                            continue
                        tc = {
                            "tool_call_id": tc_id,
                            "tool_name": tc_in.get("name", ""),
                            "args": tc_in.get("args", {}),
                        }
                        pending[tc_id] = tc
                        collected_tool_calls.append(tc)
                        if tc_id not in seen_tool_call_ids:
                            seen_tool_call_ids.add(tc_id)
                            await manager.send_event(websocket, "tool_call", tc)


async def _drive_stream(
    websocket: WebSocket,
    stream_iter: Any,
    collected_tool_calls: list[dict[str, Any]],
) -> tuple[str, InterruptData | None]:
    """Drive a DeepAgents stream iterator. Returns ``(final_output, pending_interrupt)``.

    On HITL interrupt, emits ``tool_approval_required`` and stops; caller can resume later
    by feeding decisions back via ``assistant.stream_resume``.
    """
    final_output = ""
    seen_tool_call_ids: set[str] = set()
    pending: dict[str, dict[str, Any]] = {}
    pending_interrupt: InterruptData | None = None

    async for stream_mode, stream_data in stream_iter:
        if stream_mode == "interrupt":
            pending_interrupt = stream_data
            await manager.send_event(
                websocket,
                "tool_approval_required",
                {
                    "action_requests": pending_interrupt["action_requests"],
                    "review_configs": pending_interrupt["review_configs"],
                },
            )
            break

        if stream_mode == "messages":
            chunk, _metadata = stream_data
            if isinstance(chunk, AIMessageChunk):
                final_output += await _stream_message_chunk(
                    websocket, chunk, seen_tool_call_ids
                )
        elif stream_mode == "updates":
            await _stream_update_event(
                websocket, stream_data, seen_tool_call_ids, pending, collected_tool_calls
            )

    return final_output, pending_interrupt

{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}


async def _build_agent_input(user_message: str, file_ids: list[Any]) -> str:
    """Fold attached file content into the user message as a plain-text suffix."""
    if not file_ids:
        return user_message

    file_refs: list[str] = []
{%- if cookiecutter.use_postgresql %}
    async with get_db_context() as file_db:
        attached_files = await get_conversation_service(file_db).list_attached_files(file_ids)
{%- else %}
    with contextmanager(get_db_session)() as file_db:
        attached_files = get_conversation_service(file_db).list_attached_files(file_ids)
{%- endif %}
    for chat_file in attached_files:
        if chat_file.parsed_content:
            file_refs.append(
                f"- {chat_file.filename}:\n```\n{chat_file.parsed_content}\n```"
            )
        elif chat_file.file_type == "image":
            file_refs.append(f"- {chat_file.filename} (image file)")
        else:
            file_refs.append(f"- {chat_file.filename} (binary file)")

    if file_refs:
        return user_message + "\n\nAttached files:\n" + "\n".join(file_refs)
    return user_message
{%- endif %}


async def _process_resume(
    websocket: WebSocket,
    raw_data: dict[str, Any],
    assistant: Any,
    thread_id: str,
    context: AgentContext,
    conversation_history: list[dict[str, str]],
    pending_interrupt: InterruptData | None,
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None,
{%- endif %}
) -> InterruptData | None:
    """Resume an interrupted agent run with user decisions. Returns the new interrupt (if any)."""
    if not pending_interrupt:
        await manager.send_event(
            websocket, "error", {"message": "No pending interrupt to resume"}
        )
        return None

    decisions: list[Decision] = raw_data.get("decisions", [])
    if len(decisions) != len(pending_interrupt["action_requests"]):
        await manager.send_event(
            websocket,
            "error",
            {
                "message": (
                    f"Expected {len(pending_interrupt['action_requests'])} decisions, "
                    f"got {len(decisions)}"
                )
            },
        )
        return pending_interrupt  # keep existing interrupt; caller decides

    try:
        await manager.send_event(websocket, "resume_start", {})
        collected_tool_calls: list[dict[str, Any]] = []
        final_output, new_interrupt = await _drive_stream(
            websocket,
            assistant.stream_resume(
                decisions=decisions, thread_id=thread_id, context=context
            ),
            collected_tool_calls,
        )
        if new_interrupt:
            return new_interrupt

        if final_output:
            conversation_history.append({"role": "assistant", "content": final_output})
{%- if cookiecutter.use_database %}
        if current_conversation_id and final_output:
            await persist_assistant_turn(
                current_conversation_id,
                final_output,
                getattr(assistant, "model_name", None),
                collected_tool_calls,
            )
{%- endif %}
        await manager.send_event(websocket, "final_result", {"output": final_output})
        await manager.send_event(websocket, "complete", {})
    except Exception as e:
        logger.exception(f"Error resuming agent: {e}")
        await manager.send_event(websocket, "error", {"message": str(e)})

    return None


async def _process_message(
    websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
    user: User,
{%- endif %}
    raw_data: dict[str, Any],
    assistant: Any,
    thread_id: str,
    context: AgentContext,
    conversation_history: list[dict[str, str]],
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None,
) -> tuple[InterruptData | None, str | None]:
{%- else %}
) -> InterruptData | None:
{%- endif %}
    """Process one user turn: persist input, run the agent, stream events, persist output.

    Returns the pending interrupt (if any) so the caller can hold it for the next ``resume``
    message{% if cookiecutter.use_database %}, plus the (possibly updated) conversation id{% endif %}.
    """
    user_message = raw_data.get("message", "")
    file_ids = raw_data.get("file_ids", [])

    # Optionally accept history from client (or use server-side tracking)
    if "history" in raw_data:
        conversation_history[:] = raw_data["history"]

    if not user_message and not file_ids:
        await manager.send_event(websocket, "error", {"message": "Empty message"})
{%- if cookiecutter.use_database %}
        return None, current_conversation_id
{%- else %}
        return None
{%- endif %}

{%- if cookiecutter.use_database %}
    current_conversation_id, newly_created = await persist_user_turn(
{%- if cookiecutter.websocket_auth_jwt %}
        user,
{%- endif %}
        user_message,
        file_ids,
        requested_conversation_id=raw_data.get("conversation_id"),
        current_conversation_id=current_conversation_id,
    )
    if newly_created and current_conversation_id:
        await manager.send_event(
            websocket,
            "conversation_created",
            {"conversation_id": current_conversation_id},
        )
{%- endif %}

    await manager.send_event(websocket, "user_prompt", {"content": user_message})

    try:
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}
        agent_input = await _build_agent_input(user_message, file_ids)
{%- else %}
        agent_input = user_message
{%- endif %}

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
        from app.agents.tools.rag_tool import _active_kb_collections
        kb_names = await resolve_kb_collections(
{%- if cookiecutter.use_database %}
            current_conversation_id,
{%- else %}
            None,
{%- endif %}
{%- if cookiecutter.websocket_auth_jwt %}
{%- if cookiecutter.use_postgresql %}
            user.id,
{%- else %}
            str(user.id),
{%- endif %}
{%- endif %}
        )
        kb_token = _active_kb_collections.set(kb_names)
        try:
            await manager.send_event(websocket, "model_request_start", {})
            collected_tool_calls: list[dict[str, Any]] = []
            final_output, pending_interrupt = await _drive_stream(
                websocket,
                assistant.stream(
                    agent_input,
                    history=conversation_history,
                    context=context,
                    thread_id=thread_id,
                ),
                collected_tool_calls,
            )
        finally:
            _active_kb_collections.reset(kb_token)
{%- else %}
        await manager.send_event(websocket, "model_request_start", {})
        collected_tool_calls: list[dict[str, Any]] = []
        final_output, pending_interrupt = await _drive_stream(
            websocket,
            assistant.stream(
                agent_input,
                history=conversation_history,
                context=context,
                thread_id=thread_id,
            ),
            collected_tool_calls,
        )
{%- endif %}

        if pending_interrupt:
{%- if cookiecutter.use_database %}
            return pending_interrupt, current_conversation_id
{%- else %}
            return pending_interrupt
{%- endif %}

        await manager.send_event(websocket, "final_result", {"output": final_output})

        # Update in-memory history only after the agent produced output
        if final_output:
            conversation_history.append({"role": "user", "content": user_message})
            conversation_history.append({"role": "assistant", "content": final_output})

{%- if cookiecutter.use_database %}
        assistant_msg_id: str | None = None
        if current_conversation_id and final_output:
            assistant_msg_id = await persist_assistant_turn(
                current_conversation_id,
                final_output,
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
{%- else %}
        await manager.send_event(websocket, "complete", {})
{%- endif %}
    except WebSocketDisconnect:
        raise
    except Exception as e:
        logger.exception(f"Error processing agent request: {e}")
        await manager.send_event(websocket, "error", {"message": str(e)})

{%- if cookiecutter.use_database %}
    return None, current_conversation_id
{%- else %}
    return None
{%- endif %}


@router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
    user: User = Depends(get_current_user_ws),
{%- elif cookiecutter.websocket_auth_api_key %}
    api_key: str = Query(..., alias="api_key"),
{%- endif %}
) -> None:
    """WebSocket endpoint for DeepAgents with streaming and human-in-the-loop support.

    Streams agent events to the client (text/tool deltas, tool results, final result),
    plus ``tool_approval_required`` when DEEPAGENTS_INTERRUPT_TOOLS is configured.
    The client should respond to an interrupt with::

        {"type": "resume", "decisions": [{"type": "approve"|"reject"|"edit", ...}]}
    """
{%- if cookiecutter.websocket_auth_api_key %}
    if not await verify_api_key(api_key):
        await websocket.close(code=4001, reason="Invalid API key")
        return
{%- elif cookiecutter.websocket_auth_jwt %}
    if user is None:
        return
{%- endif %}

    await manager.connect(websocket)

    conversation_history: list[dict[str, str]] = []
    context: AgentContext = {}
    thread_id: str = str(uuid.uuid4())
    pending_interrupt: InterruptData | None = None
{%- if cookiecutter.websocket_auth_jwt %}
    context["user_id"] = str(user.id) if user else None
    context["user_name"] = user.email if user else None
{%- endif %}
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None = None
{%- endif %}

    assistant = get_agent()

    try:
        while True:
            try:
                raw_data = await websocket.receive_json()
            except WebSocketDisconnect:
                break

            try:
                if raw_data.get("type", "message") == "resume":
                    pending_interrupt = await _process_resume(
                        websocket,
                        raw_data,
                        assistant,
                        thread_id,
                        context,
                        conversation_history,
                        pending_interrupt,
{%- if cookiecutter.use_database %}
                        current_conversation_id,
{%- endif %}
                    )
                else:
{%- if cookiecutter.use_database %}
                    pending_interrupt, current_conversation_id = await _process_message(
                        websocket,
{%- if cookiecutter.websocket_auth_jwt %}
                        user,
{%- endif %}
                        raw_data,
                        assistant,
                        thread_id,
                        context,
                        conversation_history,
                        current_conversation_id,
                    )
{%- else %}
                    pending_interrupt = await _process_message(
                        websocket,
{%- if cookiecutter.websocket_auth_jwt %}
                        user,
{%- endif %}
                        raw_data,
                        assistant,
                        thread_id,
                        context,
                        conversation_history,
                    )
{%- endif %}
            except WebSocketDisconnect:
                logger.info("Client disconnected during agent processing")
                break
    finally:
        manager.disconnect(websocket)


{%- elif cookiecutter.use_pydantic_deep %}
"""AI Agent WebSocket routes with streaming support (PydanticDeep)."""

import logging
from typing import Any
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

from fastapi import APIRouter, WebSocket, WebSocketDisconnect{%- if cookiecutter.websocket_auth_jwt %}, Depends{%- endif %}{%- if cookiecutter.websocket_auth_api_key %}, Query{%- endif %}

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

from app.agents.pydantic_deep_assistant import PydanticDeepContext, get_agent
from app.core.config import settings
from app.services.agent import (
    AgentConnectionManager,
{%- if cookiecutter.use_database %}
    persist_assistant_turn,
    persist_user_turn,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
    resolve_kb_collections,
{%- endif %}
)
{%- if cookiecutter.websocket_auth_jwt %}
from app.api.deps import get_current_user_ws
from app.db.models.user import User
{%- endif %}
{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
from app.db.session import get_db_context{% if cookiecutter.use_sqlite %}, get_db_session
from contextlib import contextmanager{% endif %}
from app.api.deps import get_conversation_service
from app.services.file_storage import get_file_storage
{%- if cookiecutter.use_postgresql %}
from app.api.deps import get_project_service
from app.schemas.conversation import ConversationCreate, MessageCreate
from pydantic_ai_backends import StateBackend
{%- endif %}
{%- endif %}

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

{%- if cookiecutter.websocket_auth_api_key %}


async def verify_api_key(api_key: str) -> bool:
    """Verify the API key for WebSocket authentication."""
    return api_key == settings.API_KEY
{%- endif %}


async def _stream_request_events(websocket: WebSocket, request_stream: Any) -> None:
    """Forward model-request events (text/tool deltas + final-result start)."""
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
                websocket, "final_result_start", {"tool_name": event.tool_name}
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
    """Drive the pydantic-ai agent_run iterator, forwarding all events."""
    async for node in agent_run:
        if Agent.is_user_prompt_node(node):
            prompt_text = (
                node.user_prompt if isinstance(node.user_prompt, str) else user_message
            )
            await manager.send_event(
                websocket, "user_prompt_processed", {"prompt": prompt_text}
            )
        elif Agent.is_model_request_node(node):
            await manager.send_event(websocket, "model_request_start", {})
            async with node.stream(agent_run.ctx) as request_stream:
                await _stream_request_events(websocket, request_stream)
        elif Agent.is_call_tools_node(node):
            await manager.send_event(websocket, "call_tools_start", {})
            async with node.stream(agent_run.ctx) as handle_stream:
                await _stream_tool_events(websocket, handle_stream, collected_tool_calls)
        elif Agent.is_end_node(node) and agent_run.result is not None:
            await manager.send_event(
                websocket, "final_result", {"output": agent_run.result.output}
            )

{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}


async def _build_agent_input(
    user_message: str, file_ids: list[Any], assistant: Any
) -> str | list[Any]:
    """Fold attached files into the agent input.

    Sandbox backends (Docker/Daytona) get files written to the workspace and a path
    reference appended to the prompt. ``StateBackend`` falls back to inline content.
    Images are always attached as ``BinaryContent`` parts for vision models.
    """
    if not file_ids:
        return user_message

    storage = get_file_storage()
    file_refs: list[str] = []
    image_parts: list[Any] = []

    backend = assistant.deps.backend
    has_sandbox = (
        hasattr(backend, "container_name")
        or hasattr(backend, "upload_bytes")
        or hasattr(backend, "workspace_id")
    )

{%- if cookiecutter.use_postgresql %}
    async with get_db_context() as file_db:
        attached_files = await get_conversation_service(file_db).list_attached_files(file_ids)
{%- else %}
    with contextmanager(get_db_session)() as file_db:
        attached_files = get_conversation_service(file_db).list_attached_files(file_ids)
{%- endif %}
    for chat_file in attached_files:
        try:
            rel_path = f"uploads/{chat_file.filename}"

            if chat_file.file_type == "image":
                file_data = await storage.load(chat_file.storage_path)
                image_parts.append(
                    BinaryContent(data=file_data, media_type=chat_file.mime_type)
                )
                if has_sandbox:
                    await assistant.write_file_to_workspace(rel_path, file_data)
                    file_refs.append(
                        f"- {rel_path} (image, also attached inline for vision)"
                    )
                else:
                    file_refs.append(f"- {chat_file.filename} (image attached inline)")
            elif chat_file.parsed_content:
                if has_sandbox:
                    await assistant.write_file_to_workspace(
                        rel_path, chat_file.parsed_content
                    )
                    file_refs.append(f"- {rel_path}")
                else:
                    file_refs.append(
                        f"- {chat_file.filename}:\n```\n{chat_file.parsed_content}\n```"
                    )
            else:
                file_data = await storage.load(chat_file.storage_path)
                if has_sandbox:
                    await assistant.write_file_to_workspace(rel_path, file_data)
                    file_refs.append(f"- {rel_path}")
                else:
                    file_refs.append(
                        f"- {chat_file.filename} (binary, not readable as text)"
                    )
        except Exception as e:
            logger.warning(f"Failed to load file {chat_file.id}: {e}")

    if not file_refs:
        return user_message

    header = (
        "\n\nFiles uploaded to your sandbox workspace (use read_file to access):\n"
        if has_sandbox
        else "\n\nAttached files:\n"
    )
    augmented = user_message + header + "\n".join(file_refs)
    return [augmented, *image_parts] if image_parts else augmented
{%- endif %}


async def _process_message(
    websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
    user: User,
{%- endif %}
    data: dict[str, Any],
    context: PydanticDeepContext,
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None,
) -> str | None:
{%- else %}
) -> None:
{%- endif %}
    """Process one user turn: persist input, run the agent, stream events, persist output."""
    user_message = data.get("message", "")
    file_ids = data.get("file_ids", [])

    if not user_message and not file_ids:
        await manager.send_event(websocket, "error", {"message": "Empty message"})
{%- if cookiecutter.use_database %}
        return current_conversation_id
{%- else %}
        return
{%- endif %}

{%- if cookiecutter.use_database %}
    current_conversation_id, newly_created = await persist_user_turn(
{%- if cookiecutter.websocket_auth_jwt %}
        user,
{%- endif %}
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
{%- endif %}

    await manager.send_event(websocket, "user_prompt", {"content": user_message})

    try:
        assistant = get_agent(
            model_name=data.get("model"),
{%- if cookiecutter.use_database %}
            conversation_id=current_conversation_id or "default",
{%- else %}
            conversation_id="default",
{%- endif %}
{%- if cookiecutter.websocket_auth_jwt %}
            user_id=context.get("user_id"),
            user_name=context.get("user_name"),
{%- endif %}
        )

{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}
        user_input = await _build_agent_input(user_message, file_ids, assistant)
{%- else %}
        user_input = user_message
{%- endif %}

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
        from app.agents.tools.rag_tool import _active_kb_collections
        kb_names = await resolve_kb_collections(
{%- if cookiecutter.use_database %}
            current_conversation_id,
{%- else %}
            None,
{%- endif %}
{%- if cookiecutter.websocket_auth_jwt %}
{%- if cookiecutter.use_postgresql %}
            user.id,
{%- else %}
            str(user.id),
{%- endif %}
{%- endif %}
        )
        kb_token = _active_kb_collections.set(kb_names)
        try:
            collected_tool_calls: list[dict[str, Any]] = []
            async with assistant.agent.iter(user_input, deps=assistant.deps) as agent_run:
                await _stream_agent_run(
                    websocket, agent_run, user_message, collected_tool_calls
                )
        finally:
            _active_kb_collections.reset(kb_token)
{%- else %}
        collected_tool_calls: list[dict[str, Any]] = []
        async with assistant.agent.iter(user_input, deps=assistant.deps) as agent_run:
            await _stream_agent_run(
                websocket, agent_run, user_message, collected_tool_calls
            )
{%- endif %}

{%- if cookiecutter.use_database %}
        if current_conversation_id and agent_run.result is not None:
            await persist_assistant_turn(
                current_conversation_id,
                agent_run.result.output,
                getattr(assistant, "model_name", None),
                collected_tool_calls,
            )

        await manager.send_event(
            websocket, "complete", {"conversation_id": current_conversation_id}
        )
{%- else %}
        await manager.send_event(websocket, "complete", {})
{%- endif %}
    except WebSocketDisconnect:
        raise
    except Exception as e:
        logger.exception(f"Error processing agent request: {e}")
        await manager.send_event(websocket, "error", {"message": str(e)})

{%- if cookiecutter.use_database %}
    return current_conversation_id
{%- endif %}


@router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
    user: User = Depends(get_current_user_ws),
{%- elif cookiecutter.websocket_auth_api_key %}
    api_key: str = Query(..., alias="api_key"),
{%- endif %}
) -> None:
    """WebSocket endpoint for PydanticDeep agent with full event streaming.

    PydanticDeep manages conversation history internally via the backend
    (history_messages_path). Unlike other frameworks, no message history needs to be
    passed — just send the next user message.
    """
{%- if cookiecutter.websocket_auth_api_key %}
    if not await verify_api_key(api_key):
        await websocket.close(code=4001, reason="Invalid API key")
        return
{%- elif cookiecutter.websocket_auth_jwt %}
    if user is None:
        return
{%- endif %}

    await manager.connect(websocket)

    context: PydanticDeepContext = {}
{%- if cookiecutter.websocket_auth_jwt %}
    context["user_id"] = str(user.id) if user else None
    context["user_name"] = user.email if user else None
{%- endif %}
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None = None
{%- endif %}

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break

            try:
{%- if cookiecutter.use_database %}
                current_conversation_id = await _process_message(
                    websocket,
{%- if cookiecutter.websocket_auth_jwt %}
                    user,
{%- endif %}
                    data,
                    context,
                    current_conversation_id,
                )
{%- else %}
                await _process_message(
                    websocket,
{%- if cookiecutter.websocket_auth_jwt %}
                    user,
{%- endif %}
                    data,
                    context,
                )
{%- endif %}
            except WebSocketDisconnect:
                logger.info("Client disconnected during agent processing")
                break
    finally:
        manager.disconnect(websocket)

{%- if cookiecutter.use_jwt and cookiecutter.use_postgresql %}


@router.websocket("/ws/projects/{project_id}/chats/{conversation_id}")
async def project_chat_websocket(
    project_id: UUID,
    conversation_id: UUID,
    websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
    user: User = Depends(get_current_user_ws),
{%- elif cookiecutter.websocket_auth_api_key %}
    api_key: str = Query(..., alias="api_key"),
{%- endif %}
) -> None:
    """WebSocket endpoint for project-scoped PydanticDeep chat.

    One Docker container per project is shared across all chats.
    Chat history is stored per-chat inside the project volume at:
      .pydantic-deep/sessions/{conversation_id}/messages.json

    Expected input message format:
    {
        "message": "user message here"
    }

    Authentication: Requires a valid JWT token passed as a query parameter or header.
    """
{%- if cookiecutter.websocket_auth_api_key %}
    if not await verify_api_key(api_key):
        await websocket.close(code=4001, reason="Invalid API key")
        return
{%- endif %}

    await manager.connect(websocket)

    context: PydanticDeepContext = {}
{%- if cookiecutter.websocket_auth_jwt %}
    context["user_id"] = str(user.id) if user else None
    context["user_name"] = user.email if user else None
{%- endif %}

    try:
        # Verify project access and load project config
        async with get_db_context() as db:
            project_service = get_project_service(db)
            try:
{%- if cookiecutter.websocket_auth_jwt %}
                await project_service.get(project_id, user_id=user.id)
{%- else %}
                await project_service.get(project_id)
{%- endif %}
            except Exception as exc:
                await websocket.close(code=4003, reason=str(exc))
                return

        # Build agent backend for this project
        backend: Any = StateBackend()

        assistant = get_agent(
            conversation_id=str(conversation_id),
            backend_override=backend,
            history_messages_path=f".pydantic-deep/sessions/{conversation_id}/messages.json",
        )

        # Ensure the conversation record exists and is linked to the project
        async with get_db_context() as db:
            conv_service = get_conversation_service(db)
            try:
                conv = await conv_service.get_conversation(conversation_id
{%- if cookiecutter.websocket_auth_jwt %}, user_id=user.id{%- endif %})
            except Exception:
                conv = await conv_service.create_conversation(
                    ConversationCreate(
{%- if cookiecutter.websocket_auth_jwt %}
                        user_id=user.id,
{%- endif %}
                        project_id=project_id,
                    )
                )
                await manager.send_event(
                    websocket,
                    "conversation_created",
                    {"conversation_id": str(conv.id), "project_id": str(project_id)},
                )

        while True:
            data = await websocket.receive_json()
            user_message = data.get("message", "")

            if not user_message:
                await manager.send_event(websocket, "error", {"message": "Empty message"})
                continue

            await manager.send_event(websocket, "user_prompt", {"content": user_message})

            # Persist user message
            async with get_db_context() as db:
                conv_service = get_conversation_service(db)
                try:
                    await conv_service.add_message(
                        conversation_id,
                        MessageCreate(role="user", content=user_message),
                    )
                except Exception as exc:
                    logger.warning("Failed to persist user message: %s", exc)

            try:
                await manager.send_event(websocket, "model_request_start", {})

                async with assistant.agent.run_stream(
                    user_message,
                    deps=assistant.deps,
                ) as stream:
                    async for event in stream.stream_events():
                        if isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
                            await manager.send_event(
                                websocket,
                                "text_delta",
                                {"delta": event.delta.content_delta},
                            )
                        elif isinstance(event, PartStartEvent) and isinstance(event.part, TextPart):
                            pass  # stream started
                        elif isinstance(event, FunctionToolCallEvent):
                            await manager.send_event(
                                websocket,
                                "tool_call",
                                {"tool_name": event.part.tool_name, "args": str(event.part.args)},
                            )
                        elif isinstance(event, FunctionToolResultEvent):
                            await manager.send_event(
                                websocket,
                                "tool_result",
                                {"tool_name": event.result.tool_name, "content": str(event.result.content)},
                            )
                        elif isinstance(event, FinalResultEvent):
                            await manager.send_event(
                                websocket,
                                "final_result",
                                {"content": str(event.output)},
                            )

                    result = stream.result()

                # Persist assistant response
                async with get_db_context() as db:
                    conv_service = get_conversation_service(db)
                    try:
                        await conv_service.add_message(
                            conversation_id,
                            MessageCreate(
                                role="assistant",
                                content=getattr(result, "output", ""),
                                model_name=getattr(assistant, "model_name", None),
                            ),
                        )
                    except Exception as exc:
                        logger.warning("Failed to persist assistant response: %s", exc)

                await manager.send_event(
                    websocket,
                    "complete",
                    {
                        "conversation_id": str(conversation_id),
                        "project_id": str(project_id),
                    },
                )

            except WebSocketDisconnect:
                logger.info("Client disconnected during project chat")
                break
            except Exception as exc:
                logger.exception("Error in project chat: %s", exc)
                await manager.send_event(websocket, "error", {"message": str(exc)})

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
{%- endif %}
{%- else %}
"""AI Agent routes - not configured."""
{%- endif %}
