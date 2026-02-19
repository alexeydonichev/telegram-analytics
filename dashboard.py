import streamlit as st
import sqlite3
import pandas as pd
from style_analyzer import StyleAnalyzer

st.set_page_config(page_title="Telegram Analytics", layout="wide")

conn = sqlite3.connect('analytics.db')
channels = pd.read_sql("SELECT DISTINCT channel FROM posts", conn)['channel'].tolist()

st.title("📊 Telegram Analytics Dashboard")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 Посты", "👥 Юзеры", "📈 Тренды", "🏆 Топы", "🎨 Стиль"])

with tab1:
    st.header("Посты")
    selected = st.selectbox("Канал", channels, key="posts_channel")
    posts = pd.read_sql(f"SELECT * FROM posts WHERE channel = '{selected}' ORDER BY date DESC LIMIT 50", conn)
    st.dataframe(posts)

with tab2:
    st.header("Комментаторы")
    try:
        users = pd.read_sql("SELECT * FROM commenters ORDER BY comments_count DESC LIMIT 100", conn)
        st.dataframe(users)
    except:
        st.info("Нет данных о комментаторах")

with tab3:
    st.header("Тренды по датам")
    selected = st.selectbox("Канал", channels, key="trends_channel")
    trends = pd.read_sql(f"""
        SELECT date, COUNT(*) as posts, SUM(views) as views, SUM(forwards) as forwards
        FROM posts WHERE channel = '{selected}'
        GROUP BY date ORDER BY date
    """, conn)
    if not trends.empty:
        st.line_chart(trends.set_index('date')[['views', 'forwards']])

with tab4:
    st.header("Топ посты по просмотрам")
    selected = st.selectbox("Канал", channels, key="tops_channel")
    tops = pd.read_sql(f"""
        SELECT text, views, forwards, date 
        FROM posts WHERE channel = '{selected}' 
        ORDER BY views DESC LIMIT 10
    """, conn)
    for i, row in tops.iterrows():
        with st.expander(f"👁 {row['views']} | 🔄 {row['forwards']} | {row['date']}"):
            st.write(row['text'][:500] if row['text'] else "—")

with tab5:
    st.header("🎨 Анализ стиля автора")
    selected = st.selectbox("Выберите канал", channels, key="style_channel")
    
    if st.button("🔍 Анализировать стиль", type="primary"):
        analyzer = StyleAnalyzer()
        result = analyzer.analyze(selected)
        
        if isinstance(result, str):
            st.error(result)
        else:
            # Сохраняем в session для генерации
            st.session_state['style_result'] = result
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📝 Постов проанализировано", result['posts_count'])
            with col2:
                st.metric("📏 Средняя длина", f"{result['structure']['avg_length']} симв")
            with col3:
                st.metric("🎭 Тон", result['tone']['dominant'])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("❗ Восклицания", result['tone']['exclamations'])
            with col2:
                st.metric("❓ Вопросы", result['tone']['questions'])
            with col3:
                st.metric("😀 Emoji", result['tone']['emoji'])
            
            st.subheader("📐 Структура постов")
            s = result['structure']
            st.write(f"• Предложений: **{s['avg_sentences']}** в среднем")
            st.write(f"• Абзацев: **{s['avg_paragraphs']}** в среднем")
            st.write(f"• Коротких (<300): **{s['short']}** | Средних: **{s['medium']}** | Длинных: **{s['long']}**")
            
            st.subheader("📚 Топ-15 слов")
            words = ', '.join([f"**{w[0]}** ({w[1]})" for w in result['vocabulary']['top_words'][:15]])
            st.write(words)
            
            st.subheader("🔗 Топ-10 фраз")
            phrases = ', '.join([f"**{w[0]}** ({w[1]})" for w in result['vocabulary']['top_phrases'][:10]])
            st.write(phrases)
            
            st.subheader("🪝 Примеры хуков")
            for h in result['hooks'][:5]:
                st.write(f"• {h}")
            
            st.subheader("📢 Примеры CTA")
            for c in result['cta'][:5]:
                st.write(f"• {c}")
            
            st.subheader("🤖 Промпт для подражания")
            st.code(result['prompt'], language=None)
            st.download_button("📋 Скачать промпт", result['prompt'], f"prompt_{selected}.txt")
    
    # Генерация поста
    st.divider()
    st.subheader("✍️ Написать пост в стиле автора")
    
    topic = st.text_input("Тема поста", placeholder="Например: новая коллекция леггинсов")
    
    col1, col2 = st.columns(2)
    with col1:
        post_type = st.selectbox("Тип поста", ["Анонс продукта", "Вовлечение", "Полезный контент", "Акция/скидка", "Опрос"])
    with col2:
        length = st.selectbox("Длина", ["Короткий (~200 симв)", "Средний (~500 симв)", "Длинный (~1000 симв)"])
    
    if st.button("✨ Сгенерировать пост", type="primary"):
        if 'style_result' not in st.session_state:
            st.warning("Сначала проанализируйте стиль канала")
        elif not topic:
            st.warning("Введите тему поста")
        else:
            r = st.session_state['style_result']
            
            # Формируем промпт для генерации
            gen_prompt = f"""{r['prompt']}

ЗАДАЧА: Напиши {post_type.lower()} на тему: {topic}
ДЛИНА: {length}

Используй стиль автора. Начни с хука. Закончи CTA."""

            st.subheader("📝 Промпт для Claude/ChatGPT:")
            st.code(gen_prompt, language=None)
            
            st.download_button(
                "📋 Скопировать промпт", 
                gen_prompt, 
                f"generate_{selected}_{topic[:20]}.txt"
            )
            
            st.info("👆 Скопируй этот промпт в Claude или ChatGPT для генерации поста")

conn.close()
