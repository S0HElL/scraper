import json
from pymongo import MongoClient

def import_data_to_mongodb(file_path, db_name, collection_name):
    """
    Imports data from a JSONL file to a MongoDB collection.

    Args:
        file_path (str): The path to the JSONL file.
        db_name (str): The name of the MongoDB database.
        collection_name (str): The name of the collection to import data into.
    """
    client = MongoClient('mongodb://localhost:27017/')
    db = client[db_name]
    collection = db[collection_name]

    # Clear existing data in the collection to avoid duplicates on re-run
    collection.delete_many({})

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                collection.insert_one(data)
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON line: {line.strip()}")

    print(f"Successfully imported data from '{file_path}' to the '{collection_name}' collection in the '{db_name}' database.")
    client.close()

if __name__ == "__main__":
    import_data_to_mongodb('professors.jsonl', 'university_db', 'professors')