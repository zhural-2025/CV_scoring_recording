import streamlit as st
from openai import OpenAI
from requests_html import HTMLSession
from bs4 import BeautifulSoup


# --- Настройки ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

SYSTEM_PROMPT = """
Проскорь кандидата, насколько он подходит для данной вакансии.
Сначала напиши короткий анализ, который будет пояснять оценку.
Отдельно оцени качество заполнения резюме (понятно ли, с какими задачами сталкивался кандидат и каким образом их решал?). 
Эта оценка должна учитываться при выставлении финальной оценки — нам важно нанимать таких кандидатов, которые могут рассказать про свою работу.
Потом представь результат в виде оценки от 1 до 10.
""".strip()

# --- ПАРСЕР HH ---
COOKIES = {
    # 'hhuid': 'ваш_cookie_если_парсите_резюме'
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def get_html(url: str) -> str:
    """Загружает HTML-страницу с рендерингом JS."""
    session = HTMLSession()
    r = session.get(url, headers=HEADERS, cookies=COOKIES)
    try:
        r.html.render(timeout=30, sleep=3)
    except Exception as e:
        print(f"[!] Ошибка рендера JS: {e}")
    return r.html.html


def extract_vacancy_data(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    def safe_text(tag, attrs=None):
        el = soup.find(tag, attrs or {})
        return el.get_text(strip=True) if el else "Не найдено"

    title = safe_text("h1")
    salary = safe_text("span", {"data-qa": "vacancy-salary"})
    company = safe_text("a", {"data-qa": "vacancy-company-name"})
    description = soup.find("div", {"data-qa": "vacancy-description"})
    description_text = description.get_text(separator="\n").strip() if description else "Описание не найдено"

    markdown = f"# {title}\n\n**Компания:** {company}\n\n**Зарплата:** {salary}\n\n## Описание\n\n{description_text}"
    return markdown.strip()


def extract_resume_data(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    def safe_text(tag, attrs=None):
        """
        Возвращает текст из первого найденного тега.
        attrs может быть словарём атрибутов (например {'data-qa': '...'}) или None.
        """
        if attrs:
            el = soup.find(tag, attrs=attrs)
        else:
            el = soup.find(tag)
        return el.get_text(strip=True) if el else "Не найдено"

    name = safe_text("h2", {"data-qa": "resume-personal-name"})
    gender_age = safe_text("p")
    location = safe_text("span", {"data-qa": "resume-personal-address"})
    job_title = safe_text("span", {"data-qa": "resume-block-title-position"})
    job_status = safe_text("span", {"data-qa": "job-search-status"})

    experiences = []
    exp_section = soup.find("div", {"data-qa": "resume-block-experience"})
    if exp_section:
        items = exp_section.find_all("div", class_="resume-block-item-gap")
        for item in items:
            try:
                period_el = item.find("div", class_="bloko-column_s-2")
                period = period_el.get_text(strip=True) if period_el else "Период не указан"

                company_el = item.find("div", class_="bloko-text_strong")
                company = company_el.get_text(strip=True) if company_el else "Компания не указана"

                position_el = item.find("div", {"data-qa": "resume-block-experience-position"})
                position = position_el.get_text(strip=True) if position_el else "Должность не указана"

                desc_el = item.find("div", {"data-qa": "resume-block-experience-description"})
                desc = desc_el.get_text(strip=True) if desc_el else ""

                experiences.append(f"**{period}** — *{company}*, {position}\n{desc}")
            except Exception:
                continue

    skills_section = soup.find("div", {"data-qa": "skills-table"})
    skills = []
    if skills_section:
        tags = skills_section.find_all("span", {"data-qa": "bloko-tag__text"})
        skills = [tag.get_text(strip=True) for tag in tags]

    markdown = f"# {name}\n\n**{gender_age}**\n\n**Местоположение:** {location}\n\n**Должность:** {job_title}\n\n**Статус:** {job_status}\n\n## Опыт работы\n\n"
    markdown += "\n".join(experiences) if experiences else "Опыт работы не найден.\n"
    markdown += "\n## Ключевые навыки\n\n" + (", ".join(skills) if skills else "Навыки не указаны.\n")
    return markdown.strip()

# --- GPT ---
def request_gpt(system_prompt, user_prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=1000,
        temperature=0,
    )
    return response.choices[0].message.content


# --- Streamlit UI ---
st.title('CV Scoring App')

job_url = st.text_input('Введите ссылку на вакансию с hh.ru')
resume_url = st.text_input('Введите ссылку на резюме с hh.ru')

if st.button("Проанализировать соответствие"):
    with st.spinner("Парсим данные и отправляем в GPT..."):
        try:
            # Получаем HTML страниц
            job_html = get_html(job_url)
            resume_html = get_html(resume_url)

            # Извлекаем текст
            job_text = extract_vacancy_data(job_html)
            resume_text = extract_resume_data(resume_html)

            # Формируем промпт
            prompt = f"# ВАКАНСИЯ\n{job_text}\n\n# РЕЗЮМЕ\n{resume_text}"

            # Отправляем в GPT
            response = request_gpt(SYSTEM_PROMPT, prompt)

            # Вывод результата
            st.subheader("📊 Результат анализа:")
            st.markdown(response)

        except Exception as e:
            st.error(f"Произошла ошибка: {e}")
