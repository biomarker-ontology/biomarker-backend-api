import os 
from flask import Flask 
from flask_jwt_extended import JWTManager
from flask_cors import CORS 
from flask_restx import Api
from .dataset import api as dataset_api 
from flask_pymongo import PyMongo

def create_app():

    # create flask instance 
    app = Flask(__name__, instance_relative_config = True)

    # load configurations  
    # TODO : figure out how to deal with these 
    app.config['MONGO_URI'] = f'mongodb://running_biomarkerkb:27017/biomarkerkbdb'
    app.config['JWT_SECRET_KEY'] = f''

    CORS(app)
    jwt = JWTManager(app)
    mongo = PyMongo(app)

    # setup the api using the flask_restx library 
    api = Api(app, version = '1.0', title = 'BiomarkerKB APIs', description = 'Biomarker Knowledgebase API')
    api.add_namespace(dataset_api)

    return app