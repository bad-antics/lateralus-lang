from typing import Any, Callable, Dict, List, Optional, Union

class Query:
    def __init__(self) -> None:
        self._data: List[Dict[str, Any]] = []
        self._joins: List[Any] = []

    def from_(self, data: List[Dict[str, Any]]) -> "Query":
        self._data = list(data)
        return self

    def join(
        self,
        right: List[Dict[str, Any]],
        *args: Any,
        kind: str = "inner",
    ) -> "Query":
        if len(args) == 1 and callable(args[0]):
            self._joins.append(LambdaJoinClause(right, args[0], kind))
        elif len(args) == 2 and isinstance(args[0], str) and isinstance(args[1], str):
            self._joins.append(FieldJoinClause(right, args[0], args[1], kind))
        else:
            raise ValueError("Invalid join arguments. Expected callable predicate or two field names.")
        return self

    def execute(self) -> List[Dict[str, Any]]:
        result = list(self._data)
        for join_clause in self._joins:
            result = join_clause.apply(result)
        return result


class FieldJoinClause:
    def __init__(self, right: List[Dict[str, Any]], left_field: str, right_field: str, kind: str) -> str:
        self.right = right
        self.left_field = left_field
        self.right_field = right_field
        self.kind = kind

    def apply(self, left_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return _apply_field_join(left_data, self.right, self.left_field, self.right_field, self.kind)


class LambdaJoinClause:
    def __init__(self, right: List[Dict[str, Any]], predicate: Callable[..., bool], kind: str) -> None:
        self.right = right
        self.predicate = predicate
        self.kind = kind

    def apply(self, left_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return _apply_lambda_join(left_data, self.right, self.predicate, self.kind)


def _apply_field_join(
    left_data: List[Dict[str, Any]],
    right_data: List[Dict[str, Any]],
    left_field: str,
    right_field: str,
    kind: str,
) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    matched_right_indices = set()

    for left_row in left_data:
        matched = False
        l_val = left_row.get(left_field)
        for r_idx, right_row in enumerate(right_data):
            r_val = right_row.get(right_field)
            if l_val is not None and l_val == r_val:
                matched = True
                matched_right_indices.add(r_idx)
                combined = {**left_row, **right_row}
                result.append(combined)
        
        if not matched and kind == "left":
            dummy_right = {k: None for k in (right_data[0].keys() if right_data else [])}
            combined = {**left_row, **dummy_right}
            result.append(combined)

    if kind == "right":
        for r_idx, right_row in enumerate(right_data):
            if r_idx not in matched_right_indices:
                dummy_left = {k: None for k in (left_data[0].keys() if left_data else [])}
                combined = {**dummy_left, **right_row}
                result.append(combined)

    return result


def _apply_lambda_join(
    left_data: List[Dict[str, Any]],
    right_data: List[Dict[str, Any]],
    predicate: Callable[..., bool],
    kind: str,
) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    matched_right_indices = set()

    for left_row in left_data:
        matched = False
        for r_idx, right_row in enumerate(right_data):
            if predicate(left_row, right_row):
                matched = True
                matched_right_indices.add(r_idx)
                combined = {**left_row, **right_row}
                result.append(combined)

        if not matched and kind == "left":
            dummy_right = {k: None for k in (right_data[0].keys() if right_data else [])}
            combined = {**left_row, **dummy_right}
            result.append(combined)

    if kind == "right":
        for r_idx, right_row in enumerate(right_data):
            if r_idx not in matched_right_indices:
                dummy_left = {k: None for k in (left_data[0].keys() if left_data else [])}
                combined = {**dummy_left, **right_row}
                result.append(combined)

    return result