import sqlite3

conn = sqlite3.connect('stats.sqlite')
c = conn.cursor()

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
