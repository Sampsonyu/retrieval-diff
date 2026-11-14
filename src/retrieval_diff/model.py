"""Versioned input contract. Invalid or incomparable evidence must fail visibly."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class ValidationError(ValueError):
    """The supplied snapshot cannot support a valid comparison."""


def _object(value: Any, path: str, allowed: set[str], required: set[str]) -> dict:
    if not isinstance(value, dict):
        raise ValidationError(f"{path}: expected an object")
    if any(not isinstance(key, str) for key in value):
        raise ValidationError(f"{path}: object keys must be strings")
    missing, extra = required - value.keys(), value.keys() - allowed
    if missing:
        raise ValidationError(f"{path}: missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise ValidationError(f"{path}: unknown fields: {', '.join(sorted(extra))}")
    return value


def _string(value: Any, path: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ValidationError(f"{path}: expected {'a' if empty else 'a nonempty'} string")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValidationError(f"{path}: expected valid Unicode text") from exc
    return value


def _array(value: Any, path: str) -> list:
    if not isinstance(value, list):
        raise ValidationError(f"{path}: expected an array")
    return value


def _unique(values: list, path: str) -> None:
    if len(set(values)) != len(values):
        raise ValidationError(f"{path}: duplicate identifiers")


@dataclass(frozen=True)
class Hit:
    document_id: str
    chunk_id: str
    text: str = ""
    score: float | None = None

    @property
    def key(self) -> tuple[str, str]:
        return self.document_id, self.chunk_id

    @classmethod
    def parse(cls, raw: Any, path: str) -> Hit:
        raw = _object(
            raw, path, {"document_id", "chunk_id", "text", "score"}, {"document_id", "chunk_id"}
        )
        score = raw.get("score")
        if score is not None:
            try:
                valid_score = type(score) in (float, int) and math.isfinite(score)
            except OverflowError:
                valid_score = False
            if not valid_score:
                raise ValidationError(f"{path}.score: expected a finite number or null")
        return cls(
            _string(raw["document_id"], f"{path}.document_id"),
            _string(raw["chunk_id"], f"{path}.chunk_id"),
            _string(raw.get("text", ""), f"{path}.text", empty=True),
            score,
        )


@dataclass(frozen=True)
class Drop:
    document_id: str
    chunk_id: str
    reason: str

    @property
    def key(self) -> tuple[str, str]:
        return self.document_id, self.chunk_id


@dataclass(frozen=True)
class Stage:
    name: str
    hits: tuple[Hit, ...]
    dropped: tuple[Drop, ...] = ()


@dataclass(frozen=True)
class Query:
    query_id: str
    query: str
    stages: tuple[Stage, ...]
    relevant_document_ids: tuple[str, ...] | None = None

    @property
    def final(self) -> tuple[Hit, ...]:
        return self.stages[-1].hits


@dataclass(frozen=True)
class Snapshot:
    schema_version: int
    run_id: str
    dataset_id: str
    corpus_fingerprint: str
    queries: tuple[Query, ...]
    config: dict

    @classmethod
    def from_dict(cls, raw: Any) -> Snapshot:
        fields = {
            "schema_version",
            "run_id",
            "dataset_id",
            "corpus_fingerprint",
            "queries",
            "config",
        }
        raw = _object(raw, "snapshot", fields, fields - {"config"})
        if type(raw["schema_version"]) is not int or raw["schema_version"] != 1:
            raise ValidationError("snapshot.schema_version: supported version is 1")
        config = raw.get("config", {})
        if not isinstance(config, dict):
            raise ValidationError("snapshot.config: expected an object")
        try:
            config = json.loads(json.dumps(config, allow_nan=False))
        except (ValueError, TypeError) as exc:
            raise ValidationError(f"snapshot.config: invalid JSON: {exc}") from exc
        queries = tuple(
            cls._query(q, f"queries[{i}]") for i, q in enumerate(_array(raw["queries"], "queries"))
        )
        if not queries:
            raise ValidationError("queries: must contain at least one query")
        _unique([q.query_id for q in queries], "queries")
        return cls(
            1,
            _string(raw["run_id"], "run_id"),
            _string(raw["dataset_id"], "dataset_id"),
            _string(raw["corpus_fingerprint"], "corpus_fingerprint"),
            queries,
            config,
        )

    @staticmethod
    def _query(raw: Any, path: str) -> Query:
        fields = {"query_id", "query", "stages", "relevant_document_ids"}
        raw = _object(raw, path, fields, fields - {"relevant_document_ids"})
        gold = raw.get("relevant_document_ids")
        if gold is not None:
            gold = tuple(
                _string(x, f"{path}.relevant_document_ids")
                for x in _array(gold, f"{path}.relevant_document_ids")
            )
            if not gold:
                raise ValidationError(
                    f"{path}: use null/omit labels for unlabeled queries; empty labels are ambiguous"
                )
            _unique(list(gold), f"{path}.relevant_document_ids")
        stages = []
        content_by_key: dict[tuple[str, str], str] = {}
        for i, stage in enumerate(_array(raw["stages"], f"{path}.stages")):
            p = f"{path}.stages[{i}]"
            stage = _object(stage, p, {"name", "hits", "dropped"}, {"name", "hits"})
            hits = tuple(
                Hit.parse(h, f"{p}.hits[{j}]")
                for j, h in enumerate(_array(stage["hits"], f"{p}.hits"))
            )
            _unique([h.key for h in hits], f"{p}.hits")
            for hit in hits:
                if hit.key in content_by_key and content_by_key[hit.key] != hit.text:
                    raise ValidationError(f"{p}: chunk content changed within a run: {hit.key}")
                content_by_key[hit.key] = hit.text
            drops = []
            for j, drop in enumerate(_array(stage.get("dropped", []), f"{p}.dropped")):
                d = f"{p}.dropped[{j}]"
                drop = _object(
                    drop,
                    d,
                    {"document_id", "chunk_id", "reason"},
                    {"document_id", "chunk_id", "reason"},
                )
                drops.append(
                    Drop(
                        *(
                            _string(drop[k], f"{d}.{k}")
                            for k in ("document_id", "chunk_id", "reason")
                        )
                    )
                )
            _unique([d.key for d in drops], f"{p}.dropped")
            removed = (
                ({h.key for h in stages[-1].hits} - {h.key for h in hits}) if stages else set()
            )
            if any(d.key not in removed for d in drops):
                raise ValidationError(
                    f"{p}: drop reasons must refer to chunks removed from the preceding recorded stage"
                )
            stages.append(Stage(_string(stage["name"], f"{p}.name"), hits, tuple(drops)))
        if not stages or stages[-1].name != "context":
            raise ValidationError(f"{path}: the last recorded stage must be named 'context'")
        _unique([s.name for s in stages], f"{path}.stages")
        return Query(
            _string(raw["query_id"], f"{path}.query_id"),
            _string(raw["query"], f"{path}.query"),
            tuple(stages),
            gold,
        )

    @classmethod
    def load(cls, path: str | Path) -> Snapshot:
        def unique_keys(pairs: list) -> dict:
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValidationError(f"duplicate JSON key: {key}")
                result[key] = value
            return result

        try:
            return cls.from_dict(
                json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_keys)
            )
        except ValidationError:
            raise
        except (ValueError, UnicodeError) as exc:
            raise ValidationError(f"{path}: invalid UTF-8 JSON: {exc}") from exc

    def to_dict(self) -> dict:
        raw = asdict(self)
        raw["queries"] = list(raw["queries"])
        for query in raw["queries"]:
            if query["relevant_document_ids"] is not None:
                query["relevant_document_ids"] = list(query["relevant_document_ids"])
            query["stages"] = list(query["stages"])
            for stage in query["stages"]:
                stage["hits"] = list(stage["hits"])
                stage["dropped"] = list(stage["dropped"])
        return raw

    def save(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.to_dict(), indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
