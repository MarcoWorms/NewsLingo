# adds a field to count how many news were sent to each user

def migrate_users_news_count():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    if 'news_count' not in [column[1] for column in columns]:
        cursor.execute("ALTER TABLE users ADD COLUMN news_count INTEGER DEFAULT 0")

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    for user_id, in users:
        cursor.execute("UPDATE users SET news_count = 1 WHERE user_id = ?", (user_id,))

    conn.commit()
    conn.close()
