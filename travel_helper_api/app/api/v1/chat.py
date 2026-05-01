import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from travel_helper_api.app.schemas.chat import ChatRequest, ChatResponse
from travel_helper_api.app.services.adk_gateway import AdkGatewayService

logger = logging.getLogger("travel_helper_api")
router = APIRouter(prefix="/v1", tags=["chat"])
gateway_service = AdkGatewayService()


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    try:
        response = await gateway_service.run_chat(
            user_id=payload.user_id,
            session_id=payload.session_id,
            message=payload.message,
        )
    except Exception as exc:
        logger.exception("Failed to process /v1/chat request")
        raise HTTPException(status_code=500, detail="Agent execution failed") from exc

    return ChatResponse(
        user_id=payload.user_id,
        session_id=payload.session_id,
        response=response,
    )


@router.post("/chat/stream")
async def chat_stream(payload: ChatRequest) -> StreamingResponse:
    async def event_generator():
        try:
            async for event_payload in gateway_service.stream_chat(
                user_id=payload.user_id,
                session_id=payload.session_id,
                message=payload.message,
            ):
                yield event_payload
        except Exception:
            logger.exception("Failed to process /v1/chat/stream request")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Agent execution failed'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
