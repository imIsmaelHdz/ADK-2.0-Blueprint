import json
import logging
import re
import time
from typing import Any, AsyncGenerator

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from travel_helper.agent import root_agent as travel_helper_agent
from travel_helper_api.app.core.config import APP_NAME

logger = logging.getLogger("travel_helper_api")

# Section headers that appear in the response format — used to emit section events.
_SECTION_HEADERS = [
    "SUMMARY",
    "ENTRY REQUIREMENTS",
    "CURRENCY",
    "WEATHER",
    "AIRPORT TO CITY CENTER",
    "TOURIST ATTRACTIONS",
]
_SECTION_RE = re.compile(
    r"^(" + "|".join(re.escape(h) for h in _SECTION_HEADERS) + r")\s*$",
    re.MULTILINE,
)

# Sub-agent names whose intermediate text we surface as "thinking" progress events.
_SUBAGENT_NAMES = {
    "weather_agent",
    "currency_agent",
    "google_search_agent",
    "rag_search_agent",
    "greeter_agent",
}


def _part_text(part: Any) -> str:
    return getattr(part, "text", "") or ""


def _agent_name(event: Any) -> str | None:
    """Return the author agent name from an ADK event, or None."""
    try:
        return event.author or None
    except AttributeError:
        return None


class AdkGatewayService:
    def __init__(self) -> None:
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            agent=travel_helper_agent,
            app_name=APP_NAME,
            session_service=self.session_service,
        )
        self._known_sessions: set[tuple[str, str]] = set()

    async def ensure_session(self, user_id: str, session_id: str) -> None:
        key = (user_id, session_id)
        if key in self._known_sessions:
            return
        await self.session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        self._known_sessions.add(key)

    async def run_chat(self, user_id: str, session_id: str, message: str) -> str:
        await self.ensure_session(user_id, session_id)
        user_content = Content(role="user", parts=[Part(text=message)])
        parts: list[str] = []

        async for event in self.runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_content,
        ):
            if event.content and event.content.parts:
                parts.extend(
                    t for t in (_part_text(p) for p in event.content.parts) if t
                )
            if event.is_final_response():
                break

        return "".join(parts).strip()

    async def stream_chat(
        self, user_id: str, session_id: str, message: str
    ) -> AsyncGenerator[str, None]:
        await self.ensure_session(user_id, session_id)
        user_content = Content(role="user", parts=[Part(text=message)])

        t0 = time.monotonic()
        last_author: str | None = None

        async for event in self.runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_content,
        ):
            if not (event.content and event.content.parts):
                if event.is_final_response():
                    yield f"data: {json.dumps({'type': 'final', 'done': True})}\n\n"
                continue

            texts = [t for t in (_part_text(p) for p in event.content.parts) if t]
            if not texts:
                if event.is_final_response():
                    yield f"data: {json.dumps({'type': 'final', 'done': True})}\n\n"
                continue

            author = _agent_name(event)
            is_final = event.is_final_response()
            elapsed = time.monotonic() - t0
            if author != last_author:
                logger.info("TIMING +%.1fs  author=%s  is_final=%s", elapsed, author, is_final)
                last_author = author

            if is_final:
                full_text = "".join(texts)
                yield f"data: {json.dumps({'type': 'delta', 'text': full_text})}\n\n"
                yield f"data: {json.dumps({'type': 'final', 'done': True})}\n\n"

            elif author in _SUBAGENT_NAMES:
                # Sub-agent completed — emit a lightweight progress ping so the UI can
                # show "gathering weather…" / "searching…" spinners without blocking.
                for delta in texts:
                    yield f"data: {json.dumps({'type': 'progress', 'agent': author, 'text': delta})}\n\n"

            else:
                # Intermediate root-agent tokens (e.g. "Gathering information…").
                for delta in texts:
                    yield f"data: {json.dumps({'type': 'delta', 'text': delta})}\n\n"
