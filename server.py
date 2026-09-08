import os
import secrets
import urllib.parse

import httpx
from starlette.applications import Starlette
from starlette.responses import RedirectResponse, HTMLResponse
from starlette.routing import Route

from mcp.server.fastmcp import FastMCP


# --------------------------------------------------
# Configuration
# --------------------------------------------------

LINKEDIN_CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET")

BASE_URL = "https://linkedin-growth-mcp.onrender.com"
REDIRECT_URI = f"{BASE_URL}/auth/linkedin/callback"

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"

# LinkedIn API version: YYYYMM
LINKEDIN_VERSION = "202609"


# --------------------------------------------------
# Temporary in-memory storage
# --------------------------------------------------

oauth_state = None
linkedin_access_token = None
linkedin_member_id = None


# --------------------------------------------------
# MCP
# --------------------------------------------------

mcp = FastMCP(
    "LinkedIn Growth MCP",
    instructions=(
        "A LinkedIn growth assistant that helps create and publish "
        "professional LinkedIn content. Never expose authentication "
        "credentials or access tokens."
    ),
)


@mcp.tool()
def linkedin_status() -> dict:
    """Check whether the LinkedIn Growth MCP server is running."""
    return {
        "status": "online",
        "service": "LinkedIn Growth MCP",
        "linkedin_connected": linkedin_access_token is not None,
    }


@mcp.tool()
def create_linkedin_draft(
    topic: str,
    goal: str = "generate clients",
) -> dict:
    """
    Create a basic LinkedIn post brief.

    This does not publish anything to LinkedIn.
    """
    return {
        "topic": topic,
        "goal": goal,
        "status": "draft_only",
        "message": (
            "Create a professional LinkedIn post around this topic. "
            "Focus on providing value and generating genuine business interest."
        ),
    }


@mcp.tool()
def linkedin_auth_status() -> dict:
    """Check whether LinkedIn OAuth has been completed."""
    return {
        "connected": linkedin_access_token is not None,
        "member_id": linkedin_member_id,
    }


@mcp.tool()
async def linkedin_create_post(text: str) -> dict:
    """
    Publish a text post to the authenticated LinkedIn personal profile.
    """
    if not linkedin_access_token or not linkedin_member_id:
        return {
            "success": False,
            "error": "LinkedIn is not connected. Open /auth/linkedin first.",
        }

    url = "https://api.linkedin.com/rest/posts"

    payload = {
        "author": f"urn:li:person:{linkedin_member_id}",
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    headers = {
        "Authorization": f"Bearer {linkedin_access_token}",
        "Linkedin-Version": LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url,
            json=payload,
            headers=headers,
        )

    if response.status_code in (200, 201):
        return {
            "success": True,
            "message": "LinkedIn post published successfully.",
            "post_id": response.headers.get("x-restli-id"),
        }

    return {
        "success": False,
        "status_code": response.status_code,
        "error": response.text[:1000],
    }


# --------------------------------------------------
# LinkedIn OAuth
# --------------------------------------------------

async def linkedin_login(request):
    global oauth_state

    oauth_state = secrets.token_urlsafe(32)

    params = {
        "response_type": "code",
        "client_id": LINKEDIN_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "state": oauth_state,
        "scope": "openid profile email w_member_social",
    }

    url = f"{LINKEDIN_AUTH_URL}?{urllib.parse.urlencode(params)}"

    return RedirectResponse(url)


async def linkedin_callback(request):
    global oauth_state
    global linkedin_access_token
    global linkedin_member_id

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        return HTMLResponse(
            f"<h2>LinkedIn authorization failed</h2><p>{error}</p>",
            status_code=400,
        )

    if not code:
        return HTMLResponse(
            "<h2>No authorization code received.</h2>",
            status_code=400,
        )

    if state != oauth_state:
        return HTMLResponse(
            "<h2>Invalid OAuth state.</h2>",
            status_code=400,
        )

    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET,
    }

    async with httpx.AsyncClient(timeout=30) as client:

        token_response = await client.post(
            LINKEDIN_TOKEN_URL,
            data=token_data,
        )

        if token_response.status_code != 200:
            return HTMLResponse(
                "<h2>Token exchange failed</h2>"
                f"<pre>{token_response.text[:1000]}</pre>",
                status_code=400,
            )

        token_json = token_response.json()

        linkedin_access_token = token_json.get("access_token")

        if not linkedin_access_token:
            return HTMLResponse(
                "<h2>No access token received.</h2>",
                status_code=400,
            )

        # Get LinkedIn member information
        userinfo_response = await client.get(
            LINKEDIN_USERINFO_URL,
            headers={
                "Authorization": f"Bearer {linkedin_access_token}",
            },
        )

        if userinfo_response.status_code != 200:
            return HTMLResponse(
                "<h2>Could not retrieve LinkedIn profile.</h2>"
                f"<pre>{userinfo_response.text[:1000]}</pre>",
                status_code=400,
            )

        userinfo = userinfo_response.json()

    linkedin_member_id = userinfo.get("sub")

    return HTMLResponse(
        """
        <html>
            <head>
                <title>LinkedIn Connected</title>
            </head>
            <body>
                <h1>✅ LinkedIn Connected Successfully</h1>
                <p>Your LinkedIn account has been connected to the MCP.</p>
                <p>You can close this page now.</p>
            </body>
        </html>
        """
    )


async def linkedin_home(request):
    return HTMLResponse(
        """
        <html>
            <head>
                <title>LinkedIn Growth MCP</title>
            </head>
            <body>
                <h1>LinkedIn Growth MCP</h1>
                <p>Server is running.</p>
                <p>
                    <a href="/auth/linkedin">
                        Connect LinkedIn
                    </a>
                </p>
            </body>
        </html>
        """
    )


# --------------------------------------------------
# Web application
# --------------------------------------------------

routes = [
    Route("/", linkedin_home),
    Route("/auth/linkedin", linkedin_login),
    Route("/auth/linkedin/callback", linkedin_callback),
]


app = Starlette(routes=routes)


# --------------------------------------------------
# Start MCP server
# --------------------------------------------------

if __name__ == "__main__":
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = int(os.environ.get("PORT", 8000))

    mcp.run(transport="streamable-http")
