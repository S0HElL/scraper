from pymongo import MongoClient

def verify_data(db_name, collection_name):
    """
    Connects to MongoDB and prints the number of documents in the collection.
    """
    client = MongoClient('mongodb://localhost:27017/')
    db = client[db_name]
    collection = db[collection_name]
    
    count = collection.count_documents({})
    print(f"Total documents found in '{collection_name}' collection in '{db_name}' database: {count}")
    
    client.close()

if __name__ == "__main__":
    verify_data('university_db', 'professors')