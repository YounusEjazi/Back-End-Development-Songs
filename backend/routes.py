from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# Health Check Endpoint
######################################################################
@app.route("/health", methods=["GET"])
def health():
    return {"status": "OK"}

######################################################################
# Count Documents Endpoint
######################################################################
@app.route("/count", methods=["GET"])
def count():
    count = db.songs.count_documents({})
    return {"count": count}

######################################################################
# Find Documents Endpoint
######################################################################
from flask import jsonify

@app.route("/song", methods=["GET"])
def songs():
    # Query all documents in the 'songs' collection
    results = list(db.songs.find({}))

    # Debug print to check the first document
    print(results[0])

    # Return the results using jsonify and parse_json to handle BSON to JSON conversion
    return jsonify({"songs": parse_json(results)}), 200

######################################################################
# Find Songs by ID
######################################################################
@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    # Use the db.songs.find_one method to find a song by its ID
    song = db.songs.find_one({"id": id})
    
    # If the song is not found, return a 404 response with a message
    if song is None:
        return jsonify({"message": "song with id not found"}), 404
    
    # If the song is found, return it as a JSON response with a 200 status code
    return jsonify(parse_json(song)), 200

######################################################################
# Create a Song
######################################################################
@app.route("/song", methods=["POST"])
def create_song():
    # Get data from the JSON body
    song_in = request.json

    # Debugging print statement
    print(song_in["id"])

    # Check if a song with the same ID already exists
    song = db.songs.find_one({"id": song_in["id"]})
    if song:
        # If the song already exists, return a 302 response with a message
        return jsonify({"Message": f"song with id {song_in['id']} already present"}), 302

    # If the song doesn't exist, insert the new song
    insert_id = db.songs.insert_one(song_in).inserted_id

    # Return a success message with the inserted ID and a 201 status code
    return jsonify({"inserted id": str(insert_id)}), 201


######################################################################
# Update a Song
######################################################################
@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    # Extract song data from the request body
    song_data = request.get_json()

    # Find the song in the database by its ID
    existing_song = db.songs.find_one({"id": id})

    if not existing_song:
        # If the song does not exist, return a 404 response
        return jsonify({"message": "song not found"}), 404

    # Update the existing song with the new data
    update_result = db.songs.update_one(
        {"id": id},
        {"$set": song_data}
    )

    if update_result.modified_count == 0:
        # If nothing was updated (e.g., the data is the same), return a message indicating so
        return jsonify({"message": "song found, but nothing updated"}), 200

    # Retrieve the updated song to send back in the response
    updated_song = db.songs.find_one({"id": id})

    # Convert BSON ObjectId to string if necessary
    updated_song["_id"] = str(updated_song["_id"])

    # Return the updated song with a 201 Created status
    return jsonify(updated_song), 201

######################################################################
# Delete a Song
######################################################################

@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    # Attempt to delete the song by its ID
    result = db.songs.delete_one({"id": id})

    if result.deleted_count == 0:
        # If no song was deleted, return a 404 response with a message
        return jsonify({"message": "song not found"}), 404

    # If the song was deleted, return a 204 No Content response
    return '', 204




