from requests_html import HTMLSession
from bs4 import BeautifulSoup

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
    return r.html.html  # возвращаем корректный HTML после render

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
    def safe_text(tag, **attrs):
        el = soup.find(tag, **attrs)
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
                period = item.find("div", class_="bloko-column_s-2").get_text(strip=True)
                company = item.find("div", class_="bloko-text_strong").get_text(strip=True)
                position = item.find("div", {"data-qa": "resume-block-experience-position"}).get_text(strip=True)
                desc = item.find("div", {"data-qa": "resume-block-experience-description"}).get_text(strip=True)
                experiences.append(f"**{period}** — *{company}*, {position}\n{desc}")
            except Exception:
                continue

    skills_section = soup.find("div", {"data-qa": "skills-table"})
    skills = [tag.get_text(strip=True) for tag in skills_section.find_all("span", {"data-qa": "bloko-tag__text"})] if skills_section else []

    markdown = f"# {name}\n\n**{gender_age}**\n\n**Местоположение:** {location}\n\n**Должность:** {job_title}\n\n**Статус:** {job_status}\n\n## Опыт работы\n\n"
    markdown += "\n".join(experiences) if experiences else "Опыт работы не найден.\n"
    markdown += "\n## Ключевые навыки\n\n" + (", ".join(skills) if skills else "Навыки не указаны.\n")
    return markdown.strip()
