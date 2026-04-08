import json
from pathlib import Path
from typing import Any, Dict

from app.core.models.validation import ValidationResult


class RequirementValidator:
    def __init__(self, schema_path: Path) -> None:
        self.schema_path = schema_path
        self.schema = self._load_schema(schema_path)

    @staticmethod
    def _load_schema(schema_path: Path) -> Dict[str, Any]:
        with schema_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def validate(self, payload: Dict[str, Any]) -> ValidationResult:
        missing_fields = []
        errors = []

        required = self.schema.get("required", [])
        properties = self.schema.get("properties", {})
        allow_additional = self.schema.get("additionalProperties", True)

        for field in required:
            if field not in payload:
                missing_fields.append(field)

        if not allow_additional:
            for key in payload:
                if key not in properties:
                    errors.append("unexpected field: {0}".format(key))

        for field_name, field_schema in properties.items():
            if field_name not in payload:
                continue

            value = payload[field_name]
            expected_type = field_schema.get("type")

            if expected_type == "string":
                if not isinstance(value, str):
                    errors.append("{0}: must be string".format(field_name))
                    continue
                min_length = field_schema.get("minLength")
                if isinstance(min_length, int) and len(value.strip()) < min_length:
                    errors.append("{0}: minLength={1}".format(field_name, min_length))

            elif expected_type == "boolean":
                if not isinstance(value, bool):
                    errors.append("{0}: must be boolean".format(field_name))

            elif expected_type == "array":
                if not isinstance(value, list):
                    errors.append("{0}: must be array".format(field_name))
                    continue
                item_schema = field_schema.get("items", {})
                if item_schema.get("type") == "string":
                    for idx, item in enumerate(value):
                        if not isinstance(item, str):
                            errors.append("{0}[{1}]: must be string".format(field_name, idx))

            enum_values = field_schema.get("enum")
            if enum_values and value not in enum_values:
                errors.append(
                    "{0}: must be one of {1}".format(field_name, ", ".join(enum_values))
                )

        valid = len(missing_fields) == 0 and len(errors) == 0
        return ValidationResult(valid=valid, missing_fields=missing_fields, error_messages=errors)
