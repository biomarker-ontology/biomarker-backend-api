''' Handles all the logic for assigning/generating the canonical biomarker ID.

Public functions:
    get_ordinal_id: The entry point for the canonical ID assignment process.

Private functions:
    _generate_hash: Generates the core values string and resulting hash value for a record.
    _check_collision: Checks if the hash value already exists in the canonical ID map collection.
    _assign_ordinal: Handles the canonical ID assignment/generation process
    _get_ordinal_id: Gets the existing corresponding ordinal canonical ID for the hash value.
    _new_ordinal: Creates a new entry in the ID collection map with an incremented ordinal canonical ID.
    _increment_ordinal_id: Handles the logic to incrememnt the ordinal canonical ID for a new entry.
    _extract_change: Extracts the change from the biomarker string.
'''

import logging
import hashlib
import sys
import pymongo
import misc_functions as misc_fn
from pymongo.database import Database

CANONICAL_DEFAULT = 'canonical_id_map_collection'

def get_ordinal_id(document: dict, dbh: Database, id_collection: str = CANONICAL_DEFAULT) -> tuple[str, str, str, bool]:
    ''' Assigns the ordinal canonical ID to the document.
    
    Parameters
    ----------
    document: dict
        The document to assign the canonical ID for.
    dbh: Database
        The database handle.
    id_collection: str (default: CANONICAL_DEFAULT)
        The canonical ID map collection.

    Returns
    -------
    tuple: (str, str, str)
        The assigned canonical biomarker ID, the hash value, and the core values string. 
    '''
    hash_value, core_values_str = _generate_hash(document)
    collision_status = _check_collision(hash_value, dbh, id_collection)
    canonical_id = _assign_ordinal(hash_value, core_values_str, collision_status, dbh, id_collection)
    return canonical_id, hash_value, core_values_str, collision_status

def _generate_hash(document: dict) -> tuple:
    ''' Generates the core values string and resulting hash value.
    
    Parameters
    ----------
    document: dict
        The document to generate the hash for. 

    Returns
    -------
    tuple: (str, str)
        The hash value and the concatenated core values string.
    '''
    core_values = []
    for component in document['biomarker_component']:
        core_values.append(_extract_change(component['biomarker']))
        core_values.append(component['assessed_biomarker_entity_id'])

    core_values = [misc_fn.clean_value(v) for v in core_values]
    core_values.sort()
    core_values_str = '_'.join(core_values)

    return hashlib.sha256(core_values_str.encode('utf-8')).hexdigest(), core_values_str

def _check_collision(hash_value: str, dbh: Database, id_collection: str = CANONICAL_DEFAULT) -> bool:
    ''' Checks if the hash value already exists in the database.

    Parameters
    ----------
    hash_value: str
        The hash value to check.
    dbh: Database
        The database handle.
    id_collection: str (default: CANONICAL_DEFAULT)
        The ID collection map.

    Returns
    -------
    bool
        Whether there was a collection or not.
    '''
    if dbh[id_collection].find_one({'hash_value': hash_value}) is not None:
        return True
    return False

def _assign_ordinal(hash_value: str, core_values_str: str, collision: bool, dbh: Database, id_collection: str = CANONICAL_DEFAULT) -> str:
    ''' Assigns the ordinal canonical biomarker ID.

    Parameters
    ----------
    hash_value: str
        The hash value to check for collisions against.
    core_values_str: str
        The core values to save in the collection.
    collision: bool
        Whether or not there is a collision with the hash value.
    dbh: Database
        The database handle.
    id_collection: str (default: CANONICAL_DEFAULT)
        The ID collection map.

    Returns
    -------
    str
        The assigned ordinal canonical ID.
    '''
    if collision:
        ordinal_id = _get_ordinal_id(hash_value, dbh, id_collection)
        return ordinal_id
    ordinal_id = _new_ordinal(hash_value, core_values_str, dbh, id_collection)
    return ordinal_id

def _get_ordinal_id(hash_value: str, dbh: Database, id_collection: str = CANONICAL_DEFAULT) -> str:
    ''' Gets the existing corresponding ordinal ID for the hash value. Will exit on unexpected error.
    
    Parameters
    ----------
    hash_value: str
        The hash value to search on.
    dbh: Database
        The database handle.
    id_collection (default: CANONICAL_DEFAULT)
        The ID collection map.

    Returns
    -------
    str        
        The existing corresponding ordinal canonical ID.
    '''
    target_record = dbh[id_collection].find_one({'hash_value': hash_value})
    if not target_record:
        logging.error(
            f'Some error occurred in looking up existing ordinal canonical ID in `{id_collection}` for:\n\
            \thash value: `{hash_value}`\n\
            \tID collection: `{id_collection}`'
        )
        sys.exit(1)
    return target_record['biomarker_canonical_id']

def _new_ordinal(hash_value: str, core_values_str: str, dbh: Database, id_collection: str = CANONICAL_DEFAULT) -> str:
    ''' Creates a new entry in the ID collection map with an incremented ordinal ID. Will exit if the ID space is full.

    Parameters
    ----------
    hash_value: str
        The new hash value.
    core_values_str: str
        The core values string for the new entry.
    dbh: Database
        The database handle.
    id_collection: str (default: CANONICAL_DEFAULT)
        The ID map collection.

    Raises
    ------
    ValueError
        If the ID space is full.

    Returns
    -------
    str
        The new incremented ordinal ID that was generated and added.
    '''
    max_entry = dbh[id_collection].find_one(sort=[('biomarker_canonical_id', pymongo.DESCENDING)])
    max_ordinal_id = max_entry['biomarker_canonical_id'] if max_entry else 'AA0000'

    try:
        new_ordinal_id = _increment_ordinal_id(max_ordinal_id)
    except ValueError as e:
        print(f'ValueError: {e}')
        logging.error(e)
        sys.exit(1)

    dbh[id_collection].insert_one(
        {
            'hash_value': hash_value, 
            'biomarker_canonical_id': new_ordinal_id, 
            'core_values_str': core_values_str 
        }
    )

    return new_ordinal_id
    
def _increment_ordinal_id(curr_max_id: str) -> str:
    ''' Increments the current max ordinal ID.

    Parameters
    ----------
    curr_max_id: str
        The current max ordinal ID to increment.

    Returns
    -------
    str
        The incremented ordinal ID.
    '''
    letters = curr_max_id[:2]
    numbers = int(curr_max_id[2:])
    if numbers < 9999:
        return letters + str(numbers + 1).zfill(4)
    if letters == 'ZZ':
        raise ValueError('Maximum ordinal ID reached. ID space full.')
    first_letter = letters[0]
    second_letter = letters[1]
    if second_letter == 'Z':
        first_letter = chr(ord(first_letter) + 1)
        second_letter = 'A'
    else:
        second_letter = chr(ord(second_letter) + 1)
    return first_letter + second_letter + '0000'

def _extract_change(biomarker: str) -> str:
    ''' Extracts the change from the biomarker string. For now, naive implementation (grabs first word).

    Parameters
    ----------
    biomarker: str
        The biomarker string to extract the change from.

    Returns
    -------
    str
        The extracted change.
    '''
    return biomarker.split(' ')[0]
