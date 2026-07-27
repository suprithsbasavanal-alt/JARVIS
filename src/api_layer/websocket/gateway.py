"""WebSocket Streaming Gateway Handler."""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.ai_engine.contracts.provider import LLMRequest
from src.ai_engine.providers.factory import LLMProviderFactory
from src.shared.logger.logger import get_logger

logger = get_logger("api_layer.websocket")
ws_router = APIRouter()


@ws_router.websocket("/ws/v1/agent/stream")
async def websocket_agent_stream(websocket: WebSocket) -> None:
    """Real-time streaming WebSocket endpoint for token-by-token LLM output."""
    await websocket.accept()
    logger.info("WebSocket connection established.")

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            query = payload.get("prompt", "")

            if not query:
                await websocket.send_json({"error": "Prompt string is required."})
                continue

            provider = LLMProviderFactory.get_provider()
            request = LLMRequest(prompt=query)

            # Stream tokens to client
            async for token in provider.generate_stream(request):
                await websocket.send_json({"type": "token", "content": token})

            await websocket.send_json({"type": "done"})
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket streaming error: {e}")
        await websocket.close()
