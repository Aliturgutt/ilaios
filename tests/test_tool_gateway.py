import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from src.core.bootstrap_validator import BootstrapValidator, ContextError
from src.core.immutable_context import ExecutionContext
from src.core.tool_gateway import ToolGateway


class TestToolGateway(unittest.TestCase):
    def setUp(self) -> None:
        self.context = ExecutionContext(
            Path.cwd(),
            "main",
            "a1b2c3",
            "https://github.com/user/repo.git",
        )
        self.validator = BootstrapValidator()
        self.gateway = ToolGateway(self.context, self.validator)

    def test_toolgateway_constructs_correctly(self) -> None:
        """ToolGateway(context, validator) constructs correctly."""
        self.assertIs(self.gateway.context, self.context)
        self.assertIs(self.gateway.validator, self.validator)
        self.assertEqual(self.gateway.handlers, {})

    def test_registered_handler_executes(self) -> None:
        """Registered handler executes."""
        called: list[bool] = []

        def handler(*args: Any, **kwargs: Any) -> str:
            called.append(True)
            return "result"

        self.gateway.register_handler("test", handler)
        result = self.gateway.dispatch("test")
        self.assertTrue(called)
        self.assertEqual(result, "result")

    def test_unknown_handler_raises_valueerror(self) -> None:
        """Unknown handler raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            self.gateway.dispatch("unknown")
        self.assertEqual(str(cm.exception), "Tool 'unknown' not registered")

    def test_unknown_handler_does_not_trigger_git_validation(self) -> None:
        """Unknown handler does not trigger Git validation."""
        mock_validator = MagicMock()
        mock_validator.validate_git_identity.side_effect = Exception(
            "Git validation should not be called"
        )
        gateway = ToolGateway(self.context, mock_validator)

        with self.assertRaises(ValueError):
            gateway.dispatch("unknown")

        mock_validator.validate_git_identity.assert_not_called()

    def test_git_validation_occurs_before_handler_execution(self) -> None:
        """Git validation occurs before handler execution."""
        mock_validator = MagicMock()
        gateway = ToolGateway(self.context, mock_validator)
        handler = MagicMock(return_value="result")
        gateway.register_handler("test", handler)

        result = gateway.dispatch("test")

        mock_validator.validate_git_identity.assert_called_once()
        handler.assert_called_once()
        self.assertEqual(result, "result")

    def test_valid_explicit_path_is_resolved_and_passed_to_handler(self) -> None:
        """Valid explicit path is resolved and passed to handler."""
        captured_path: list[Path] = []

        def handler(*args: Any, path: Path | None = None, **kwargs: Any) -> str:
            if path is not None:
                captured_path.append(path)
            return "done"

        gateway = ToolGateway(self.context, self.validator)
        gateway.register_handler("test", handler)

        result = gateway.dispatch("test", path="subdir/file.txt")

        self.assertEqual(result, "done")
        self.assertEqual(len(captured_path), 1)
        expected_path = self.context.resolve_path("subdir/file.txt")
        self.assertEqual(captured_path[0], expected_path)

    def test_escaping_path_error_prevents_handler_execution(self) -> None:
        """Escaping path error prevents handler execution."""
        handler = MagicMock()
        gateway = ToolGateway(self.context, self.validator)
        gateway.register_handler("test", handler)

        with self.assertRaises(ContextError):
            gateway.dispatch("test", path="../etc/passwd")

        handler.assert_not_called()

    def test_git_validation_failure_prevents_path_resolution_and_handler_execution(
        self,
    ) -> None:
        """Git validation failure prevents path resolution and handler execution."""
        mock_validator = MagicMock()
        mock_validator.validate_git_identity.side_effect = RuntimeError(
            "Git validation failed"
        )
        gateway = ToolGateway(self.context, mock_validator)
        handler = MagicMock()
        gateway.register_handler("test", handler)

        with self.assertRaises(RuntimeError):
            gateway.dispatch("test", path="some/path")

        handler.assert_not_called()

    def test_normal_string_arguments_not_treated_as_paths(self) -> None:
        """Normal string arguments are not treated as paths."""
        captured_kwargs: dict[str, Any] = {}

        def handler(*args: Any, **kwargs: Any) -> str:
            captured_kwargs.update(kwargs)
            return str(kwargs.get("value", "no value"))

        gateway = ToolGateway(self.context, self.validator)
        gateway.register_handler("test", handler)

        result = gateway.dispatch("test", "normal_string", value="test_value")

        self.assertEqual(result, "test_value")
        self.assertNotIn("path", captured_kwargs)

    def test_positional_and_keyword_arguments_pass_unchanged(self) -> None:
        """Positional and keyword arguments pass unchanged."""
        captured_args: list[Any] = []
        captured_kwargs: dict[str, Any] = {}

        def handler(*args: Any, **kwargs: Any) -> tuple[tuple[Any, ...], dict[str, Any]]:
            captured_args.extend(args)
            captured_kwargs.update(kwargs)
            return args, kwargs

        gateway = ToolGateway(self.context, self.validator)
        gateway.register_handler("test", handler)

        gateway.dispatch("test", "arg1", "arg2", key1="val1", key2="val2")

        self.assertEqual(captured_args, ["arg1", "arg2"])
        self.assertEqual(captured_kwargs, {"key1": "val1", "key2": "val2"})


if __name__ == "__main__":
    unittest.main()
