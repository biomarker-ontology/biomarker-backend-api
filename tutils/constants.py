from tutils.db import get_collections


def biomarker_default() -> str:
    collections = get_collections()
    return collections["data_model"]


def canonical_id_default() -> str:
    collections = get_collections()
    return collections["canonical_id_map"]


def second_level_id_default() -> str:
    collections = get_collections()
    return collections["second_level_id_map"]


def unreviewed_default() -> str:
    collections = get_collections()
    return collections["unreviewed"]


def stats_default() -> str:
    collections = get_collections()
    return collections["stats"]
