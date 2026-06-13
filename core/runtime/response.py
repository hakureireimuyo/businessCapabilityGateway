"""Runtime: ActionResult — uniform API response wrapper"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ActionResult:
    """Uniform return format for all execution results."""
    success: bool
    data: dict | None = None
    message: str = ""
    error: dict | None = None

    @classmethod
    def ok(cls, data: dict | None = None, message: str = "") -> "ActionResult":
        return cls(success=True, data=data or {}, message=message)

    @classmethod
    def fail(cls, code: str, message: str) -> "ActionResult":
        return cls(
            success=False,
            error={"code": code, "message": message},
            message=message,
        )

    def to_dict(self) -> dict:
        result: dict[str, Any] = {"success": self.success}
        if self.success:
            result["data"] = self.data
            result["message"] = self.message
        else:
            result["error"] = self.error
        return result
