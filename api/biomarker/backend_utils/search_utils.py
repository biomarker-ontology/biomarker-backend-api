""" Handles the backend logic for the biomarker search endpoints.
"""

from flask import Request, current_app
from typing import Tuple, Dict, List
import time

from . import db as db_utils
from . import utils as utils
from . import DB_COLLECTION, SEARCH_CACHE_COLLECTION


def init() -> Tuple[Dict, int]:
    """Gets the searchable fields? Not really sure the purpose
    of this endpoint, copying Robel's response object.

    Returns
    -------
    tuple : (dict, int)
        The searchable fields and the HTTP code.
    """
    # TODO : implement a separate collection for this eventually, hardcoding for now
    response_object = {
        "best_biomarker_role": [
            "prognostic",
            "diagnostic",
            "monitoring",
            "risk",
            "predictive",
            "safety",
            "response",
        ],
        "assessed_entity_type": [
            "protein",
            "glycan",
            "metabolite",
            "gene",
            "chemical element",
            "cell",
        ],
        "simple_search_category": [
            {"id": "any", "display": "Any"},
            {"id": "biomarker", "display": "Biomarker"},
            {"id": "condition", "display": "Condition"},
        ],
    }
    return response_object, 200


def simple_search(api_request: Request) -> Tuple[Dict, int]:
    """Entry point for the backend logic of the search/simple endpoint.

    Parameters
    ----------
    api_request : Request
        The flask request object.

    Returns
    -------
    tuple : (dict, int)
        The return JSON and HTTP code.
    """
    request_arguments, request_http_code = utils.get_request_object(
        api_request, "search_simple"
    )
    if request_http_code != 200:
        return request_arguments, request_http_code

    mongo_query, projection_object = _search_query_builder(request_arguments, True)

    # TODO : delete logging
    custom_app = db_utils.cast_app(current_app)
    start_time = time.time()
    custom_app.api_logger.info(f"SIMPLE SEARCH QUERY TIME\n\tREQUEST: {request_arguments}")
    custom_app.api_logger.info(f"\tSTART TIME: {start_time}")

    return_object, query_http_code = db_utils.search_and_cache(
        request_object=request_arguments,
        query_object=mongo_query,
        search_type="simple",
        projection_object=projection_object,
        collection=DB_COLLECTION,
        cache_collection=SEARCH_CACHE_COLLECTION,
    )

    # TODO : delete logging
    end_time = time.time()
    custom_app.api_logger.info(f"\tEND TIME: {end_time}\n\tELAPSED TIME: {end_time - start_time}")

    return return_object, query_http_code


def full_search(api_request: Request) -> Tuple[Dict, int]:
    """Entry point for the backend logic of the search/full endpoint.

    Parameters
    ----------
    api_request : Request
        The flask request object.

    Returns
    -------
    tuple : (dict, int)
        The return JSON and HTTP code.
    """
    request_arguments, request_http_code = utils.get_request_object(
        api_request, "search_full"
    )
    if request_http_code != 200:
        return request_arguments, request_http_code

    mongo_query, projection_object = _search_query_builder(request_arguments, False)
    return_object, query_http_code = db_utils.search_and_cache(
        request_object=request_arguments,
        query_object=mongo_query,
        search_type="full",
        projection_object=projection_object,
        collection=DB_COLLECTION,
        cache_collection=SEARCH_CACHE_COLLECTION,
    )

    return return_object, query_http_code


def _search_query_builder(
    request_object: Dict, simple_search_flag: bool
) -> Tuple[Dict, Dict]:
    """Biomarker search endpoint query builder.

    Parameters
    ----------
    request_object : dict
        The validated request object from the user API call.
    simple_search_flag : bool
        True if simple search, False for full search.

    Returns
    -------
    tuple : (dict, dict)
        The MongoDB query and the projection object.
    """
    field_map = {
        "biomarker_id": "biomarker_id",
        "biomarker": "biomarker_component.biomarker",
        "biomarker_entity_name": "biomarker_component.assessed_biomarker_entity.recommended_name",
        "biomarker_entity_id": "biomarker_component.assessed_biomarker_entity_id",
        "biomarker_entity_type": "biomarker_component.assessed_entity_type",
        "specimen_name": "biomarker_component.specimen.name",
        "specimen_id": "biomarker_component.specimen.id",
        "specimen_loinc_code": "biomarker_component.specimen.loinc_code",
        "best_biomarker_role": "best_biomarker_role.role",
        "publication_id": "citation.reference.id",
        "condition_id": "condition.recommended_name.id",
        "condition_name": "condition.recommended_name.name",
        "condition_synonym_id": "condition.synonyms.id",
        "condition_synonym_name": "condition.synonyms.name",
    }

    projection_object = {"biomarker_id": 1}
    query_list: List[Dict] = []

    if simple_search_flag:
        search_term = request_object["term"]
        term_category = request_object["term_category"].strip().lower()

        if term_category == "any":
            return {"$text": {"$search": utils.prepare_search_term(search_term)}}, projection_object

        elif term_category == "biomarker":
            query_list = [
                {path: {"$regex": utils.prepare_search_term(search_term, wrap=False), "$options": "i"}}
                for key, path in field_map.items()
                if key
                not in {
                    "condition_id",
                    "condition_name",
                    "condition_synonym_id",
                    "condition_synonym_name",
                }
            ]

        elif term_category == "condition":
            query_list = [
                {path: {"$regex": utils.prepare_search_term(search_term, wrap=False), "$options": "i"}}
                for key, path in field_map.items()
                if key
                in {
                    "condition_id",
                    "condition_name",
                    "condition_synonym_id",
                    "condition_synonym_name",
                }
            ]

        mongo_query = {"$or": query_list} if query_list else {}

    else:
        cleaned_reuest_object = {
            key: utils.prepare_search_term(value, wrap=False)
            for key, value in request_object.items()
            if key in field_map
        }
        operation = request_object["operation"].lower().strip()

        query_list = [
            {field_map[key]: {"$regex": value, "$options": "i"}}
            for key, value in cleaned_reuest_object.items()
            if key in field_map
        ]

        mongo_query = {f"${operation}": query_list} if query_list else {}

    return mongo_query, projection_object
