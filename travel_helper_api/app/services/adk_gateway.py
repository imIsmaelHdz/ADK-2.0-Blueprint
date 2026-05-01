import json
import logging
from typing import Any, AsyncGenerator

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from travel_helper.agent import root_agent as travel_helper_agent
from travel_helper_api.app.core.config import APP_NAME

logger = logging.getLogger("travel_helper_api")


def _part_text(part: Any) -> str:
    return getattr(part, "text", "") or ""


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
        response_text_parts: list[str] = []

        async for event in self.runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_content,
        ):
            if event.content and event.content.parts:
                response_text_parts.extend(
                    text for text in (_part_text(part) for part in event.content.parts) if text
                )
            if event.is_final_response():
                break

        return "".join(response_text_parts).strip()

    async def stream_chat(self, user_id: str, session_id: str, message: str) -> AsyncGenerator[str, None]:
        await self.ensure_session(user_id, session_id)
        user_content = Content(role="user", parts=[Part(text=message)])

        async for event in self.runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_content,
        ):
            if event.content and event.content.parts:
                texts = [text for text in (_part_text(part) for part in event.content.parts) if text]
                for delta in texts:
                    yield f"data: {json.dumps({'type': 'delta', 'text': delta})}\n\n"

            if event.is_final_response():
                yield f"data: {json.dumps({'type': 'final', 'done': True})}\n\n"
                break
