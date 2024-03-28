import mysql.connector

# MySQL connection
db_conn = mysql.connector.connect(
  host="kafka-3855.westus3.cloudapp.azure.com",  # VM's DNS name or IP address
  user="adam",
  passwd="password",
  database="artist_tracker"
)

db_cursor = db_conn.cursor()

# List of tables to drop
tables_to_drop = ['artists', 'social_media', 'radio_play', 'tracked_artists']

for table in tables_to_drop:
    try:
        db_cursor.execute(f'DROP TABLE IF EXISTS {table};')
        print(f"Table {table} dropped successfully.")
    except mysql.connector.Error as e:
        print(f"Error dropping table {table}: {e}")

db_conn.commit()
db_conn.close()
