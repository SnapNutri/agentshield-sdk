from contextvars import ContextVar, Token

from agentshield.session import AgentSession


_current_session: ContextVar[AgentSession | None] = ContextVar(
    "agentshield_current_session",
    default=None,
)


def set_current_session(
    session: AgentSession,
) -> Token[AgentSession | None]:
    """Set the session for the current execution context."""

    return _current_session.set(session)


def get_current_session() -> AgentSession:
    """Return the current AgentShield session."""

    session = _current_session.get()

    if session is None:
        raise RuntimeError(
            "No active AgentShield session"
        )

    return session


def current_session() -> AgentSession:
    """Return the currently active AgentShield session."""

    return get_current_session()


def reset_current_session(
    token: Token[AgentSession | None],
) -> None:
    """Restore the previous execution context."""

    _current_session.reset(token)