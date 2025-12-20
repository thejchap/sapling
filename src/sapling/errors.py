class SaplingError(Exception):
    """base exception for all sapling errors."""


class NotFoundError(SaplingError):
    """raised when document not found by fetch operation."""
