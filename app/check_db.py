import sqlite3

con = sqlite3.connect("instance/railsmart_backup.db")
cur = con.cursor()

for table in ["users", "trains", "bookings"]:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(table, ":", cur.fetchone()[0], "records")
    except Exception as e:
        print(table, ":", e)

con.close()