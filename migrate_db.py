import sqlite3

conn = sqlite3.connect('books.db')
cursor = conn.cursor()

# Try to add a 'category' column
try:
    cursor.execute("ALTER TABLE books ADD COLUMN category TEXT")
    print("✅ 'category' column added successfully.")
except sqlite3.OperationalError as e:
    print("⚠️ It looks like the column already exists or there's an issue.")
    print("Error:", e)

conn.commit()
conn.close()
