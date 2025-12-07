import math
from flask import Flask, render_template, request, make_response
from pymongo import MongoClient

app = Flask(__name__)

# MongoDB setup
MONGO_URI = 'mongodb://localhost:27017/'
DATABASE_NAME = 'university_db'
COLLECTION_NAME = 'professors'
professors_collection = None
client = None

try:
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    professors_collection = db[COLLECTION_NAME]
    
    # Create an index on 'name' for faster lookups/sorting
    professors_collection.create_index("name")
    
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    professors_collection = None


@app.route('/')
def index():
    if professors_collection is None:
        return "<h1>Database Connection Error</h1><p>Failed to connect to MongoDB. Please ensure the MongoDB server is running.</p>", 500
    
    # Theme handling
    theme = request.cookies.get('theme', 'dark')
    
    # Check if a new theme is requested via query parameter
    requested_theme = request.args.get('theme')
    if requested_theme in ['light', 'dark']:
        theme = requested_theme

    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'university').strip()
    sort_dir = request.args.get('sort_dir', 'asc').strip()
    
    # Research field filtering
    research_fields_filter_raw = request.args.get('fields', '').strip()
    research_fields_filter = [f.strip() for f in research_fields_filter_raw.split(',') if f.strip()]
    
    per_page = 20

    query = {}
    if search_term:
        # Search by name, university, major, or research fields (case-insensitive regex)
        regex_query = {"$regex": search_term, "$options": "i"}
        query = {
            "$or": [
                {"name": regex_query},
                {"university": regex_query},
                {"major": regex_query},
                {"research_fields": regex_query}
            ]
        }
    
    # Add research fields filter to query
    if research_fields_filter:
        # Match documents where research_fields array contains ALL selected fields
        query["research_fields"] = {"$all": research_fields_filter}
        
    
    total_count = professors_collection.count_documents(query)
    total_pages = math.ceil(total_count / per_page)
    
    # Determine sorting parameters
    ALLOWED_SORT_FIELDS = ['name', 'university', 'major', 'h_index']
    
    # Set default sort field to 'university' ascending (1) as requested.
    sort_field = sort_by if sort_by in ALLOWED_SORT_FIELDS else 'university'
    sort_direction = 1 if sort_dir.lower() == 'asc' else -1
    
    if sort_field == 'h_index':
        # Use aggregation to sort h_index numerically (assuming it's stored as string and needs casting)
        pipeline = [
            {"$match": query},
            {
                "$addFields": {
                    # Use $convert to safely cast h_index string to integer for numerical sorting.
                    # If $h_index is null or missing, $ifNull handles it by returning "0" as input.
                    # If the input (including empty string "") fails conversion, onError returns 0.
                    "h_index_numeric": {
                        "$convert": {
                            "input": {"$ifNull": ["$h_index", "0"]},
                            "to": "int",
                            "onError": 0,
                            "onNull": 0
                        }
                    }
                }
            },
            {"$sort": {"h_index_numeric": sort_direction}},
            {"$skip": (page - 1) * per_page},
            {"$limit": per_page}
        ]
        professors = list(professors_collection.aggregate(pipeline))
    else:
        # Use standard find for string/default sorting
        professors = list(professors_collection.find(query)
                          .sort(sort_field, sort_direction)
                          .skip((page - 1) * per_page)
                          .limit(per_page))

    # Render template and set theme cookie
    response = make_response(render_template('index.html',
                                             professors=professors,
                                             page=page,
                                             total_pages=total_pages,
                                             search_term=search_term,
                                             total_count=total_count,
                                             sort_by=sort_by,
                                             sort_dir=sort_dir,
                                             theme=theme,
                                             research_fields_filter=research_fields_filter,
                                             research_fields_filter_raw=research_fields_filter_raw))
    response.set_cookie('theme', theme)
    return response

if __name__ == '__main__':
    # We rely on the index function to handle DB connection errors gracefully.
    app.run(debug=True)