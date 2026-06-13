"""SDK: GraphError — errors raised during SDK-side graph construction"""


class GraphError(Exception):
    """Base error for SDK-side graph construction issues.

    Raised when the SDK detects problems during graph construction:
      - Unknown node name (plugin misconfiguration)
      - Parameter validation failure
      - Missing required parameters
      - Type mismatch in artifact references (detected early)
    """
    pass
