import sqlite3
from datetime import datetime
from collections import Counter
import json
from config import DB_NAME

def analyze_source(source_id=None):
    """Полный анализ источника"""
    
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Получаем источник
    if source_id:
        c.execute('SELECT * FROM sources WHERE id = ?', (source_id,))
    else:
        c.execute('SELECT * FROM sources ORDER BY id DESC LIMIT 1')
    
    source = c.fetchone()
    if not source:
        print("❌ Источник не найден")
        return
    
    print("\n" + "="*60)
    print(f"📊 АНАЛИТИКА: {source['title']}")
    print(f"   Тип: {source['type']} | @{source['username']}")
    print("="*60)
    
    # ===== СТАТИСТИКА ПОСТОВ =====
    c.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(views) as views,
            SUM(forwards) as forwards,
            SUM(replies_count) as comments,
            AVG(views) as avg_views
        FROM posts WHERE source_id = ?
    ''', (source['id'],))
    
    stats = c.fetchone()
    
    print(f"\n📝 ПОСТЫ:")
    print(f"   Всего: {stats['total']}")
    print(f"   Просмотров: {stats['views']:,}")
    print(f"   Репостов: {stats['forwards']:,}")
    print(f"   Комментариев: {stats['comments']:,}")
    print(f"   Среднее просмотров: {int(stats['avg_views'] or 0):,}")
    
    # ===== ТОП ПОСТЫ =====
    print(f"\n🏆 ТОП-5 ПО ПРОСМОТРАМ:")
    c.execute('''
        SELECT telegram_id, text, views, forwards, replies_count, reactions_json
        FROM posts WHERE source_id = ?
        ORDER BY views DESC LIMIT 5
    ''', (source['id'],))
    
    for i, post in enumerate(c.fetchall(), 1):
        preview = post['text'][:60].replace('\n', ' ') + "..."
        print(f"   {i}. [{post['views']:,} 👀] {preview}")
    
    # ===== ТОП ПО КОММЕНТАРИЯМ =====
    print(f"\n💬 ТОП-5 ПО КОММЕНТАРИЯМ:")
    c.execute('''
        SELECT telegram_id, text, views, replies_count
        FROM posts WHERE source_id = ?
        ORDER BY replies_count DESC LIMIT 5
    ''', (source['id'],))
    
    for i, post in enumerate(c.fetchall(), 1):
        preview = post['text'][:60].replace('\n', ' ') + "..."
        print(f"   {i}. [{post['replies_count']} 💬] {preview}")
    
    # ===== РЕАКЦИИ =====
    print(f"\n😀 ПОПУЛЯРНЫЕ РЕАКЦИИ:")
    c.execute('SELECT reactions_json FROM posts WHERE source_id = ?', (source['id'],))
    
    all_reactions = Counter()
    for row in c.fetchall():
        if row['reactions_json']:
            reactions = json.loads(row['reactions_json'])
            for emoji, count in reactions.items():
                all_reactions[emoji] += count
    
    for emoji, count in all_reactions.most_common(10):
        print(f"   {emoji}: {count:,}")
    
    # ===== ВРЕМЯ ПОСТИНГА =====
    print(f"\n🕐 ЛУЧШЕЕ ВРЕМЯ ПОСТИНГА:")
    c.execute('SELECT date, views FROM posts WHERE source_id = ?', (source['id'],))
    
    hours = Counter()
    weekdays = Counter()
    days_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    
    for row in c.fetchall():
        try:
            dt = datetime.fromisoformat(row['date'].replace('+00:00', '').replace('Z', ''))
            hours[dt.hour] += row['views'] or 0
            weekdays[dt.weekday()] += row['views'] or 0
        except:
            pass
    
    print("   По дням (топ-3 по просмотрам):")
    for day, views in sorted(weekdays.items(), key=lambda x: x[1], reverse=True)[:3]:
        print(f"      {days_ru[day]}: {views:,} просмотров")
    
    print("   По часам (топ-5):")
    for hour, views in sorted(hours.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"      {hour}:00 — {views:,}")
    
    # ===== ДЛИНА ТЕКСТА =====
    print(f"\n📏 ДЛИНА ТЕКСТА vs ВОВЛЕЧЁННОСТЬ:")
    c.execute('SELECT text, views, replies_count FROM posts WHERE source_id = ?', (source['id'],))
    
    short, medium, long_posts = [], [], []
    for row in c.fetchall():
        length = len(row['text'] or '')
        data = {'views': row['views'] or 0, 'comments': row['replies_count'] or 0}
        if length < 300:
            short.append(data)
        elif length < 1000:
            medium.append(data)
        else:
            long_posts.append(data)
    
    if short:
        avg_v = sum(p['views'] for p in short) / len(short)
        avg_c = sum(p['comments'] for p in short) / len(short)
        print(f"   Короткие (<300 симв): {len(short)} постов, {avg_v:.0f} просм, {avg_c:.1f} комм")
    if medium:
        avg_v = sum(p['views'] for p in medium) / len(medium)
        avg_c = sum(p['comments'] for p in medium) / len(medium)
        print(f"   Средние (300-1000): {len(medium)} постов, {avg_v:.0f} просм, {avg_c:.1f} комм")
    if long_posts:
        avg_v = sum(p['views'] for p in long_posts) / len(long_posts)
        avg_c = sum(p['comments'] for p in long_posts) / len(long_posts)
        print(f"   Длинные (>1000): {len(long_posts)} постов, {avg_v:.0f} просм, {avg_c:.1f} комм")
    
    # ===== ЛИДЕРБОРД КОММЕНТАТОРОВ =====
    print(f"\n👥 ТОП-20 АКТИВНЫХ УЧАСТНИКОВ:")
    c.execute('''
        SELECT 
            u.username,
            u.first_name,
            us.total_comments,
            us.total_likes_received
        FROM user_stats us
        JOIN users u ON us.user_id = u.id
        WHERE us.source_id = ?
        ORDER BY us.total_comments DESC, us.total_likes_received DESC
        LIMIT 20
    ''', (source['id'],))
    
    print(f"   {'#':<3} {'Имя':<20} {'Комментов':<12} {'Лайков':<10}")
    print("   " + "-"*50)
    for i, user in enumerate(c.fetchall(), 1):
        name = user['username'] or user['first_name'] or 'Anonymous'
        print(f"   {i:<3} @{name:<19} {user['total_comments']:<12} {user['total_likes_received']:<10}")
    
    conn.close()
    print("\n" + "="*60)

def list_sources():
    """Список всех источников в базе"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, title, type, username FROM sources')
    
    print("\n📋 Источники в базе:")
    for row in c.fetchall():
        print(f"   [{row[0]}] {row[1]} ({row[2]}) @{row[3]}")
    
    conn.close()

if __name__ == "__main__":
    list_sources()
    source_id = input("\nВведи ID источника (или Enter для последнего): ").strip()
    analyze_source(int(source_id) if source_id else None)
