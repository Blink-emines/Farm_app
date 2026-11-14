"""Rotation templates: the candidate alternatives. Crop order only; months come
from the request (current rotation only) or from crops.yaml."""

TEMPLATES = [
    {"id": "wheat_chickpea", "crops": ["wheat", "chickpea"]},
    {"id": "wheat_faba_bean", "crops": ["wheat", "faba_bean"]},
    {"id": "barley_lentil", "crops": ["barley", "lentil"]},
    {"id": "wheat_vetch_oat_cover", "crops": ["wheat", "vetch_oat_cover"]},
    {"id": "wheat_sunflower", "crops": ["wheat", "sunflower"]},
    {"id": "wheat_fallow", "crops": ["wheat", "fallow"]},
    {"id": "alfalfa_perennial", "crops": ["alfalfa"]},
    {"id": "olive_intercrop_perennial", "crops": ["olive_intercrop"]},
]
