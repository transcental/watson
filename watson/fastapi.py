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


async def send_to_slack(message: str, method: str, path: str, headers: Dict[str, Any], channel_id: Optional[str] = None):
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
                "channel": channel_id or config.slack.channel_id,
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
                error = result.get('error')
                logger.warning(f"Slack API error: {error}")
                return False, error
            else:
                logger.info("Message sent to Slack successfully")
                return True, None

    except Exception as e:
        error_msg = str(e)
        logger.warning(f"Error sending to Slack: {error_msg}")
        return False, error_msg


@app.middleware("http")
async def catch_all_middleware(request: Request, call_next):
    """Middleware to catch all requests and send to Slack"""

    # Get request details
    method = request.method
    path = str(request.url.path)
    headers = dict(request.headers)

    # Check for slack_id query parameter
    slack_channel_id = request.query_params.get("channel_id")

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
        res, error = await send_to_slack(body_text, method, path, headers, slack_channel_id)
    except Exception as e:
        res = False
        error = str(e)
        logger.warning(f"Failed to send to Slack: {e}")

    # Prepare response content with channel info
    response_content = {
        "status": "ok" if res else "warning",
        "method": method,
        "path": path
    }

    if slack_channel_id:
        response_content["slack_channel_override"] = slack_channel_id

    if res:
        response_content["message"] = "Request processed successfully and sent to Slack"
        if slack_channel_id:
            response_content["message"] += f" (custom channel: {slack_channel_id})"
    else:
        # Handle specific Slack API errors
        if error == "channel_not_found":
            channel = slack_channel_id or config.slack.channel_id
            response_content["message"] = f"Request processed, but Slack channel not found: {channel}"
        elif error == "not_in_channel":
            channel = slack_channel_id or config.slack.channel_id
            response_content["message"] = f"Request processed, but bot is not in Slack channel: {channel}"
        elif error == "channel_is_archived":
            channel = slack_channel_id or config.slack.channel_id
            response_content["message"] = f"Request processed, but Slack channel is archived: {channel}"
        elif error and "channel" in error.lower():
            channel = slack_channel_id or config.slack.channel_id
            response_content["message"] = f"Request processed, but Slack channel error ({error}): {channel}"
        else:
            response_content["message"] = "Request processed, but failed to send to Slack"
            if slack_channel_id:
                response_content["message"] += f" (attempted custom channel: {slack_channel_id})"
            if error:
                response_content["slack_error"] = error

    return JSONResponse(
        status_code=200,
        content=response_content
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
