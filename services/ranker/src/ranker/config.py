"""Ranker configuration: loads ranking.yaml on top of base settings."""

from __future__ import annotations

from pathlib import Path

import yaml
from luna_shared.config import RankerSettings
from luna_shared.ir.bm25 import BM25Config
from luna_shared.ir.scoring import ScoringConfig


def load_ranking_yaml(path: str = "config/ranking.yaml") -> dict:
    p = Path(path)
    if not p.exists():
        # Try relative to repo root from service working dir
        for candidate in (Path.cwd() / path, Path(__file__).resolve().parents[5] / path):
            if candidate.exists():
                p = candidate
                break
    if p.exists():
        with p.open() as fh:
            return yaml.safe_load(fh) or {}
    return {}


def get_settings() -> RankerSettings:
    return RankerSettings()


def get_bm25_config() -> BM25Config:
    return BM25Config.from_ranking_yaml(load_ranking_yaml())


def get_scoring_config() -> ScoringConfig:
    return ScoringConfig.from_ranking_yaml(load_ranking_yaml())


__all__ = ["get_bm25_config", "get_scoring_config", "get_settings", "load_ranking_yaml"]
