"""Strict, bounded JSON and the JSON Schema subset used by setup contracts.

No remote references or executable expressions. Diagnostics never contain input
values. This is deliberately not a general-purpose JSON Schema implementation.
"""
import json
import re


class Invalid(ValueError):
    def __init__(self, code, pointer=""):
        self.code, self.pointer = code, pointer
        super().__init__(code)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Invalid("duplicate_key")
        result[key] = value
    return result


def _reject_number(_value):
    raise Invalid("integer_required")


def _safe_tree(value, depth=0, *, ascii_keys=True):
    if depth > 32:
        raise Invalid("nesting_limit")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or (ascii_keys and not key.isascii()):
                raise Invalid("invalid_key")
            _safe_tree(key, depth + 1, ascii_keys=ascii_keys)
            _safe_tree(child, depth + 1, ascii_keys=ascii_keys)
    elif isinstance(value, list):
        for child in value:
            _safe_tree(child, depth + 1, ascii_keys=ascii_keys)
    elif isinstance(value, str):
        if any(0xD800 <= ord(c) <= 0xDFFF for c in value) or "\x00" in value:
            raise Invalid("invalid_string")
    elif type(value) is float:
        raise Invalid("integer_required")
    elif type(value) is int:
        if abs(value) > 9007199254740991:
            raise Invalid("integer_range")
    elif value is not None and type(value) is not bool:
        raise Invalid("invalid_value")


def loads(data, limit=1024 * 1024, *, ascii_keys=True, object_field=None):
    """Validate a strict document or one object field embedded in ordinary JSON."""
    try:
        if isinstance(data, str):
            data = data.encode("utf-8", errors="strict")
        if len(data) > limit:
            raise Invalid("size_limit")
        value = json.loads(data.decode("utf-8", errors="strict"), object_pairs_hook=_pairs,
                           parse_constant=_reject_number, parse_float=float if object_field is not None else _reject_number)
        if object_field is not None:
            if not isinstance(value, dict) or not isinstance(value.get(object_field), dict):
                raise Invalid("object_field_required")
            value = value[object_field]
        _safe_tree(value, ascii_keys=ascii_keys)
        return value
    except Invalid:
        raise
    except (ValueError, UnicodeError, RecursionError, TypeError):
        raise Invalid("invalid_json") from None


def canonical(value):
    _safe_tree(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


KEYWORDS = {"$schema", "$id", "$defs", "$ref", "title", "description", "type", "const", "enum",
            "properties", "required", "additionalProperties", "propertyNames", "maxProperties",
            "items", "minItems", "maxItems", "uniqueItems", "minLength", "maxLength", "pattern",
            "minimum", "maximum", "oneOf"}


def check_schema(schema, root=None, visited=None):
    root = root or schema
    visited = set() if visited is None else visited
    if isinstance(schema, bool):
        return
    if not isinstance(schema, dict) or set(schema) - KEYWORDS:
        raise Invalid("unsupported_schema")
    if id(schema) in visited:
        return
    visited.add(id(schema))
    if "$ref" in schema:
        ref = schema["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/$defs/") or ref[8:] not in root.get("$defs", {}):
            raise Invalid("unsupported_reference")
        check_schema(root["$defs"][ref[8:]], root, visited)
    for key in ("properties", "$defs"):
        for child in schema.get(key, {}).values():
            check_schema(child, root, visited)
    for key in ("additionalProperties", "items", "propertyNames"):
        if key in schema:
            check_schema(schema[key], root, visited)
    for child in schema.get("oneOf", []):
        check_schema(child, root, visited)


def validate(value, schema, *, partial=False):
    """Return safe pointer/code diagnostics; partial only relaxes missing fields."""
    check_schema(schema)
    errors = []

    def visit(v, s, pointer, out):
        if len(out) >= 128:
            return
        def bad(code):
            out.append({"pointer": pointer, "code": code})
        if s is False:
            bad("unknown_field")
            return
        if s is True:
            return
        if "$ref" in s:
            visit(v, schema["$defs"][s["$ref"][8:]], pointer, out)
        if "oneOf" in s:
            matches = 0
            for branch in s["oneOf"]:
                branch_errors = []
                visit(v, branch, pointer, branch_errors)
                matches += not branch_errors
            if matches != 1:
                bad("variant")
                return
        types = {"object": isinstance(v, dict), "array": isinstance(v, list),
                 "string": isinstance(v, str), "integer": type(v) is int,
                 "boolean": type(v) is bool, "null": v is None}
        if "type" in s and not types.get(s["type"], False):
            bad("type")
            return
        if "const" in s and (type(v) is not type(s["const"]) or v != s["const"]):
            bad("const")
        if "enum" in s and not any(type(v) is type(x) and v == x for x in s["enum"]):
            bad("enum")
        if isinstance(v, dict):
            props = s.get("properties", {})
            if not partial:
                for key in s.get("required", []):
                    if key not in v:
                        out.append({"pointer": pointer + "/" + key, "code": "required"})
            if len(v) > s.get("maxProperties", 1000000):
                bad("properties_limit")
            for key, child in v.items():
                # Unknown names may themselves contain secrets: never echo them.
                child_pointer = pointer + "/" + (key if key in props else "*")
                if "propertyNames" in s:
                    visit(key, s["propertyNames"], pointer + "/*", out)
                visit(child, props.get(key, s.get("additionalProperties", True)), child_pointer, out)
        if isinstance(v, list):
            if not s.get("minItems", 0) <= len(v) <= s.get("maxItems", 1000000):
                bad("array_size")
            if s.get("uniqueItems") and len({canonical(x) for x in v}) != len(v):
                bad("duplicate_item")
            for index, child in enumerate(v):
                if "items" in s:
                    visit(child, s["items"], pointer + "/" + str(index), out)
        if isinstance(v, str):
            if not s.get("minLength", 0) <= len(v) <= s.get("maxLength", 10000000):
                bad("string_size")
            if "pattern" in s and re.search(s["pattern"], v) is None:
                bad("pattern")
        if type(v) is int and not s.get("minimum", -9007199254740991) <= v <= s.get("maximum", 9007199254740991):
            bad("number_range")
    visit(value, schema, "", errors)
    return errors[:128]
