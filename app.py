import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import json

if not firebase_admin._apps:
    try:
        firebase_key = st.secrets["firebase_key"]
        cred = credentials.Certificate(firebase_key)
        firebase_admin.initialize_app(cred)
        st.sidebar.success("Подключено к Firebase (через st.secrets)")
    except KeyError:

        KEY_PATH = "serviceAccountKey.json"
        if os.path.exists(KEY_PATH):
            cred = credentials.Certificate(KEY_PATH)
            firebase_admin.initialize_app(cred)
            st.sidebar.info(" Подключено к Firebase (локальный файл)")
        else:
            st.error("Ошибка: файл serviceAccountKey.json не найден и st.secrets не настроен!")
            st.stop()

db = firestore.client()

st.set_page_config(page_title="Опрос: Карьерные ожидания", layout="wide")
st.title("Карьерные ожидания выпускников")
st.markdown("Участие анонимное. Опрос состоит из 10 вопросов. Данные используются исключительно в учебных целях для анализа рынка труда.")

with st.form("career_survey"):
    st.subheader("Анкета соискателя")

    specialty = st.text_input(
        "1. Ваша специальность / Факультет", 
        placeholder="Например: Технология разработки программного обеспечения, Экономика, Менеджмент"
    )

    education_level = st.radio(
        "2. Ваш уровень образования", 
        ["Бакалавриат", "Магистратура", "Специалитет", "Уже выпускник"]
    )

    industry = st.selectbox(
        "3. Желаемая сфера деятельности", 
        ["IT / Разработка", "Финансы / Банки", "Маркетинг / Реклама", 
         "HR / Управление персоналом", "Государственная служба", 
         "Производство / Инженерия", "Образование / Наука", "Другое"]
    )

    expected_salary = st.selectbox(
        "4. Ожидаемый уровень зарплаты (на руки)", 
        ["До 40 000 руб.", "40 000 - 80 000 руб.", "80 000 - 120 000 руб.", 
         "120 000 - 200 000 руб.", "Более 200 000 руб."]
    )

    work_format = st.radio(
        "5. Предпочитаемый формат работы", 
        ["Строгий офис", "Удалённая работа (Remote)", 
         "Гибридный формат", "Не имеет значения"]
    )

    company_type = st.selectbox(
        "6. Тип компании, в которой вы хотите работать", 
        ["Крупная корпорация (Газпром, Сбер и т.п.)", 
         "Международная компания", 
         "Стартап / IT-компания", 
         "Малый / Средний бизнес", 
         "Государственная организация"]
    )

    priorities = st.multiselect(
        "7. Что для вас важнее всего в работе? (до 3 пунктов)", 
        ["Высокая зарплата", "Стабильность компании", "Карьерный рост", 
         "Обучение и развитие", "Дружный коллектив", "Свободный график", 
         "ДМС и соцпакет", "Известность бренда"]
    )

    confidence = st.slider(
        "8. Уверенность в успешном трудоустройстве (1 — совсем не уверен, 10 — полностью уверен)", 
        1, 10, 5
    )

    fears = st.multiselect(
        "9. Ваши главные страхи при трудоустройстве?", 
        ["Нет опыта работы", "Низкие зарплаты на старте", 
         "Сложно пройти собеседование", "Не по специальности", 
         "Высокая конкуренция", "Придётся переезжать", 
         "Нет актуальных вакансий", "Страхов нет"]
    )

    ready_to_relocate = st.checkbox(
        "10. Готов(а) к переезду в другой город/страну ради работы"
    )

    comment = st.text_area("Дополнительные комментарии или пожелания работодателям (необязательно)")
    
    submitted = st.form_submit_button("Отправить ответы", use_container_width=True)

if submitted:
    if not specialty:
        st.warning("Пожалуйста, укажите вашу специальность (вопрос 1)!")
    elif not priorities:
        st.warning("Выберите хотя бы один приоритет (вопрос 7)!")
    else:
        record = {
            "specialty": specialty,
            "education_level": education_level,
            "industry": industry,
            "salary": expected_salary,
            "format": work_format,
            "company_type": company_type,
            "priorities": priorities,
            "confidence": int(confidence),
            "fears": fears,
            "relocation": ready_to_relocate,
            "comment": comment,
            "timestamp": datetime.utcnow()
        }
        try:
            db.collection("career_responses").add(record)
            st.success("Спасибо! Ваши ответы успешно сохранены в облако.")
            st.balloons()
        except Exception as e:
            st.error(f"Ошибка при сохранении: {e}")

