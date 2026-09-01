from collections.abc import Callable
from typing import Any

from .bootstrap_validator import BootstrapValidator
from .immutable_context import ExecutionContext


class ToolGateway:
    def __init__(
        self,
        context: ExecutionContext,
        validator: BootstrapValidator | None = None,
    ) -> None:
        self.context = context
        self.validator = validator or BootstrapValidator()
        self.handlers: dict[str, Callable[..., Any]] = {}

    def register_handler(self, name: str, handler: Callable[..., Any]) -> None:
        self.handlers[name] = handler

    def dispatch(
        self,
        tool_name: str,
        *args: Any,
        path: str | None = None,
        **kwargs: Any,
    ) -> Any:
        if tool_name not in self.handlers:
            raise ValueError(f"Tool '{tool_name}' not registered")

        self.validator.validate_git_identity()

        if path is not None:
            resolved_path = self.context.resolve_path(path)
            kwargs["path"] = resolved_path

        return self.handlers[tool_name](*args, **kwargs)
