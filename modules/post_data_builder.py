from dataclasses import MISSING, fields
from typing import Any, Dict, Callable, List, Optional

from modules.models import PostData

class PostDataBuilder:
    """Helper for constructing :class:`PostData` from minimal input."""

    #: Fields on ``PostData`` that do not have default values
    REQUIRED_FIELDS: List[str] = [
        f.name
        for f in fields(PostData)
        if f.default is MISSING and f.default_factory is MISSING
    ]

    def __init__(self, item_url: str, region: str) -> None:
        if not item_url:
            raise ValueError("'item_url' is required")
        if not region:
            raise ValueError("'region' is required")
        # only store required values provided at initialisation
        self._data: Dict[str, Any] = {"item_url": item_url, "region": region}

    def update_from_dict(self, values: Dict[str, Any]) -> "PostDataBuilder":
        for key, value in values.items():
            if key in PostData.__dataclass_fields__ and value is not None:
                self._data[key] = value
        return self

    def missing_required_fields(self) -> List[str]:
        """Return a list of required ``PostData`` fields that are not yet set."""
        return [f for f in self.REQUIRED_FIELDS if f not in self._data]

    def populate_missing(self, generator: Callable[[str], Any]) -> "PostDataBuilder":
        """Populate missing required fields using ``generator(field_name)``."""
        for field in self.missing_required_fields():
            self._data[field] = generator(field)
        return self

    def build(
        self, *, generator: Optional[Callable[[str], Any]] = None
    ) -> PostData:
        """Construct and return a ``PostData`` instance.

        If ``generator`` is provided, it will be called for each missing
        required field prior to building.
        """
        if generator is not None:
            self.populate_missing(generator)
        missing = self.missing_required_fields()
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        # fill optional fields with PostData defaults if absent
        for f in fields(PostData):
            if f.name not in self._data:
                if f.default is not MISSING:
                    self._data[f.name] = f.default
                elif f.default_factory is not MISSING:  # type: ignore[compare-types]
                    self._data[f.name] = f.default_factory()  # type: ignore[misc]

        return PostData(**self._data)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "PostDataBuilder":
        builder = cls(raw.get("item_url", ""), raw.get("region", ""))
        return builder.update_from_dict(raw)
