import sqlite3
conn = sqlite3.connect('leadlift.db')
print(conn.execute('SELECT value FROM settings WHERE key="signalhire_api_key"').fetchone())
conn.close()
