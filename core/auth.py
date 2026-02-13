"""Twitter OAuth 2.0 PKCE authentication and session management."""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass, field

import httpx


@dataclass
class TwitterUser:
    """Authenticated Twitter user."""

    user_id: str
    handle: str
    name: str
    profile_image_url: str | None = None


@dataclass
class UserNetwork:
    """Cached follower/following ID sets for network matching."""

    following_ids: set[str] = field(default_factory=set)
    follower_ids: set[str] = field(default_factory=set)
    loaded: bool = False
    loading: bool = False


@dataclass
class UserSession:
    """An authenticated user session."""

    token: str
    user: TwitterUser
    access_token: str
    network: UserNetwork = field(default_factory=UserNetwork)
    created_at: float = field(default_factory=time.time)


# In-memory stores
_sessions: dict[str, UserSession] = {}
_oauth_states: dict[str, str] = {}  # state -> code_verifier


def generate_pkce_pair() -> tuple[str, str]:
    """Generate a PKCE code_verifier and code_challenge pair."""
    code_verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


def create_auth_url(client_id: str, redirect_uri: str) -> tuple[str, str]:
    """
    Create a Twitter OAuth 2.0 authorization URL with PKCE.

    Returns (auth_url, state) — the state maps to code_verifier internally.
    """
    code_verifier, code_challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(32)

    _oauth_states[state] = code_verifier

    params = httpx.QueryParams({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "tweet.read users.read follows.read offline.access",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
    url = f"https://twitter.com/i/oauth2/authorize?{params}"
    return url, state


async def exchange_code(
    code: str,
    state: str,
    client_id: str,
    client_secret: str | None,
    redirect_uri: str,
) -> dict:
    """
    Exchange an authorization code for tokens.

    Returns the token response dict from Twitter.
    Raises ValueError if state is invalid.
    """
    code_verifier = _oauth_states.pop(state, None)
    if not code_verifier:
        raise ValueError("Invalid or expired OAuth state")

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }

    # Use basic auth if client_secret is provided (confidential client)
    auth = None
    if client_secret:
        auth = (client_id, client_secret)
    else:
        data["client_id"] = client_id

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.twitter.com/2/oauth2/token",
            data=data,
            auth=auth,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()


async def fetch_twitter_user(access_token: str) -> TwitterUser:
    """Fetch the authenticated user's profile from Twitter API v2."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.twitter.com/2/users/me",
            params={"user.fields": "profile_image_url"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        data = response.json()["data"]
        return TwitterUser(
            user_id=data["id"],
            handle=data["username"],
            name=data["name"],
            profile_image_url=data.get("profile_image_url"),
        )


def create_session(user: TwitterUser, access_token: str) -> str:
    """Create a new session and return the session token."""
    token = secrets.token_urlsafe(32)
    _sessions[token] = UserSession(
        token=token,
        user=user,
        access_token=access_token,
    )
    return token


def get_session(token: str) -> UserSession | None:
    """Get a session by token."""
    return _sessions.get(token)


def delete_session(token: str) -> None:
    """Delete a session."""
    _sessions.pop(token, None)
