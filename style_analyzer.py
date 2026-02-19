import sqlite3
import re
from collections import Counter

class StyleAnalyzer:
    def __init__(self, db_path='analytics.db'):
        self.db_path = db_path
    
    def analyze(self, channel):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT text FROM posts WHERE channel = ? AND text IS NOT NULL', (channel,))
        posts = [row[0] for row in c.fetchall() if row[0]]
        conn.close()
        
        if not posts:
            return "❌ Нет постов для анализа"
        
        result = {
            'channel': channel,
            'posts_count': len(posts),
            'structure': self._analyze_structure(posts),
            'vocabulary': self._analyze_vocabulary(posts),
            'tone': self._analyze_tone(posts),
            'formatting': self._analyze_formatting(posts),
            'hooks': self._extract_hooks(posts),
            'cta': self._extract_cta(posts),
        }
        result['prompt'] = self._generate_prompt(result)
        return result
    
    def _analyze_structure(self, posts):
        lengths = [len(p) for p in posts]
        sentences = [len(re.findall(r'[.!?]+', p)) for p in posts]
        paragraphs = [len(p.split('\n\n')) for p in posts]
        return {
            'avg_length': int(sum(lengths) / len(lengths)),
            'avg_sentences': round(sum(sentences) / len(sentences), 1),
            'avg_paragraphs': round(sum(paragraphs) / len(paragraphs), 1),
            'short': len([p for p in posts if len(p) < 300]),
            'medium': len([p for p in posts if 300 <= len(p) < 1000]),
            'long': len([p for p in posts if len(p) >= 1000])
        }
    
    def _analyze_vocabulary(self, posts):
        all_text = ' '.join(posts).lower()
        words = re.findall(r'[а-яёa-z]+', all_text)
        stop = {'и', 'в', 'на', 'с', 'что', 'как', 'это', 'не', 'а', 'но', 'по', 'к', 'из', 'за', 'то', 'все', 'от', 'так', 'же', 'для', 'вы', 'мы', 'он', 'она', 'они', 'я', 'ты', 'у', 'о', 'бы'}
        filtered = [w for w in words if w not in stop and len(w) > 2]
        freq = Counter(filtered).most_common(30)
        
        bigrams = []
        for post in posts:
            w = re.findall(r'[а-яёa-z]+', post.lower())
            bigrams.extend([f"{w[i]} {w[i+1]}" for i in range(len(w)-1)])
        bigram_freq = Counter(bigrams).most_common(15)
        
        return {'top_words': freq, 'top_phrases': bigram_freq}
    
    def _analyze_tone(self, posts):
        all_text = ' '.join(posts).lower()
        markers = {
            'formal': ['уважаемые', 'предлагаем', 'рекомендуем'],
            'casual': ['кстати', 'ну', 'вообще', 'короче', 'круто'],
            'expert': ['исследования', 'данные', 'статистика', 'анализ'],
            'emotional': ['!', '🔥', '💪', 'вау', 'супер', 'класс'],
            'personal': ['я ', 'мой', 'моя', 'мне'],
        }
        scores = {tone: sum(all_text.count(w) for w in words) for tone, words in markers.items()}
        dominant = max(scores, key=scores.get)
        return {
            'dominant': dominant,
            'exclamations': all_text.count('!'),
            'questions': all_text.count('?'),
            'emoji': len(re.findall(r'[\U0001F300-\U0001F9FF]', ' '.join(posts)))
        }
    
    def _analyze_formatting(self, posts):
        return {
            'emoji': any(re.search(r'[\U0001F300-\U0001F9FF]', p) for p in posts),
            'lists': any(re.search(r'^[\-•]\s', p, re.MULTILINE) for p in posts),
            'links': sum(1 for p in posts if 'http' in p or 't.me' in p),
            'hashtags': sum(len(re.findall(r'#\w+', p)) for p in posts),
        }
    
    def _extract_hooks(self, posts):
        hooks = []
        for post in posts[:20]:
            first = post.split('\n')[0].strip()
            if len(first) > 10:
                hooks.append(first[:100])
        return hooks
    
    def _extract_cta(self, posts):
        patterns = [r'подпис\w+', r'переход\w+', r'жми', r'читай', r'смотри', r'пиши', r'ссылк']
        ctas = []
        for post in posts:
            last = post[-200:] if len(post) > 200 else post
            for pat in patterns:
                if re.search(pat, last.lower()):
                    for sent in re.split(r'[.!?\n]', last):
                        if re.search(pat, sent.lower()) and len(sent.strip()) > 5:
                            ctas.append(sent.strip())
                            break
        return list(set(ctas))[:10]
    
    def _generate_prompt(self, a):
        s, t = a['structure'], a['tone']
        return f"""Пиши как автор канала @{a['channel']}.

СТРУКТУРА: ~{s['avg_length']} символов, {s['avg_sentences']} предложений, {s['avg_paragraphs']} абзацев.

ТОН: {t['dominant']}. {'Много восклицаний!' if t['exclamations'] > a['posts_count'] else 'Спокойно'}. {'Вопросы читателю' if t['questions'] > a['posts_count'] else 'Утверждения'}.

ЧАСТЫЕ СЛОВА: {', '.join([w[0] for w in a['vocabulary']['top_words'][:15]])}

ФРАЗЫ: {', '.join([w[0] for w in a['vocabulary']['top_phrases'][:10]])}

ХУКИ:
{chr(10).join(['• ' + h for h in a['hooks'][:5]])}

CTA:
{chr(10).join(['• ' + c for c in a['cta'][:5]])}"""

    def print_report(self, channel):
        r = self.analyze(channel)
        if isinstance(r, str):
            print(r)
            return
        
        print(f"\n{'='*60}")
        print(f"📊 АНАЛИЗ СТИЛЯ @{r['channel']}")
        print(f"{'='*60}")
        print(f"📝 Постов: {r['posts_count']}")
        
        s = r['structure']
        print(f"\n📐 СТРУКТУРА:")
        print(f"   Длина: {s['avg_length']} симв | Предложений: {s['avg_sentences']} | Абзацев: {s['avg_paragraphs']}")
        print(f"   Коротких: {s['short']} | Средних: {s['medium']} | Длинных: {s['long']}")
        
        t = r['tone']
        print(f"\n🎭 ТОН: {t['dominant']}")
        print(f"   ! = {t['exclamations']} | ? = {t['questions']} | emoji = {t['emoji']}")
        
        print(f"\n📚 ТОП СЛОВА: {', '.join([w[0] for w in r['vocabulary']['top_words'][:15]])}")
        print(f"\n🔗 ТОП ФРАЗЫ: {', '.join([w[0] for w in r['vocabulary']['top_phrases'][:10]])}")
        
        print(f"\n🪝 ХУКИ:")
        for h in r['hooks'][:5]:
            print(f"   • {h}")
        
        print(f"\n📢 CTA:")
        for c in r['cta'][:5]:
            print(f"   • {c}")
        
        print(f"\n{'='*60}")
        print("🤖 ПРОМПТ:")
        print(f"{'='*60}")
        print(r['prompt'])

if __name__ == '__main__':
    import sys
    channel = sys.argv[1] if len(sys.argv) > 1 else 'yourfit_store'
    StyleAnalyzer().print_report(channel)
