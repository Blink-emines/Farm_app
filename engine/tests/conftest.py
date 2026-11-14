import copy
import json
from pathlib import Path

import pytest

from engine.loaders import load_crops, load_weights
from engine.rules import Ctx
from engine.season_calendar import build_calendar
from engine.scorer import resolve_seasons

HERE = Path(__file__).parent
REAL_SAMPLE = HERE.parents[1] / "data" / "samples" / "features_default.json"


@pytest.fixture
def features_mock():
    return json.loads((HERE / "features_mock.json").read_text())


@pytest.fixture
def crops():
    return load_crops()


@pytest.fixture
def weights():
    return load_weights()


@pytest.fixture
def make_ctx(features_mock, crops, weights):
    def make(crop_ids, features=None):
        seasons, _ = resolve_seasons(crop_ids, None, crops)
        feats = features or features_mock
        cal, seasons = build_calendar(seasons, crops, feats, weights["warnings"])
        return Ctx(seasons, cal, copy.deepcopy(crops), feats, weights,
                   {s["id"]: s["name"] for s in feats["sources"]})
    return make


@pytest.fixture
def request_default():
    return {"latitude": 33.96, "longitude": -5.27,
            "current_rotation": {"seasons": [{"crop_id": "wheat"}, {"crop_id": "wheat"}]},
            "priorities": {"save_water": 3, "improve_soil": 3, "extra_income": 2,
                           "reduce_erosion": 1, "forage": 0}}
