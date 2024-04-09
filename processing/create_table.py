import sqlite3
import os

def initialize_db(db_path):
    """
    Initialize the database at the specified path.
    Creates the database file if it does not exist and sets up the initial table structure.
    """
    # Ensure the directory for the SQLite file exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Create the stats table if it doesn't already exist
    c.execute('''
    CREATE TABLE IF NOT EXISTS stats
    (id INTEGER PRIMARY KEY ASC,
    total_artists INTEGER NOT NULL,
    max_followers INTEGER NOT NULL,
    max_spins INTEGER NOT NULL,
    number_of_tracked_artists INTEGER NOT NULL,
    last_updated VARCHAR(100) NOT NULL)
    ''')

    conn.commit()
    conn.close()
