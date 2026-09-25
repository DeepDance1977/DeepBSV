class BSVRPCError(Exception):
    """Base exception for all BSV RPC client errors."""

    pass


class BSVRPCConnectionError(BSVRPCError):
    """Raised when connection to the BSV node fails."""

    pass


class BSVRPCAuthenticationError(BSVRPCError):
    """Raised on invalid RPC credentials (401 Unauthorized)."""

    pass


class BSVRPCResponseError(BSVRPCError):
    """Raised when the BSV node returns an explicit JSON-RPC error payload."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"RPC error {code}: {message}")
