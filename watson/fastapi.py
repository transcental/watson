import logging
import json
import httpx
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from watson.config import config

app = FastAPI()



app = FastAPI(title="Watson", description="Returns 200 to all requests and forwards data to Slack")

logger = logging.getLogger(__name__)


class SlackMessage(BaseModel):
    text: str
    channel: Optional[str] = None
    key: str


async def send_to_slack(message: str, method: str, path: str, headers: Dict[str, Any]):
    """Send a message to Slack using webhook or bot token"""

    # format message as json if it is json
    if isinstance(message, dict):
        message = json.dumps(message, indent=2)
    formatted_message = f"""
🔔 *Watson Request*
• Method: `{method}`
• Path: `{path}`
• Message: ```{message}```
• Headers: ```{json.dumps(dict(headers), indent=2)}```
    """.strip()

    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "channel": config.slack.channel_id,
                "text": formatted_message,
                "parse": "mrkdwn"
            }
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                json=payload,
                headers={
                    "Authorization": f"Bearer {config.slack.bot_token}",
                    "Content-Type": "application/json"
                }
            )
            result = response.json()
            if not result.get("ok"):
                print(f"Slack API error: {result.get('error')}")
                return False
            else:
                print("Message sent to Slack successfully")
                return True

    except Exception as e:
        print(f"Error sending to Slack: {str(e)}")
        return False


@app.middleware("http")
async def catch_all_middleware(request: Request, call_next):
    """Middleware to catch all requests and send to Slack"""

    # Get request details
    method = request.method
    path = str(request.url.path)
    headers = dict(request.headers)

    # Try to get request body for logging
    try:
        body = await request.body()
        if body:
            try:
                body_text = body.decode('utf-8')
                if len(body_text) > 35000:  # Truncate long bodies
                    body_text = body_text[:35000] + "... [truncated]"
            except:
                body_text = "[binary data]"
        else:
            body_text = "[empty body]"
    except:
        body_text = "[could not read body]"

    try:
        res = await send_to_slack(body_text, method, path, headers)
    except Exception as e:
        res = False
        print(f"Failed to send to Slack: {e}")

    if not res:
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "message": "Request processed successfully",
                "method": method,
                "path": path
            }
        )
    else:
        # If sending to Slack failed, still return 500
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Request processed, but failed to send to Slack",
                "method": method,
                "path": path
            }
        )


@app.get("/")
async def root():
    """Root endpoint - handled by middleware but documented here"""
    pass


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    pass


@app.post("/slack/test")
async def test_slack(message: SlackMessage):
    """Test endpoint to manually send a message to Slack"""
    if message.key != config.secret_key:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid key"}
        )
    await send_to_slack(
        message.text,
        "POST",
        "/slack/test",
        {"test": "manual message"}
    )
    return {"status": "Message sent to Slack"}


# Catch-all route for any other endpoints
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def catch_all(path: str, request: Request):
    """Catch-all route - handled by middleware"""
    pass
