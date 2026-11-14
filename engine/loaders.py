"""Load crops.yaml, weights.yaml and the contract schemas; small crop helpers."""
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
CONTRACTS = HERE.parent / "docs" / "contracts"
UNKNOWN = "unknown, needs local data"
DEFAULT_SOURCE = "default approved by user 2026-11-14, to confirm locally"


def load_crops():
    return yaml.safe_load((HERE / "crops.yaml").read_text())["crops"]


def load_weights():
    return yaml.safe_load((HERE / "weights.yaml").read_text())


def _schema(name):
    return json.loads((CONTRACTS / name).read_text())


def validators():
    feats = Draft202012Validator(_schema("features.schema.json"))
    strat = _schema("strategy.schema.json")
    resp = Draft202012Validator(strat)
    req = Draft202012Validator({"$schema": strat["$schema"], "$defs": strat["$defs"],
                                "$ref": "#/$defs/StrategyRequest"})
    return feats, req, resp


def field(crops, crop, name):
    """The raw {value, source, ...} entry."""
    return crops[crop][name]


def val(crops, crop, name):
    """The value, or None when it is unknown or not applicable."""
    v = crops[crop][name]["value"]
    if v == UNKNOWN or v == "not applicable":
        return None
    return v


def is_unknown(crops, crop, name):
    return crops[crop][name]["value"] == UNKNOWN


def families(crops, crop):
    f = val(crops, crop, "family")
    if f is None:
        return set()
    return set(f) if isinstance(f, list) else {f}


def rooting_class(crops, crop, weights):
    zr = val(crops, crop, "rooting_zr_min_m")
    if not isinstance(zr, (int, float)):
        return None
    rc = weights["rooting_class"]
    if zr >= rc["deep_min_zr_m"]:
        return "deep"
    return "medium" if zr >= rc["medium_min_zr_m"] else "shallow"
