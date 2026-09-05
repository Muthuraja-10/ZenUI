from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from app.llm.llm_service import LLMService


# ============================================================
# RESULT NORMALIZER
# ============================================================


class ResultNormalizer:
    """
    Converts heterogeneous tool/resource output into one stable
    ZenUI data contract.

    The normalizer does NOT decide the UI.

    It only produces reliable structured data for the intelligence
    and UI-planning layers.

    Supported input styles include:

        {
            "records": [...]
        }

        {
            "data": [...]
        }

        {
            "data": {
                "items": [...]
            }
        }

        {
            "results": [...]
        }

        {
            "value": 42
        }

        {
            "metrics": {...}
        }

        arbitrary nested dictionaries/lists

    Output contract:

        {
            "source": str,
            "query": str,
            "summary": str,
            "metrics": dict,
            "metric_cards": list,
            "records": list,
            "collections": list,
            "sources": list,
            "metadata": dict
        }

    No domain-specific business logic belongs here.
    """

    def __init__(self) -> None:
        self.llm = LLMService()

    # ========================================================
    # PUBLIC
    # ========================================================

    async def normalize(
        self,
        *,
        user_prompt: str,
        intent: Any,
        tool_name: str,
        tool_data: Any,
    ) -> dict[str, Any]:

        source = self._clean_string(
            tool_name
        ) or "unknown"

        # ----------------------------------------------------
        # Invalid / empty result
        # ----------------------------------------------------

        if tool_data is None:
            return self._empty_result(
                source=source,
            )

        # ----------------------------------------------------
        # Preserve already-normalized data
        # ----------------------------------------------------

        if self._looks_normalized(
            tool_data
        ):
            return self._sanitize_normalized(
                source=source,
                data=tool_data,
            )

        # ----------------------------------------------------
        # Structured result
        # ----------------------------------------------------

        if isinstance(
            tool_data,
            Mapping,
        ):

            data = dict(
                tool_data
            )

            if not data:
                return self._empty_result(
                    source=source,
                )

            # ------------------------------------------------
            # External/search-like data
            # ------------------------------------------------

            if self._looks_like_search_result(
                data
            ):

                return await self._normalize_search(
                    user_prompt=user_prompt,
                    intent=intent,
                    tool_name=source,
                    tool_data=data,
                )

            # ------------------------------------------------
            # Generic structured data
            # ------------------------------------------------

            return self._normalize_structured(
                source=source,
                data=data,
            )

        # ----------------------------------------------------
        # Top-level list
        # ----------------------------------------------------

        if isinstance(
            tool_data,
            list,
        ):

            return self._normalize_list(
                source=source,
                data=tool_data,
            )

        # ----------------------------------------------------
        # Scalar
        # ----------------------------------------------------

        return self._normalize_scalar(
            source=source,
            value=tool_data,
        )

    # ========================================================
    # EMPTY RESULT
    # ========================================================

    @staticmethod
    def _empty_result(
        *,
        source: str,
    ) -> dict[str, Any]:

        return {
            "source": source,
            "query": "",
            "summary": "",
            "metrics": {},
            "metric_cards": [],
            "records": [],
            "collections": [],
            "sources": [],
            "metadata": {
                "normalized": True,
                "empty": True,
            },
        }

    # ========================================================
    # ALREADY NORMALIZED
    # ========================================================

    @staticmethod
    def _looks_normalized(
        data: Any,
    ) -> bool:

        if not isinstance(
            data,
            Mapping,
        ):
            return False

        required = {
            "summary",
            "metrics",
            "records",
            "sources",
        }

        return required.issubset(
            data.keys()
        )

    def _sanitize_normalized(
        self,
        *,
        source: str,
        data: Mapping[str, Any],
    ) -> dict[str, Any]:

        result = dict(
            data
        )

        return {
            "source": self._clean_string(
                result.get(
                    "source"
                )
            ) or source,

            "query": self._clean_string(
                result.get(
                    "query"
                )
            ),

            "summary": self._clean_string(
                result.get(
                    "summary"
                )
            ),

            "metrics": self._sanitize_metrics(
                result.get(
                    "metrics"
                )
            ),

            "metric_cards": self._sanitize_metric_cards(
                result.get(
                    "metric_cards"
                )
            ),

            "records": self._sanitize_records(
                result.get(
                    "records"
                )
            ),

            "collections": self._sanitize_collections(
                result.get(
                    "collections"
                )
            ),

            "sources": self._sanitize_sources(
                result.get(
                    "sources"
                )
            ),

            "metadata": self._sanitize_metadata(
                result.get(
                    "metadata"
                )
            ),
        }

    # ========================================================
    # STRUCTURED DATA
    # ========================================================

    def _normalize_structured(
        self,
        *,
        source: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:

        summary = self._extract_summary(
            data
        )

        metrics = self._extract_metrics(
            data
        )

        records = self._extract_records(
            data
        )

        collections = self._extract_collections(
            data
        )

        sources = self._extract_sources(
            data
        )

        metric_cards = self._build_metric_cards(
            metrics
        )

        metadata = self._extract_metadata(
            data
        )

        query = self._clean_string(
            data.get(
                "query"
            )
        )

        return {
            "source": source,
            "query": query,
            "summary": summary,
            "metrics": metrics,
            "metric_cards": metric_cards,
            "records": records,
            "collections": collections,
            "sources": sources,
            "metadata": {
                **metadata,
                "normalized": True,
                "record_count": len(
                    records
                ),
                "collection_count": len(
                    collections
                ),
            },
        }

    # ========================================================
    # LIST
    # ========================================================

    def _normalize_list(
        self,
        *,
        source: str,
        data: list[Any],
    ) -> dict[str, Any]:

        records: list[dict[str, Any]] = []
        collections: list[dict[str, Any]] = []

        for index, item in enumerate(
            data
        ):

            if isinstance(
                item,
                Mapping,
            ):

                record = self._clean_record(
                    item
                )

                if record:
                    records.append(
                        record
                    )

                continue

            collections.append(
                {
                    "index": index,
                    "value": item,
                }
            )

        return {
            "source": source,
            "query": "",
            "summary": "",
            "metrics": {},
            "metric_cards": [],
            "records": records,
            "collections": collections,
            "sources": [],
            "metadata": {
                "normalized": True,
                "record_count": len(
                    records
                ),
                "collection_count": len(
                    collections
                ),
            },
        }

    # ========================================================
    # SCALAR
    # ========================================================

    def _normalize_scalar(
        self,
        *,
        source: str,
        value: Any,
    ) -> dict[str, Any]:

        return {
            "source": source,
            "query": "",
            "summary": "",
            "metrics": {
                "value": value,
            },
            "metric_cards": [
                {
                    "label": "Value",
                    "value": self._display_value(
                        value
                    ),
                    "source": None,
                }
            ],
            "records": [],
            "collections": [],
            "sources": [],
            "metadata": {
                "normalized": True,
                "scalar": True,
            },
        }

    # ========================================================
    # SEARCH / EXTERNAL
    # ========================================================

    async def _normalize_search(
        self,
        *,
        user_prompt: str,
        intent: Any,
        tool_name: str,
        tool_data: dict[str, Any],
    ) -> dict[str, Any]:

        compact = self._compact_search_data(
            tool_data
        )

        intent_data = self._as_dict(
            intent
        )

        prompt = f"""
You are ZenUI's Result Normalizer.

Convert the supplied tool result into structured data.

Do NOT answer the user.
Do NOT generate UI code.
Do NOT generate OpenUI code.
Do NOT invent information.

USER REQUEST:
{user_prompt}

INTENT:
{json.dumps(
    intent_data,
    ensure_ascii=False,
    default=str,
)}

TOOL:
{tool_name}

TOOL DATA:
{json.dumps(
    compact,
    ensure_ascii=False,
    default=str,
)}

Return ONLY valid JSON.

Use exactly this structure:

{{
    "summary": "",
    "metrics": {{}},
    "metric_cards": [],
    "records": [],
    "sources": []
}}

Rules:

- Preserve factual information from the tool.
- Never invent facts.
- Never invent numbers.
- Never invent URLs.
- A metric must come from the supplied data.
- A source URL must come from the supplied data.
- Records should contain useful factual information.
- Empty arrays/objects are valid.
- Do not force metrics when none exist.
- Do not force records when none exist.
"""

        try:

            normalized = await self.llm.generate_json(
                prompt,
                max_tokens=2500,
            )

            if isinstance(
                normalized,
                Mapping,
            ):

                return self._sanitize_search_output(
                    tool_name=tool_name,
                    normalized=dict(
                        normalized
                    ),
                    raw=tool_data,
                )

        except Exception as error:

            print(
                "ResultNormalizer search normalization failed:",
                error,
            )

        return self._deterministic_search(
            tool_name=tool_name,
            raw=tool_data,
        )

    # ========================================================
    # SEARCH SANITIZATION
    # ========================================================

    def _sanitize_search_output(
        self,
        *,
        tool_name: str,
        normalized: dict[str, Any],
        raw: dict[str, Any],
    ) -> dict[str, Any]:

        allowed_urls = set(
            self._extract_urls_recursive(
                raw
            )
        )

        metrics = self._sanitize_metrics(
            normalized.get(
                "metrics"
            )
        )

        metric_cards = self._sanitize_metric_cards(
            normalized.get(
                "metric_cards"
            )
        )

        # Only retain source URLs that really exist
        # in the original tool response.
        clean_cards = []

        for card in metric_cards:

            source = card.get(
                "source"
            )

            if (
                source
                and source not in allowed_urls
            ):

                card = {
                    **card,
                    "source": None,
                }

            clean_cards.append(
                card
            )

        records = self._sanitize_records(
            normalized.get(
                "records"
            )
        )

        sources = []

        for source in self._sanitize_sources(
            normalized.get(
                "sources"
            )
        ):

            if source["url"] in allowed_urls:
                sources.append(
                    source
                )

        return {
            "source": tool_name,
            "query": self._clean_string(
                raw.get(
                    "query"
                )
            ),
            "summary": self._clean_string(
                normalized.get(
                    "summary"
                )
            ),
            "metrics": metrics,
            "metric_cards": clean_cards,
            "records": records,
            "collections": [],
            "sources": sources,
            "metadata": {
                "normalized": True,
                "external": True,
                "record_count": len(
                    records
                ),
            },
        }

    # ========================================================
    # DETERMINISTIC SEARCH FALLBACK
    # ========================================================

    def _deterministic_search(
        self,
        *,
        tool_name: str,
        raw: dict[str, Any],
    ) -> dict[str, Any]:

        items = self._search_items(
            raw
        )

        records = []

        sources = []

        seen_urls: set[str] = set()

        for item in items:

            title = self._clean_string(
                item.get(
                    "title"
                )
                or item.get(
                    "name"
                )
            )

            snippet = self._clean_string(
                item.get(
                    "snippet"
                )
                or item.get(
                    "description"
                )
                or item.get(
                    "content"
                )
            )

            date = self._clean_string(
                item.get(
                    "date"
                )
            )

            url = self._clean_string(
                item.get(
                    "url"
                )
                or item.get(
                    "link"
                )
            )

            record: dict[str, Any] = {}

            if title:
                record["title"] = title

            if snippet:
                record["snippet"] = snippet

            if date:
                record["date"] = date

            if url:
                record["source"] = url

            if record:
                records.append(
                    record
                )

            if url and url not in seen_urls:

                sources.append(
                    {
                        "title": title or url,
                        "url": url,
                    }
                )

                seen_urls.add(
                    url
                )

        return {
            "source": tool_name,
            "query": self._clean_string(
                raw.get(
                    "query"
                )
            ),
            "summary": "",
            "metrics": {},
            "metric_cards": [],
            "records": records,
            "collections": [],
            "sources": sources,
            "metadata": {
                "normalized": True,
                "external": True,
                "fallback": True,
                "record_count": len(
                    records
                ),
            },
        }

    # ========================================================
    # SUMMARY
    # ========================================================

    def _extract_summary(
        self,
        data: dict[str, Any],
    ) -> str:

        for key in (
            "summary",
            "description",
            "message",
            "text",
        ):

            value = data.get(
                key
            )

            if isinstance(
                value,
                str,
            ) and value.strip():

                return value.strip()

        return ""

    # ========================================================
    # METRICS
    # ========================================================

    def _extract_metrics(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:

        metrics: dict[str, Any] = {}

        explicit = data.get(
            "metrics"
        )

        if isinstance(
            explicit,
            Mapping,
        ):

            metrics.update(
                self._sanitize_metrics(
                    explicit
                )
            )

        # A single explicit numeric value can be represented
        # as a metric without assuming a business meaning.
        if "value" in data:

            value = data.get(
                "value"
            )

            if self._is_scalar(
                value
            ):

                metrics.setdefault(
                    "value",
                    value,
                )

        return metrics

    # ========================================================
    # METRIC CARDS
    # ========================================================

    def _build_metric_cards(
        self,
        metrics: dict[str, Any],
    ) -> list[dict[str, Any]]:

        cards = []

        for key, value in metrics.items():

            cards.append(
                {
                    "label": self._humanize_key(
                        key
                    ),
                    "value": self._display_value(
                        value
                    ),
                    "source": None,
                }
            )

        return cards

    # ========================================================
    # RECORD EXTRACTION
    # ========================================================

    def _extract_records(
        self,
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:

        # Explicit records have highest priority.
        explicit = data.get(
            "records"
        )

        records = self._records_from_list(
            explicit
        )

        if records:
            return records

        # Search common structural containers,
        # without assuming a domain.
        candidates: list[Any] = []

        for key in (
            "data",
            "items",
            "rows",
            "entries",
            "objects",
            "results",
        ):

            if key in data:
                candidates.append(
                    data.get(
                        key
                    )
                )

        for candidate in candidates:

            records = self._records_from_value(
                candidate
            )

            if records:
                return records

        # Finally inspect nested dictionaries.
        for key, value in data.items():

            if key in {
                "metrics",
                "metadata",
                "sources",
                "summary",
                "description",
            }:
                continue

            records = self._records_from_value(
                value
            )

            if records:
                return records

        return []

    def _records_from_value(
        self,
        value: Any,
    ) -> list[dict[str, Any]]:

        if isinstance(
            value,
            list,
        ):
            return self._records_from_list(
                value
            )

        if isinstance(
            value,
            Mapping,
        ):

            nested = value.get(
                "records"
            )

            if isinstance(
                nested,
                list,
            ):

                return self._records_from_list(
                    nested
                )

            for nested_value in value.values():

                if isinstance(
                    nested_value,
                    list,
                ):

                    records = self._records_from_list(
                        nested_value
                    )

                    if records:
                        return records

        return []

    def _records_from_list(
        self,
        value: Any,
    ) -> list[dict[str, Any]]:

        if not isinstance(
            value,
            list,
        ):
            return []

        records = []

        for item in value:

            if isinstance(
                item,
                Mapping,
            ):

                clean = self._clean_record(
                    item
                )

                if clean:
                    records.append(
                        clean
                    )

        return records

    # ========================================================
    # COLLECTIONS
    # ========================================================

    def _extract_collections(
        self,
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:

        collections = []

        for key, value in data.items():

            if not isinstance(
                value,
                list,
            ):
                continue

            if all(
                isinstance(
                    item,
                    Mapping,
                )
                for item in value
            ):
                continue

            if not value:
                continue

            collections.append(
                {
                    "name": str(
                        key
                    ),
                    "values": list(
                        value
                    ),
                }
            )

        return collections

    # ========================================================
    # SOURCES
    # ========================================================

    def _extract_sources(
        self,
        data: dict[str, Any],
    ) -> list[dict[str, str]]:

        sources = []

        explicit = data.get(
            "sources"
        )

        if isinstance(
            explicit,
            list,
        ):

            sources.extend(
                self._sanitize_sources(
                    explicit
                )
            )

        # Also discover URLs embedded in the result.
        discovered = self._extract_urls_recursive(
            data
        )

        existing = {
            item["url"]
            for item in sources
        }

        for url in discovered:

            if url not in existing:

                sources.append(
                    {
                        "title": url,
                        "url": url,
                    }
                )

                existing.add(
                    url
                )

        return sources

    # ========================================================
    # METADATA
    # ========================================================

    def _extract_metadata(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:

        metadata = data.get(
            "metadata"
        )

        if isinstance(
            metadata,
            Mapping,
        ):

            return dict(
                metadata
            )

        return {}

    # ========================================================
    # SEARCH DETECTION
    # ========================================================

    @staticmethod
    def _looks_like_search_result(
        data: dict[str, Any],
    ) -> bool:

        results = data.get(
            "results"
        )

        if not isinstance(
            results,
            Mapping,
        ):
            return False

        organic = results.get(
            "organic"
        )

        nested = results.get(
            "results"
        )

        return (
            isinstance(
                organic,
                list,
            )
            or isinstance(
                nested,
                list,
            )
        )

    # ========================================================
    # SEARCH ITEMS
    # ========================================================

    @staticmethod
    def _search_items(
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:

        results = data.get(
            "results"
        )

        if not isinstance(
            results,
            Mapping,
        ):
            return []

        organic = results.get(
            "organic"
        )

        if isinstance(
            organic,
            list,
        ):

            return [
                dict(item)
                for item in organic
                if isinstance(
                    item,
                    Mapping,
                )
            ]

        nested = results.get(
            "results"
        )

        if isinstance(
            nested,
            list,
        ):

            return [
                dict(item)
                for item in nested
                if isinstance(
                    item,
                    Mapping,
                )
            ]

        return []

    # ========================================================
    # COMPACT SEARCH DATA
    # ========================================================

    @classmethod
    def _compact_search_data(
        cls,
        data: dict[str, Any],
    ) -> dict[str, Any]:

        items = cls._search_items(
            data
        )

        if not items:
            return {
                "source": data.get(
                    "source"
                ),
                "query": data.get(
                    "query"
                ),
                "results": data.get(
                    "results"
                ),
            }

        compact_items = []

        for item in items[:10]:

            compact: dict[str, Any] = {}

            for key in (
                "title",
                "name",
                "link",
                "url",
                "snippet",
                "description",
                "content",
                "date",
            ):

                if key in item:

                    value = item.get(
                        key
                    )

                    if isinstance(
                        value,
                        str,
                    ):
                        value = value[:3000]

                    compact[key] = value

            compact_items.append(
                compact
            )

        return {
            "source": data.get(
                "source"
            ),
            "query": data.get(
                "query"
            ),
            "results": compact_items,
        }

    # ========================================================
    # URL EXTRACTION
    # ========================================================

    @classmethod
    def _extract_urls_recursive(
        cls,
        value: Any,
    ) -> list[str]:

        urls: list[str] = []

        if isinstance(
            value,
            str,
        ):

            if cls._looks_like_url(
                value
            ):
                urls.append(
                    value.strip()
                )

            return urls

        if isinstance(
            value,
            Mapping,
        ):

            for nested in value.values():

                urls.extend(
                    cls._extract_urls_recursive(
                        nested
                    )
                )

            return list(
                dict.fromkeys(
                    urls
                )
            )

        if isinstance(
            value,
            list,
        ):

            for item in value:

                urls.extend(
                    cls._extract_urls_recursive(
                        item
                    )
                )

        return list(
            dict.fromkeys(
                urls
            )
        )

    # ========================================================
    # SANITIZERS
    # ========================================================

    @staticmethod
    def _sanitize_metrics(
        value: Any,
    ) -> dict[str, Any]:

        if not isinstance(
            value,
            Mapping,
        ):
            return {}

        metrics = {}

        for key, item in value.items():

            if not ResultNormalizer._is_scalar(
                item
            ):
                continue

            clean_key = ResultNormalizer._metric_key(
                key
            )

            metrics[
                clean_key
            ] = item

        return metrics

    @staticmethod
    def _sanitize_metric_cards(
        value: Any,
    ) -> list[dict[str, Any]]:

        if not isinstance(
            value,
            list,
        ):
            return []

        cards = []

        for item in value:

            if not isinstance(
                item,
                Mapping,
            ):
                continue

            label = ResultNormalizer._clean_string(
                item.get(
                    "label"
                )
            )

            raw_value = item.get(
                "value"
            )

            if not label or raw_value is None:
                continue

            source = ResultNormalizer._clean_string(
                item.get(
                    "source"
                )
            )

            cards.append(
                {
                    "label": label,
                    "value": ResultNormalizer._display_value(
                        raw_value
                    ),
                    "source": source or None,
                }
            )

        return cards

    @staticmethod
    def _sanitize_records(
        value: Any,
    ) -> list[dict[str, Any]]:

        if not isinstance(
            value,
            list,
        ):
            return []

        records = []

        for item in value:

            if isinstance(
                item,
                Mapping,
            ):

                clean = ResultNormalizer._clean_record(
                    item
                )

                if clean:
                    records.append(
                        clean
                    )

        return records

    @staticmethod
    def _clean_record(
        item: Mapping[str, Any],
    ) -> dict[str, Any]:

        clean: dict[str, Any] = {}

        for key, value in item.items():

            if value is None:
                continue

            clean[
                str(key)
            ] = value

        return clean

    @staticmethod
    def _sanitize_collections(
        value: Any,
    ) -> list[dict[str, Any]]:

        if not isinstance(
            value,
            list,
        ):
            return []

        collections = []

        for item in value:

            if isinstance(
                item,
                Mapping,
            ):

                name = ResultNormalizer._clean_string(
                    item.get(
                        "name"
                    )
                )

                values = item.get(
                    "values"
                )

                if name and isinstance(
                    values,
                    list,
                ):

                    collections.append(
                        {
                            "name": name,
                            "values": values,
                        }
                    )

        return collections

    @staticmethod
    def _sanitize_sources(
        value: Any,
    ) -> list[dict[str, str]]:

        if not isinstance(
            value,
            list,
        ):
            return []

        sources = []

        seen: set[str] = set()

        for item in value:

            if not isinstance(
                item,
                Mapping,
            ):
                continue

            url = ResultNormalizer._clean_string(
                item.get(
                    "url"
                )
            )

            if not url:
                continue

            if url in seen:
                continue

            title = ResultNormalizer._clean_string(
                item.get(
                    "title"
                )
            )

            sources.append(
                {
                    "title": title or url,
                    "url": url,
                }
            )

            seen.add(
                url
            )

        return sources

    @staticmethod
    def _sanitize_metadata(
        value: Any,
    ) -> dict[str, Any]:

        if isinstance(
            value,
            Mapping,
        ):
            return dict(
                value
            )

        return {}

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def _as_dict(
        value: Any,
    ) -> dict[str, Any]:

        if isinstance(
            value,
            Mapping,
        ):
            return dict(
                value
            )

        if hasattr(
            value,
            "model_dump",
        ):

            try:

                result = value.model_dump()

                if isinstance(
                    result,
                    Mapping,
                ):
                    return dict(
                        result
                    )

            except Exception:
                pass

        return {}

    @staticmethod
    def _clean_string(
        value: Any,
    ) -> str:

        if value is None:
            return ""

        return str(
            value
        ).strip()

    @staticmethod
    def _is_scalar(
        value: Any,
    ) -> bool:

        return value is None or isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        )

    @staticmethod
    def _display_value(
        value: Any,
    ) -> str:

        if isinstance(
            value,
            bool,
        ):
            return (
                "Yes"
                if value
                else "No"
            )

        if value is None:
            return ""

        return str(
            value
        )

    @staticmethod
    def _metric_key(
        value: Any,
    ) -> str:

        text = str(
            value or "metric"
        ).strip().lower()

        text = re.sub(
            r"[^a-z0-9]+",
            "_",
            text,
        )

        text = text.strip(
            "_"
        )

        return text or "metric"

    @staticmethod
    def _humanize_key(
        value: Any,
    ) -> str:

        text = str(
            value or ""
        ).replace(
            "_",
            " ",
        ).strip()

        if not text:
            return "Value"

        return text.title()

    @staticmethod
    def _looks_like_url(
        value: str,
    ) -> bool:

        return bool(
            re.match(
                r"^https?://",
                value.strip(),
                flags=re.IGNORECASE,
            )
        )


# ============================================================
# SINGLETON
# ============================================================

result_normalizer = ResultNormalizer()