"""
Schema validator for knowledge base data files.

Validates KB data against JSON Schema definitions to ensure
data integrity before loading into the engine.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

try:
    import jsonschema
    _HAS_JSONSCHEMA = True
except ImportError:
    _HAS_JSONSCHEMA = False

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"


class SchemaValidator:
    """Validates KB data files against their JSON schemas."""

    @staticmethod
    def _load_schema(name: str) -> Dict[str, Any]:
        path = SCHEMA_DIR / name
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def validate_banks(cls, banks: list) -> List[str]:
        """
        Validate a list of bank product dicts.
        Returns list of error strings (empty = all valid).
        """
        schema = cls._load_schema("bank_product.schema.json")
        if not schema or not _HAS_JSONSCHEMA:
            return []
        errors = []
        for i, bank in enumerate(banks):
            try:
                jsonschema.validate(bank, schema)
            except jsonschema.ValidationError as e:
                bid = bank.get("id", f"index-{i}")
                errors.append(f"Bank[{i}] ({bid}): {e.message}")
        return errors

    @classmethod
    def validate_industry_acceptance(cls, rows: list) -> List[str]:
        """Validate industry acceptance data."""
        schema = cls._load_schema("industry_acceptance.schema.json")
        if not schema or not _HAS_JSONSCHEMA:
            return []
        errors = []
        for i, row in enumerate(rows):
            try:
                jsonschema.validate(row, schema)
            except jsonschema.ValidationError as e:
                errors.append(f"Industry[{i}]: {e.message}")
        return errors

    @classmethod
    def validate_tax_scoring(cls, mapping: dict) -> List[str]:
        """Validate tax scoring dict."""
        schema = cls._load_schema("tax_scoring.schema.json")
        if not schema or not _HAS_JSONSCHEMA:
            return []
        errors = []
        try:
            jsonschema.validate(mapping, schema)
        except jsonschema.ValidationError as e:
            errors.append(f"Tax scoring: {e.message}")
        return errors

    @classmethod
    def check_schema_dir(cls) -> Dict[str, bool]:
        """Check which schema files exist."""
        expected = [
            "bank_product.schema.json",
            "industry_acceptance.schema.json",
            "tax_scoring.schema.json",
        ]
        return {
            name: (SCHEMA_DIR / name).exists()
            for name in expected
        }


# Simple CSV validation (no jsonschema needed)
def validate_csv_columns(path: str, expected_columns: List[str]) -> List[str]:
    """
    Validate that a CSV file has the expected columns.
    Returns list of errors (empty = valid).
    """
    import pandas as pd
    errors = []
    try:
        df = pd.read_csv(path, encoding="utf-8", nrows=1)
        missing = [c for c in expected_columns if c not in df.columns]
        if missing:
            errors.append(
                f"{Path(path).name}: missing columns: {missing}"
            )
    except Exception as e:
        errors.append(f"{Path(path).name}: {e}")
    return errors
