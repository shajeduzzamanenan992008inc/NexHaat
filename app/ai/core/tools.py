"""Validated, allowlisted AI tools with scope checks and pinned caller identity."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re

from .logging import log_ai_event
from .permissions import has_ai_scope


_TOOL_NAME = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    fn: object
    scope: str
    parameters: dict
    mutation: bool = False


class ToolRegistry:
    """Register a closed set of typed application services for model function calls."""

    def __init__(self, *, max_calls=5):
        self._tools: dict[str, ToolSpec] = {}
        self.max_calls = max(1, min(int(max_calls), 20))

    def register(self, name, fn, *, scope, description="", parameters=None, mutation=False):
        if not isinstance(name, str) or not _TOOL_NAME.fullmatch(name):
            raise ValueError("Tool names must be short lowercase identifiers.")
        if name in self._tools or not callable(fn) or not scope:
            raise ValueError("Tool registration is invalid or duplicated.")
        schema = parameters or {"type": "object", "properties": {}, "additionalProperties": False}
        if schema.get("type") != "object" or not isinstance(schema.get("properties", {}), dict):
            raise ValueError("Tool input schema must be an object schema.")
        self._tools[name] = ToolSpec(
            name=name,
            description=str(description)[:500],
            fn=fn,
            scope=scope,
            parameters=schema,
            mutation=bool(mutation),
        )
        return fn

    @property
    def names(self):
        return tuple(self._tools)

    def provider_tools(self, *, scope):
        return [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters,
                },
            }
            for spec in self._tools.values()
            if has_ai_scope(scope, spec.scope)
        ]

    def validate(self, name, arguments, *, scope):
        spec = self._tools.get(name)
        if not spec or not has_ai_scope(scope, spec.scope):
            raise PermissionError("Tool is not available in this assistant scope.")
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be an object.")
        schema = spec.parameters
        properties = schema.get("properties", {})
        if schema.get("additionalProperties", False) is False:
            unexpected = set(arguments) - set(properties)
            if unexpected:
                raise ValueError("Tool arguments contain unsupported fields.")
        missing = set(schema.get("required", ())) - set(arguments)
        if missing:
            raise ValueError("A required tool argument is missing.")
        for key, value in arguments.items():
            rule = properties.get(key)
            if not rule:
                raise ValueError("Tool argument is unsupported.")
            _validate_value(value, rule)
        return spec

    def call(self, name, *, scope, user=None, arguments=None, allow_mutation=False, **kwargs):
        """Validate provider arguments and call a tool with the server's caller identity."""
        args = dict(arguments or {})
        args.update(kwargs)
        try:
            spec = self.validate(name, args, scope=scope)
            if spec.mutation and not allow_mutation:
                raise PermissionError("Mutation tools require a separate user confirmation flow.")
            # Caller identity is supplied here, never accepted from the model.
            result = spec.fn(user=user, **args)
            return {"ok": True, "result": result, "mutation": spec.mutation}
        except PermissionError:
            log_ai_event("tool_rejected", scope=scope, tool=name[:64], reason="scope")
            return {"ok": False, "error": "Tool is not available in this assistant scope."}
        except (TypeError, ValueError) as error:
            log_ai_event("tool_rejected", scope=scope, tool=name[:64], reason=type(error).__name__)
            return {"ok": False, "error": "Tool input could not be used."}
        except Exception as error:  # provider tools must not leak tracebacks or private data
            log_ai_event("tool_failed", scope=scope, tool=name[:64], reason=type(error).__name__)
            return {"ok": False, "error": "Marketplace data is temporarily unavailable."}


def parse_tool_arguments(value):
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or len(value) > 8000:
        raise ValueError("Tool arguments are invalid.")
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("Tool arguments must be an object.")
    return parsed


def _matches_schema_type(value, expected):
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        from decimal import Decimal

        return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return False


def _validate_value(value, rule):
    if not _matches_schema_type(value, rule.get("type")):
        raise ValueError("A tool argument has the wrong type.")
    if "enum" in rule and value not in rule["enum"]:
        raise ValueError("A tool argument is outside the allowed values.")
    if isinstance(value, str):
        if len(value) > int(rule.get("maxLength", 400)) or len(value) < int(rule.get("minLength", 0)):
            raise ValueError("A tool argument has an invalid length.")
    if isinstance(value, list):
        if len(value) > int(rule.get("maxItems", 10)) or len(value) < int(rule.get("minItems", 0)):
            raise ValueError("A tool argument has an invalid item count.")
        if rule.get("items"):
            for item in value:
                _validate_value(item, rule["items"])
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        import math

        from decimal import Decimal

        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("A numeric tool argument is not finite.")
        if isinstance(value, Decimal) and not value.is_finite():
            raise ValueError("A numeric tool argument is not finite.")
        if value < rule.get("minimum", value) or value > rule.get("maximum", value):
            raise ValueError("A numeric tool argument is outside its allowed range.")
