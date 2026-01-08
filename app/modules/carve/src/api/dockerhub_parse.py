"""
Docker Hub response parsing functions.
Handles parsing of indexed JSON responses.
"""

from typing import Dict, List, Any


def resolve_value(data: List, index: int) -> Any:
    """Resolve a value from the indexed JSON array, returning None if invalid."""
    if index < 0 or index >= len(data):
        return None
    return data[index]


def parse_result(data: List, result_index: int) -> Dict[str, Any]:
    """Parse a single result from Docker Hub's indexed JSON format."""
    result_obj = data[result_index]
    if not isinstance(result_obj, dict):
        return {}

    parsed = {}

    # Map known field keys to values
    # These indices match responses WITHOUT _routes parameter (correct API format)
    field_mappings = {
        "_30": "id",
        "_32": "name",
        "_33": "slug",
        "_34": "type",
        "_40": "created_at",
        "_42": "updated_at",
        "_44": "short_description",
        "_46": "badge",
        "_48": "star_count",
        "_50": "pull_count",
    }

    for key, field_name in field_mappings.items():
        if key in result_obj:
            value_index = result_obj[key]
            parsed[field_name] = resolve_value(data, value_index)

    # Handle publisher (object)
    # Index _36 matches responses WITHOUT _routes parameter
    if "_36" in result_obj:
        pub_index = result_obj["_36"]
        pub_obj = resolve_value(data, pub_index)
        if isinstance(pub_obj, dict) and "_32" in pub_obj:
            parsed["publisher"] = resolve_value(data, pub_obj["_32"])
        else:
            parsed["publisher"] = pub_obj

    # Handle operating_systems (array of objects)
    # Index _57 matches responses WITHOUT _routes parameter
    if "_57" in result_obj:
        os_arr_index = result_obj["_57"]
        os_arr = resolve_value(data, os_arr_index)
        if isinstance(os_arr, list):
            os_list = []
            for idx in os_arr:
                obj = resolve_value(data, idx)
                if isinstance(obj, dict) and "_32" in obj:
                    os_list.append(resolve_value(data, obj["_32"]))
            parsed["operating_systems"] = os_list
            parsed["os_count"] = len(os_list)

    # Handle architectures (array of objects)
    # Index _63 matches responses WITHOUT _routes parameter
    if "_63" in result_obj:
        arch_arr_index = result_obj["_63"]
        arch_arr = resolve_value(data, arch_arr_index)
        if isinstance(arch_arr, list):
            arch_list = []
            for idx in arch_arr:
                obj = resolve_value(data, idx)
                if isinstance(obj, dict) and "_32" in obj:
                    arch_list.append(resolve_value(data, obj["_32"]))
            parsed["architectures"] = arch_list
            parsed["architecture_count"] = len(arch_list)

    return parsed


def parse_response(data: List) -> Dict[str, Any]:
    """Parse full Docker Hub response, returning total, page_size, and results."""
    total = None
    results_indices = None
    page_size = 30

    for i, item in enumerate(data):
        if item == "total" and i + 1 < len(data):
            total = data[i + 1]
        elif item == "results" and i + 1 < len(data):
            results_indices = data[i + 1]
        elif item == "pageSize" and i + 1 < len(data):
            page_size = data[i + 1]

    results = []
    if results_indices:
        for idx in results_indices:
            parsed = parse_result(data, idx)
            if parsed:
                results.append(parsed)

    return {
        "total": total or 0,
        "page_size": page_size,
        "results": results,
    }
