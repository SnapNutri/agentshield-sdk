class AgentShieldError(Exception):
    """Base exception for AgentShield."""


class BudgetExceededError(AgentShieldError):
    """Raised when an agent reaches or exceeds its configured budget."""


class DurationLimitExceededError(AgentShieldError):
    """Raised when an agent exceeds its configured duration limit."""


class StepLimitExceededError(AgentShieldError):
    """Raised when a session exceeds its configured step limit."""


class LoopDetectedError(AgentShieldError):
    """Raised when AgentShield detects a repeating agent loop."""


class ToolRepetitionError(AgentShieldError):
    """Raised when the same tool is called too many times consecutively."""


class StagnationDetectedError(AgentShieldError):
    """Raised when an agent shows sustained lack of meaningful progress."""