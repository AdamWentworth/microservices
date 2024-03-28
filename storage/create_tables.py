import mysql.connector

# MySQL connection
db_conn = mysql.connector.connect(
  host="kafka-3855.westus3.cloudapp.azure.com",  # VM's DNS name or IP address
  user="adam",
  passwd="password",
  database="artist_tracker"
)

db_cursor = db_conn.cursor()

# Create the 'artists' table with 'IF NOT EXISTS' clause
db_cursor.execute('''
CREATE TABLE IF NOT EXISTS artists (
  id VARCHAR(250) PRIMARY KEY,
  name VARCHAR(250) NOT NULL,
  genre VARCHAR(250) NOT NULL,
  region VARCHAR(250) NOT NULL,
  top_tracks TEXT,
  certifications TEXT,
  trace_id VARCHAR(250),  
  date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
''')

# Create the 'social_media' table with 'IF NOT EXISTS' clause
db_cursor.execute('''
CREATE TABLE IF NOT EXISTS social_media (
  id INT AUTO_INCREMENT PRIMARY KEY, 
  artist_id VARCHAR(250) NOT NULL,
  platform VARCHAR(250),
  followers INT,
  plays INT,
  trace_id VARCHAR(250), 
  date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
''')

# Create the 'radio_play' table with 'IF NOT EXISTS' clause
db_cursor.execute('''
CREATE TABLE IF NOT EXISTS radio_play (
  id INT AUTO_INCREMENT PRIMARY KEY, 
  artist_id VARCHAR(250) NOT NULL,
  region VARCHAR(250),
  song_title VARCHAR(250),
  spins INT,
  trace_id VARCHAR(250),  
  date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
''')

# Create the 'tracked_artists' table with 'IF NOT EXISTS' clause
db_cursor.execute('''
CREATE TABLE IF NOT EXISTS tracked_artists (
  id INT AUTO_INCREMENT PRIMARY KEY, 
  user_id VARCHAR(250),
  artist_id VARCHAR(250) NOT NULL,
  trace_id VARCHAR(250),  
  date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
''')

# Commit the changes and close the connection to the database
db_conn.commit()
db_conn.close()
