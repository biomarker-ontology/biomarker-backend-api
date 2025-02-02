import sys
import subprocess
from pymongo import MongoClient
import pymongo
from pymongo.database import Database
from pymongo.collection import Collection
from logging import Logger
from typing import Optional, NoReturn, Literal
from urllib.parse import quote_plus
from tutils.config import get_config
from tutils.logging import log_msg


def get_database_handle(
    db_name: str,
    port: int,
    username: str,
    password: str,
    host: str = "mongodb://127.0.0.1:",
    auth_source: Optional[str] = None,
    auth_mechanism: str = "SCRAM-SHA-1",
    timeout: int = 1_000,
) -> Database | NoReturn:
    """Returns a database handle."""
    try:
        auth_source = db_name if auth_source is None else auth_source
        client: MongoClient = MongoClient(
            host=f"{host}{port}",
            username=username,
            password=password,
            authSource=auth_source,
            authMechanism=auth_mechanism,
            serverSelectionTimeoutMS=timeout,
        )
        dbh = client[db_name]
        return dbh
    except Exception as e:
        print(e)
        sys.exit(1)


def get_standard_db_handle(server: str) -> Database:
    """Gets the standard database handle."""
    config_obj = get_config()
    port = config_obj["dbinfo"]["port"][server]
    db_name = config_obj["dbinfo"]["dbname"]
    db_user = config_obj["dbinfo"][db_name]["user"]
    db_pass = config_obj["dbinfo"][db_name]["password"]
    return get_database_handle(
        db_name=db_name, port=port, username=db_user, password=db_pass
    )


def get_collections() -> dict[str, str]:
    """Gets a list of the collections."""
    config = get_config()
    db_name = config["dbinfo"]["dbname"]
    return config["dbinfo"][db_name]["collections"]


def setup_index(
    collection: Collection,
    index_field: str,
    unique: bool = False,
    order: Literal["ascending", "descending"] = "ascending",
    index_name: Optional[str] = None,
    logger: Optional[Logger] = None,
) -> None:
    """Sets up a regular index on a field.

    Parameters
    ----------
    collection: Collection
        The database collection.
    index_field: str
        The field to index.
    unique: bool, optional
        Whether to make the index unique, defaults to False.
    order: Literal["ascending", "descending"], optional
        Sort order for the index, defaults to "ascending".
    index_name: str, optional
        The name of the index to create, will be assigned a default name if None.
    logger: Logger, optional
        A logger to log status messages to.
    """
    if index_name is None:
        index_name = f"{index_field}_{order}"
    if index_name not in collection.index_information():
        if order == "ascending":
            collection.create_index(
                [(index_field, pymongo.ASCENDING)], name=index_name, unique=unique
            )
        elif order == "descending":
            collection.create_index(
                [(index_field, pymongo.DESCENDING)], name=index_name, unique=unique
            )
        status_message = (
            f"Created `{order}` index `{index_name}` on collection `{collection.name}`."
        )
        if logger is not None:
            log_msg(logger=logger, msg=status_message)
        print(status_message)
    else:
        status_message = f"{order.title()} index `{index_name}` on collection `{collection.name}` already exists."
        if logger is not None:
            log_msg(logger=logger, msg=status_message)
        print(status_message)


def create_text_index(collection: Collection, logger: Optional[Logger] = None) -> None:
    """Creates a text index on the `all_text` field."""
    collection.create_index([("all_text", "text")])
    status_message = f"Created `all_text` text index on collection `{collection.name}`."
    if logger is not None:
        log_msg(logger=logger, msg=status_message)
    print(status_message)


def get_connection_string(
    server: str,
    host: str = "127.0.0.1:",
    auth_source: Optional[str] = None,
    auth_mechanism: str = "SCRAM-SHA-1",
) -> str:
    """Return a connection string."""
    config_obj = get_config()
    db_name = config_obj["dbinfo"]["dbname"]
    port = config_obj["dbinfo"]["port"][server]
    db_user = quote_plus(config_obj["dbinfo"][db_name]["user"])
    db_pass = quote_plus(config_obj["dbinfo"][db_name]["password"])
    auth_source = auth_source if auth_source is not None else db_name
    uri = f"mongodb://{db_user}:{db_pass}@{host}{port}/{db_name}?authSource={auth_source}&authMechanism={auth_mechanism}"
    return uri


def dump_id_collection(connection_string: str, save_path: str, collection: str) -> bool:
    """Dumps the ID collections to disk to be used later for replication in the
    production database. Can only be run on the tst server.

    Parameters
    ----------
    connection_string: str
        Connection string for the MongoDB connection.
    save_path: str
        The filepath to the local ID map.
    collection: str
        The collection to dump.

    Returns
    -------
    bool
        Indication if the collection was dumped successfully.
    """
    command = [
        "mongoexport",
        "--uri",
        connection_string,
        "--collection",
        collection,
        "--out",
        save_path,
    ]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print("Args passed:")
        print(f"Connection string: {connection_string}")
        print(f"Save path: {save_path}")
        print(f"Collection: {collection}")
        print(e)
        return False
    return True


def load_id_collection(connection_string: str, load_path: str, collection: str) -> bool:
    """Loads the local ID collections into the prod database.

    Parameters
    ----------
    connection_string : str
        Connection string for the MongoDB connection.
    load_path : str
        The filepath to the local ID map.
    collection : str
        The collection to load into.

    Returns
    -------
    bool
        Indication if the collection was loaded successfully.
    """
    command = [
        "mongoimport",
        "--uri",
        connection_string,
        "--collection",
        collection,
        "--file",
        load_path,
        "--mode",
        "upsert",
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print("Args passed:")
        print(f"Connection string: {connection_string}")
        print(f"Load path: {load_path}")
        print(f"Collection: {collection}")
        print(e)
        return False
    return True
