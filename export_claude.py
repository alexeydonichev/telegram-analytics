import sqlite3
import json
from config import DB_NAME

def export_for_claude(source_id=None, filename="for_claude.md"):
    """Экспорт данных для анализа в Claude"""
    
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Источник
    if source_id:
        c.execute('SELECT * FROM sources WHERE id = ?', (source_id,))
    else:
        c.execute('SELECT * FROM sources ORDER BY id DESC LIMIT 1')
    source = c.fetchone()
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# Анализ канала: {source['title']}\n\n")
        f.write(f"Username: @{source['username']}\n")
        f.write(f"Тип: {source['type']}\n\n")
        
        # ТОП посты
        f.write("## ТОП-20 постов по просмотрам\n\n")
        c.execute('''
            SELECT * FROM posts WHERE source_id = ?
            ORDER BY views DESC LIMIT 20
        ''', (source['id'],))
        
        for i, post in enumerate(c.fetchall(), 1):
            f.write(f"### Пост {i}\n")
            f.write(f"- Просмотры: {post['views']}\n")
            f.write(f"- Репосты: {post['forwards']}\n")
            f.write(f"- Комментарии: {post['replies_count']}\n")
            f.write(f"- Реакции: {post['reactions_json']}\n\n")
            f.write(f"```\n{post['text']}\n```\n\n")
            f.write("---\n\n")
        
        # Лидерборд
        f.write("## ТОП-50 активных участников\n\n")
        f.write("| # | Username | Комментов | Лайков |\n")
        f.write("|---|----------|-----------|--------|\n")
        
        c.execute('''
            SELECT u.username, u.first_name, us.total_comments, us.total_likes_received
            FROM user_stats us
            JOIN users u ON us.user_id = u.id
            WHERE us.source_id = ?
            ORDER BY us.total_comments DESC
            LIMIT 50
        ''', (source['id'],))
        
        for i, user in enumerate(c.fetchall(), 1):
            name = user['username'] or user['first_name'] or 'anon'
            f.write(f"| {i} | @{name} | {user['total_comments']} | {user['total_likes_received']} |\n")
    
    conn.close()
    print(f"✅ Экспортировано в {filename}")
    print("   Скопируй содержимое и вставь в Claude для анализа!")

if __name__ == "__main__":
    export_for_claude()
