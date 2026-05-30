from typing import Any

class DatumInContext:
    value: Any

class JSONPath:
    def find(self, data: Any) -> list[DatumInContext]: ...
