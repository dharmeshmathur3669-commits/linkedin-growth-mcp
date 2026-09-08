
import os

from mcp.server.fastmcp import FastMCP


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
        "message": "MCP server is running successfully.",
    }


@mcp.tool()
def create_linkedin_draft(topic: str, goal: str = "generate clients") -> dict:
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


if __name__ == "__main__":
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = int(os.environ.get("PORT", 8000))

    # Render/remote MCP host
    mcp.settings.http_allowed_hosts = [
        "localhost",
        "127.0.0.1",
        "linkedin-growth-mcp.onrender.com",
    ]

    mcp.run(transport="streamable-http")
