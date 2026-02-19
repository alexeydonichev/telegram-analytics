import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from style_analyzer import StyleAnalyzer

st.set_page_config(page_title="Telegram Analytics Pro", layout="wide")

# === CSS для красоты ===
st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    .stMetric {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
               padding: 15px; border-radius: 10px; color: white;}
    .stMetric label {color: white !important;}
    .stMetric [data-testid="stMetricValue"] {color: white !important;}
</style>
""", unsafe_allow_html=True)

# === ДАННЫЕ ===
@st.cache_data
def get_channels():
    conn = sqlite3.connect('analytics.db')
    df = pd.read_sql('SELECT DISTINCT channel FROM posts', conn)
    conn.close()
    return df['channel'].tolist()

@st.cache_data
def load_posts(channel):
    conn = sqlite3.connect('analytics.db')
    df = pd.read_sql('SELECT * FROM posts WHERE channel = ?', conn, params=[channel])
    conn.close()
    if len(df) == 0:
        return df
    df['date'] = pd.to_datetime(df['date'])
    df['hour'] = df['date'].dt.hour
    df['weekday'] = df['date'].dt.day_name()
    df['month'] = df['date'].dt.to_period('M').astype(str)
    df['date_only'] = df['date'].dt.date
    df['text_len'] = df['text'].str.len().fillna(0)
    df['content_type'] = df.apply(
        lambda r: 'Видео' if r['has_video'] else ('Фото' if r['has_photo'] else 'Текст'), axis=1)
    return df

@st.cache_data
def load_comments(channel):
    try:
        conn = sqlite3.connect('analytics.db')
        df = pd.read_sql('SELECT * FROM comments WHERE channel = ?', conn, params=[channel])
        conn.close()
        if len(df) > 0:
            df['date'] = pd.to_datetime(df['date'])
        return df
    except:
        return pd.DataFrame()

@st.cache_data
def load_reactions(channel):
    try:
        conn = sqlite3.connect('analytics.db')
        df = pd.read_sql('SELECT * FROM reactions WHERE channel = ?', conn, params=[channel])
        conn.close()
        return df
    except:
        return pd.DataFrame()

@st.cache_data
def load_users(channel):
    try:
        conn = sqlite3.connect('analytics.db')
        df = pd.read_sql('''
            SELECT u.user_id, u.username, u.first_name, 
                   us.comments_count, us.first_activity, us.last_activity
            FROM users u
            LEFT JOIN user_stats us ON u.user_id = us.user_id
            WHERE us.channel = ?
            ORDER BY us.comments_count DESC
        ''', conn, params=[channel])
        conn.close()
        return df
    except:
        return pd.DataFrame()

# === SIDEBAR ===
st.sidebar.title("⚙️ Настройки")
channels = get_channels()
selected_channel = st.sidebar.selectbox("📺 Канал", channels)

st.sidebar.divider()
st.sidebar.markdown("### 🔧 Инструменты")
if st.sidebar.button("🔄 Обновить данные"):
    st.cache_data.clear()
    st.rerun()

# === ЗАГРУЗКА ===
posts = load_posts(selected_channel)
comments = load_comments(selected_channel)
reactions = load_reactions(selected_channel)
users = load_users(selected_channel)

# === HEADER ===
st.title(f"📊 @{selected_channel}")

if len(posts) > 0:
    st.markdown(f"📅 {posts['date'].min().strftime('%d.%m.%Y')} — {posts['date'].max().strftime('%d.%m.%Y')}")
    
    # === МЕТРИКИ ===
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("📝 Постов", len(posts))
    c2.metric("👀 Ср. просмотры", f"{posts['views'].mean():,.0f}")
    c3.metric("💬 Комментов", len(comments))
    c4.metric("🔄 Ср. репосты", f"{posts['forwards'].mean():.1f}")
    c5.metric("❤️ Реакций", int(reactions['count'].sum()) if len(reactions) > 0 else 0)
    c6.metric("👤 Юзеров", len(users))

    # === ТАБЫ ===
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Аналитика", "👤 Юзеры", "📈 Тренды", "🏆 Топы", "🎨 Стиль"])

    # ===================== TAB 1: АНАЛИТИКА =====================
    with tab1:
        st.subheader("📈 Просмотры по дням")
        daily = posts.groupby('date_only').agg(
            posts_count=('message_id','count'),
            views=('views','sum'),
            comments=('replies','sum')
        ).reset_index()
        fig = px.bar(daily, x='date_only', y='views', color='views',
            color_continuous_scale='Blues', labels={'date_only':'Дата','views':'Просмотры'})
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("⏰ Лучшее время")
            hourly = posts.groupby('hour')['views'].mean().reset_index()
            fig = px.bar(hourly, x='hour', y='views', color='views',
                color_continuous_scale='Greens', labels={'hour':'Час','views':'Ср. просмотры'})
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            best_hour = hourly.loc[hourly['views'].idxmax(), 'hour']
            st.success(f"🎯 Лучшее время: **{int(best_hour)}:00**")

        with col2:
            st.subheader("📅 Лучший день")
            days_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
            days_ru = {'Monday':'Пн','Tuesday':'Вт','Wednesday':'Ср','Thursday':'Чт',
                       'Friday':'Пт','Saturday':'Сб','Sunday':'Вс'}
            weekly = posts.groupby('weekday')['views'].mean().reindex(days_order).reset_index()
            weekly['day_ru'] = weekly['weekday'].map(days_ru)
            fig = px.bar(weekly, x='day_ru', y='views', color='views',
                color_continuous_scale='Oranges', labels={'day_ru':'День','views':'Ср. просмотры'})
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            best_day = weekly.loc[weekly['views'].idxmax(), 'day_ru']
            st.success(f"🎯 Лучший день: **{best_day}**")

        st.subheader("📊 Эффективность по типу контента")
        content_stats = posts.groupby('content_type').agg(
            count=('message_id','count'),
            avg_views=('views','mean'),
            avg_comments=('replies','mean')
        ).reset_index()
        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(content_stats, values='count', names='content_type', 
                         title='Распределение постов', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.bar(content_stats, x='content_type', y='avg_views', color='content_type',
                labels={'content_type':'Тип','avg_views':'Ср. просмотры'}, title='Просмотры по типу')
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # ===================== TAB 2: ЮЗЕРЫ =====================
    with tab2:
        st.subheader("👥 Топ комментаторов")
        if len(users) > 0:
            top_users = users.head(20)
            fig = px.bar(top_users, x='username', y='comments_count',
                color='comments_count', color_continuous_scale='Purples',
                labels={'username':'Юзер','comments_count':'Комментов'})
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("📋 Полный список")
            st.dataframe(users.head(100), use_container_width=True, height=400)
        else:
            st.info("💡 Данные о юзерах появятся после парсинга комментариев")

    # ===================== TAB 3: ТРЕНДЫ =====================
    with tab3:
        st.subheader("📈 Динамика по месяцам")
        monthly = posts.groupby('month').agg(
            posts=('message_id','count'),
            views=('views','sum'),
            avg_views=('views','mean')
        ).reset_index()
        
        col1, col2 = st.columns(2)
        with col1:
            fig = px.line(monthly, x='month', y='avg_views', markers=True,
                labels={'month':'Месяц','avg_views':'Ср. просмотры'}, title='Средние просмотры')
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.bar(monthly, x='month', y='posts', color='posts',
                color_continuous_scale='Viridis', labels={'month':'Месяц','posts':'Постов'}, 
                title='Количество постов')
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        if len(comments) > 0:
            st.subheader("💬 Активность комментариев")
            comments_copy = comments.copy()
            comments_copy['month'] = comments_copy['date'].dt.to_period('M').astype(str)
            comm_monthly = comments_copy.groupby('month').size().reset_index(name='count')
            fig = px.area(comm_monthly, x='month', y='count',
                labels={'month':'Месяц','count':'Комментариев'})
            st.plotly_chart(fig, use_container_width=True)

    # ===================== TAB 4: ТОПЫ =====================
    with tab4:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔥 Топ по просмотрам")
            top_views = posts.nlargest(10, 'views')[['date','text','views','replies','forwards']]
            for i, row in top_views.iterrows():
                with st.expander(f"👁 {row['views']:,} | 💬 {row['replies']} | {row['date'].strftime('%d.%m.%Y')}"):
                    st.write(row['text'][:500] if row['text'] else "—")
        
        with col2:
            st.subheader("💬 Топ по комментам")
            top_replies = posts.nlargest(10, 'replies')[['date','text','views','replies','forwards']]
            for i, row in top_replies.iterrows():
                with st.expander(f"💬 {row['replies']} | 👁 {row['views']:,} | {row['date'].strftime('%d.%m.%Y')}"):
                    st.write(row['text'][:500] if row['text'] else "—")

        st.subheader("🔄 Топ по репостам")
        top_forwards = posts.nlargest(5, 'forwards')[['date','text','views','replies','forwards']]
        for i, row in top_forwards.iterrows():
            with st.expander(f"🔄 {row['forwards']} | 👁 {row['views']:,} | {row['date'].strftime('%d.%m.%Y')}"):
                st.write(row['text'][:500] if row['text'] else "—")

    # ===================== TAB 5: СТИЛЬ =====================
    with tab5:
        st.subheader("🎨 Анализ стиля автора")
        
        if st.button("🔍 Анализировать стиль", type="primary", use_container_width=True):
            with st.spinner("Анализирую посты..."):
                analyzer = StyleAnalyzer()
                result = analyzer.analyze(selected_channel)
            
            if isinstance(result, str):
                st.error(result)
            else:
                st.session_state['style_result'] = result
                
                # Метрики стиля
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📝 Постов", result['posts_count'])
                with col2:
                    st.metric("📏 Ср. длина", f"{result['structure']['avg_length']} симв")
                with col3:
                    st.metric("🎭 Тон", result['tone']['dominant'])
                with col4:
                    st.metric("😀 Emoji", result['tone']['emoji'])
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📐 Структура")
                    s = result['structure']
                    struct_data = pd.DataFrame({
                        'Параметр': ['Коротких (<300)', 'Средних (300-1000)', 'Длинных (>1000)'],
                        'Количество': [s['short'], s['medium'], s['long']]
                    })
                    fig = px.pie(struct_data, values='Количество', names='Параметр', hole=0.4)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.write(f"• Предложений: **{s['avg_sentences']}** в среднем")
                    st.write(f"• Абзацев: **{s['avg_paragraphs']}** в среднем")
                
                with col2:
                    st.subheader("📚 Топ-15 слов")
                    words_data = pd.DataFrame(result['vocabulary']['top_words'][:15], 
                                              columns=['Слово', 'Частота'])
                    fig = px.bar(words_data, x='Частота', y='Слово', orientation='h',
                                 color='Частота', color_continuous_scale='Blues')
                    fig.update_layout(height=400, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("🪝 Примеры хуков")
                for h in result['hooks'][:5]:
                    st.info(f"💡 {h}")
                
                st.subheader("📢 Примеры CTA")
                for c in result['cta'][:5]:
                    st.success(f"👉 {c}")
                
                st.subheader("🤖 Готовый промпт")
                st.code(result['prompt'], language=None)
                st.download_button("📋 Скачать промпт", result['prompt'], 
                                   f"prompt_{selected_channel}.txt", use_container_width=True)
        
        # === ГЕНЕРАТОР ПОСТОВ ===
        st.divider()
        st.subheader("✍️ Генератор постов")
        
        topic = st.text_input("📌 Тема поста", placeholder="Например: новая коллекция леггинсов")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            post_type = st.selectbox("📋 Тип", ["Анонс продукта", "Вовлечение", "Полезный контент", "Акция", "Опрос"])
        with col2:
            length = st.selectbox("📏 Длина", ["Короткий (~200)", "Средний (~500)", "Длинный (~1000)"])
        with col3:
            tone = st.selectbox("🎭 Тон", ["Как в канале", "Дружелюбный", "Экспертный", "Продающий"])
        
        if st.button("✨ Создать промпт для генерации", type="primary", use_container_width=True):
            if 'style_result' not in st.session_state:
                st.warning("⚠️ Сначала проанализируйте стиль (кнопка выше)")
            elif not topic:
                st.warning("⚠️ Введите тему поста")
            else:
                r = st.session_state['style_result']
                
                gen_prompt = f"""{r['prompt']}

---
ЗАДАЧА: Напиши {post_type.lower()} на тему: {topic}
ДЛИНА: {length}
ТОН: {tone}

Требования:
1. Начни с цепляющего хука
2. Используй стиль автора канала
3. Добавь emoji как в оригинале
4. Закончи сильным CTA
"""
                st.subheader("📝 Промпт готов!")
                st.code(gen_prompt, language=None)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button("📋 Скачать", gen_prompt, 
                                       f"gen_{selected_channel}_{topic[:15]}.txt", 
                                       use_container_width=True)
                with col2:
                    st.link_button("🤖 Открыть Claude", "https://claude.ai", 
                                   use_container_width=True)

else:
    st.warning("⚠️ Нет данных для этого канала. Запустите парсер.")

# === FOOTER ===
st.sidebar.divider()
st.sidebar.caption("Made with ❤️ for Telegram Analytics")
