"""Exceptions for the telegram bot."""


class NoneTokenError(Exception):
    """Raised when the token is not set."""


class RequestError(Exception):
    """Raised when the request to the API failed."""
