# Current Tasks

- [ ] Issue: The 'major_cshub_scraper.py' script is still not clicking on the advanced search icon in the sidebar after login, even with the updated locator.

## Task: Import professors.jsonl to MongoDB and create a GUI

### Phase 1: Database Setup and Data Import
- [ ] **Install MongoDB and pymongo:** Ensure MongoDB is installed and running. Install the Python driver: `pip install pymongo`.
- [ ] **Create an import script:** Write a Python script (`import_to_mongo.py`) that reads `professors.jsonl` line by line.
- [ ] **Connect to MongoDB:** The script should connect to a local MongoDB instance.
- [ ] **Insert data:** For each line in the JSONL file, parse the JSON and insert it as a document into a new collection (e.g., `professors`) in a new database (e.g., `university_db`).

### Phase 2: GUI Implementation
- [ ] **Choose a GUI framework:** Select a Python GUI library like Tkinter, PyQt, or a web framework like Flask/Django. Flask is a good lightweight choice.
- [ ] **Create the main application file:** Write a Python script for the GUI (e.g., `app.py`).
- [ ] **Connect to MongoDB:** The GUI application will need to connect to the MongoDB database to fetch data.
- [ ] **Display data:** Implement a view that queries the `professors` collection and displays the data in a user-friendly format, like a table.
- [ ] **Implement basic features:** Add features like pagination to handle the large dataset and a search bar to filter professors by name, university, or research fields.