st.divider()
if st.checkbox("Показать аналитику (Режим преподавателя/аналитика)"):
    st.subheader("Дашборд собранных данных")
    
    docs = db.collection("career_responses").stream()
    data = [doc.to_dict() for doc in docs]
    
    if not data:
        st.info("Пока нет ответов. Будьте первым!")
    else:
        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        st.markdown("### Экспорт данных")
        col_exp1, col_exp2 = st.columns(2)

        csv_data = df.to_csv(index=False, encoding='utf-8-sig')
        col_exp1.download_button(
            label="Скачать CSV",
            data=csv_data,
            file_name=f"survey_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

        df_export = df.copy()

        for col in df_export.columns:
            if pd.api.types.is_datetime64_any_dtype(df_export[col]):
                if df_export[col].dt.tz is not None:
                    df_export[col] = df_export[col].dt.tz_localize(None)

        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Answers')
        excel_buffer.seek(0)
        
        col_exp2.download_button(
            label="Скачать Excel",
            data=excel_buffer,
            file_name=f"survey_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        st.divider()

        tab1, tab2, tab3, tab4 = st.tabs([
            "Сырые данные", 
            "Зарплата и Сфера", 
            "Формат и Компания", 
            "Приоритеты и Страхи"
        ])

        with tab1:
            st.dataframe(df, use_container_width=True)
            st.caption(f"Всего собрано ответов: {len(df)}")

        with tab2:
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Ожидаемая зарплата**")
                fig_salary = px.bar(
                    df, x='salary', 
                    title="Распределение по зарплатным ожиданиям",
                    color_discrete_sequence=['#636EFA']
                )
                st.plotly_chart(fig_salary, use_container_width=True)
                
            with col_b:
                st.markdown("**Желаемая сфера деятельности**")
                fig_industry = px.pie(
                    df, names='industry', hole=0.4, 
                    title="Популярность сфер",
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                st.plotly_chart(fig_industry, use_container_width=True)

        with tab3:
            col_c, col_d = st.columns(2)
            with col_c:
                st.markdown("**Формат работы**")
                fig_format = px.pie(
                    df, names='format', hole=0.4, 
                    title="Предпочтения по формату",
                    color_discrete_sequence=px.colors.sequential.RdBu
                )
                st.plotly_chart(fig_format, use_container_width=True)
                
            with col_d:
                st.markdown("**Тип компании мечты**")
                fig_company = px.bar(
                    df, x='company_type', 
                    title="Предпочтения по типу компании",
                    color_discrete_sequence=['#EF553B']
                )
                st.plotly_chart(fig_company, use_container_width=True)

        with tab4:
            st.markdown("**Общая статистика**")
            avg_conf = df['confidence'].mean()
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("Средняя оценка уверенности", f"{avg_conf:.1f} / 10")
            with col_m2:
                reloc_yes = int(df['relocation'].sum())
                st.metric("Готовы к переезду", f"{reloc_yes} чел. ({reloc_yes/len(df)*100:.0f}%)")
            with col_m3:
                st.metric("Всего ответов", f"{len(df)}")

            fig_conf = px.histogram(
                df, x='confidence', nbins=10, 
                title="Распределение уверенности (1-10)",
                color_discrete_sequence=['#00CC96']
            )
            st.plotly_chart(fig_conf, use_container_width=True)

            col_e, col_f = st.columns(2)
            
            with col_e:
                st.markdown("**Главные приоритеты в работе**")
                priorities_flat = [p for plist in df['priorities'] for p in plist]
                if priorities_flat:
                    pr_df = pd.DataFrame(priorities_flat, columns=['priority'])
                    pr_counts = pr_df['priority'].value_counts().reset_index()
                    pr_counts.columns = ['Приоритет', 'Количество']
                    fig_pr = px.bar(
                        pr_counts, x='Количество', y='Приоритет', 
                        orientation='h', color='Количество',
                        color_continuous_scale='Viridis'
                    )
                    st.plotly_chart(fig_pr, use_container_width=True)
                else:
                    st.info("Нет данных")
            
            with col_f:
                st.markdown("**Главные страхи при трудоустройстве**")
                fears_flat = [f for flist in df['fears'] for f in flist]
                if fears_flat:
                    fr_df = pd.DataFrame(fears_flat, columns=['fear'])
                    fr_counts = fr_df['fear'].value_counts().reset_index()
                    fr_counts.columns = ['Страх', 'Количество']
                    fig_fr = px.bar(
                        fr_counts, x='Количество', y='Страх', 
                        orientation='h', color='Количество',
                        color_continuous_scale='Reds'
                    )
                    st.plotly_chart(fig_fr, use_container_width=True)
                else:
                    st.info("Нет данных")
