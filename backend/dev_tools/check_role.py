import sqlite3
conn = sqlite3.connect('c:/Users/Yoel Abreu/Documents/epran/Astroweb/AppWeb_v2/backend/app.db')
cursor = conn.cursor()
cursor.execute("SELECT rol FROM users WHERE username='dev'")
print("ROLE IS:", cursor.fetchone())
