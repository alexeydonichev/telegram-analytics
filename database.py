import sqlite3

def init_db():
    conn = sqlite3.connect('analytics.db')
    c = conn.cursor()
    
    # Посты
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY,
        channel TEXT,
        message_id INTEGER,
        date TEXT,
        text TEXT,
        views INTEGER DEFAULT 0,
        forwards INTEGER DEFAULT 0,
        replies INTEGER DEFAULT 0,
        has_photo INTEGER DEFAULT 0,
        has_video INTEGER DEFAULT 0,
        has_document INTEGER DEFAULT 0,
        UNIQUE(channel, message_id)
    )''')
    
    # Комментарии
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY,
        post_id INTEGER,
        channel TEXT,
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        date TEXT,
        text TEXT,
        reply_to INTEGER,
        FOREIGN KEY(post_id) REFERENCES posts(message_id)
    )''')
    
    # Юзеры
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        user_id INTEGER UNIQUE,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        first_seen TEXT,
        last_seen TEXT
    )''')
    
    # Реакции
    c.execute('''CREATE TABLE IF NOT EXISTS reactions (
        id INTEGER PRIMARY KEY,
        post_id INTEGER,
        channel TEXT,
        emoji TEXT,
        count INTEGER,
        UNIQUE(post_id, channel, emoji)
    )''')
    
    # Статистика юзеров
    c.execute('''CREATE TABLE IF NOT EXISTS user_stats (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        channel TEXT,
        comments_count INTEGER DEFAULT 0,
        reactions_count INTEGER DEFAULT 0,
        first_activity TEXT,
        last_activity TEXT,
        UNIQUE(user_id, channel)
    )''')
    
    conn.commit()
    conn.close()
    print("✅ База данных готова (5 таблиц)")

if __name__ == "__main__":
    init_db()
