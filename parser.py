from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import MessageService
from datetime import datetime, timedelta, timezone
import sqlite3
import asyncio
from database import init_db

API_ID = 35668407
API_HASH = "b18ff2c86b7d4617d39603069cd1b5b0"

CHANNELS = ["yourfit_store"]
DAYS_BACK = 365  # ГОД
PARSE_COMMENTS = True
MAX_COMMENTS_PER_POST = 100

class TelegramParser:
    def __init__(self):
        self.client = None
        self.conn = None
        
    async def connect(self):
        self.client = TelegramClient('session', API_ID, API_HASH)
        await self.client.connect()
        
        if not await self.client.is_user_authorized():
            print("❌ Не авторизован!")
            return False
        
        me = await self.client.get_me()
        print(f"✅ Вход: {me.first_name}")
        return True
    
    def db_connect(self):
        self.conn = sqlite3.connect('analytics.db')
        return self.conn.cursor()
    
    def db_commit(self):
        self.conn.commit()
    
    def db_close(self):
        self.conn.close()
    
    async def parse_channel(self, channel_username):
        print(f"\n{'='*50}")
        print(f"📡 @{channel_username} (за 365 дней)")
        print('='*50)
        
        try:
            channel = await self.client.get_entity(channel_username)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return
        
        date_from = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
        
        posts_count = 0
        comments_count = 0
        reactions_count = 0
        users_set = set()
        
        c = self.db_connect()
        
        async for msg in self.client.iter_messages(channel, limit=5000):
            if msg.date < date_from:
                break
            
            if isinstance(msg, MessageService):
                continue
            
            text = msg.text or ""
            views = msg.views or 0
            forwards = msg.forwards or 0
            replies = msg.replies.replies if msg.replies else 0
            
            has_photo = 1 if msg.photo else 0
            has_video = 1 if msg.video else 0
            has_document = 1 if msg.document else 0
            
            c.execute('''INSERT OR REPLACE INTO posts 
                (channel, message_id, date, text, views, forwards, replies, has_photo, has_video, has_document)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (channel_username, msg.id, msg.date.isoformat(), text[:5000], 
                 views, forwards, replies, has_photo, has_video, has_document))
            
            posts_count += 1
            
            if msg.reactions:
                for r in msg.reactions.results:
                    emoji = r.reaction.emoticon if hasattr(r.reaction, 'emoticon') else str(r.reaction)
                    c.execute('''INSERT OR REPLACE INTO reactions 
                        (post_id, channel, emoji, count)
                        VALUES (?, ?, ?, ?)''',
                        (msg.id, channel_username, emoji, r.count))
                    reactions_count += 1
            
            if PARSE_COMMENTS and msg.replies and msg.replies.replies > 0:
                try:
                    async for comment in self.client.iter_messages(
                        channel, reply_to=msg.id, limit=MAX_COMMENTS_PER_POST
                    ):
                        if isinstance(comment, MessageService):
                            continue
                        
                        user_id = comment.sender_id or 0
                        username = ""
                        first_name = ""
                        last_name = ""
                        
                        if comment.sender:
                            username = getattr(comment.sender, 'username', '') or ''
                            first_name = getattr(comment.sender, 'first_name', '') or ''
                            last_name = getattr(comment.sender, 'last_name', '') or ''
                        
                        c.execute('''INSERT OR IGNORE INTO comments 
                            (post_id, channel, user_id, username, first_name, date, text, reply_to)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                            (msg.id, channel_username, user_id, username, first_name,
                             comment.date.isoformat(), (comment.text or "")[:2000], 
                             comment.reply_to_msg_id if comment.reply_to else None))
                        
                        comments_count += 1
                        
                        if user_id:
                            users_set.add(user_id)
                            c.execute('''INSERT INTO users (user_id, username, first_name, last_name, first_seen, last_seen)
                                VALUES (?, ?, ?, ?, ?, ?)
                                ON CONFLICT(user_id) DO UPDATE SET
                                    username = excluded.username,
                                    last_seen = excluded.last_seen''',
                                (user_id, username, first_name, last_name,
                                 comment.date.isoformat(), comment.date.isoformat()))
                            
                            c.execute('''INSERT INTO user_stats (user_id, channel, comments_count, first_activity, last_activity)
                                VALUES (?, ?, 1, ?, ?)
                                ON CONFLICT(user_id, channel) DO UPDATE SET
                                    comments_count = comments_count + 1,
                                    last_activity = excluded.last_activity''',
                                (user_id, channel_username, comment.date.isoformat(), comment.date.isoformat()))
                    
                    await asyncio.sleep(0.3)
                except FloodWaitError as e:
                    print(f"   ⏳ Ждём {e.seconds} сек...")
                    await asyncio.sleep(e.seconds)
                except:
                    pass
            
            if posts_count % 50 == 0:
                print(f"   📝 {posts_count} постов | 💬 {comments_count} комментов")
                self.db_commit()
        
        self.db_commit()
        self.db_close()
        
        print(f"\n✅ @{channel_username}:")
        print(f"   📝 Постов: {posts_count}")
        print(f"   💬 Комментов: {comments_count}")
        print(f"   ❤️ Реакций: {reactions_count}")
        print(f"   👤 Юзеров: {len(users_set)}")
    
    async def run(self):
        if not await self.connect():
            return
        
        for channel in CHANNELS:
            await self.parse_channel(channel)
        
        await self.client.disconnect()
        
        conn = sqlite3.connect('analytics.db')
        c = conn.cursor()
        print(f"\n{'='*50}")
        print("📊 ИТОГО:")
        c.execute("SELECT COUNT(*) FROM posts")
        print(f"   📝 Постов: {c.fetchone()[0]}")
        c.execute("SELECT COUNT(*) FROM comments")
        print(f"   💬 Комментов: {c.fetchone()[0]}")
        c.execute("SELECT COUNT(*) FROM users")
        print(f"   👤 Юзеров: {c.fetchone()[0]}")
        conn.close()

if __name__ == "__main__":
    init_db()
    parser = TelegramParser()
    asyncio.run(parser.run())
