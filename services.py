import httpx
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from openai import OpenAI
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from config import YANDEX_FOLDERID, YANDEX_API_KEY, OPENAI_API_KEY
from database import UrlChat

# Initialize OpenAI client
try:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    openai_client = None

async def parse_url_from_message(message_text: str, dialog_id: int) -> Dict[str, Any]:
    """
    Parse the URL and query from the message text
    Similar to Code12 in n8n workflow
    """
    if not message_text:
        return {"error": "No input provided", "dialog_id": dialog_id}
    
    # Remove extra spaces and normalize
    message_text = message_text.strip()
    
    # Check if it's a full URL or domain with a query
    match = re.match(r'^((?:https?:\/\/)?(?:www\.)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?:\/[^\s]*)?)(?:\s+(.*))?$', message_text)
    if match:
        full_site = match.group(1)  # Can be either a link or a domain
        query = match.group(3).strip() if match.group(3) else None
        
        # Make sure the URL has a protocol
        if not (full_site.startswith('http://') or full_site.startswith('https://')):
            full_site = 'https://' + full_site
        
        print(f"Parsed URL: {full_site}, Query: {query or 'None'}")
        
        result = {"site": full_site, "type": "site", "dialog_id": dialog_id}
        if query:
            result["query"] = query
        
        return result
    
    # If it's just a query (without a link or domain)
    print(f"Parsed as query only: {message_text}")
    return {"query": message_text, "type": "queryOnly", "dialog_id": dialog_id}

async def save_url_to_db(db: Session, dialog_id: int, website: str) -> None:
    """
    Save URL to database
    Similar to Postgres3 in n8n workflow
    """
    # Check if record exists
    existing = db.query(UrlChat).filter(
        UrlChat.dialog_id == dialog_id,
        UrlChat.website == website
    ).first()
    
    if existing:
        # Update timestamp
        existing.created_at = UrlChat.created_at.default.arg()
        db.commit()
    else:
        # Create new record
        new_url = UrlChat(dialog_id=dialog_id, website=website)
        db.add(new_url)
        db.commit()

async def get_latest_url(db: Session, dialog_id: int) -> Optional[str]:
    """
    Get the latest URL for a dialog
    Similar to Postgres4 in n8n workflow
    """
    latest = db.query(UrlChat).filter(
        UrlChat.dialog_id == dialog_id
    ).order_by(UrlChat.created_at.desc()).first()
    
    return latest.website if latest else None

async def search_yandex(url: str, query: Optional[str] = None) -> str:
    """
    Search Yandex API for the given URL and query
    Similar to HTTP Request4 and XML2 in n8n workflow
    """
    # Ensure URL is properly formatted for search
    if url and not (url.startswith('http://') or url.startswith('https://')):
        formatted_url = 'https://' + url
    else:
        formatted_url = url
        
    # For domain-only URLs, also try to search just the domain name
    domain_only = re.sub(r'^https?://', '', url)
    
    # Use site: operator for more precise search
    if query:
        search_query = f"site:{domain_only} {query}"
    else:
        search_query = f"site:{domain_only}"
    
    yandex_url = f"https://yandex.ru/search/xml"
    
    params = {
        "folderid": YANDEX_FOLDERID,
        "apikey": YANDEX_API_KEY,
        "query": search_query,
        "l10n": "ru",
        "groupby": "attr%3Dd.mode%3Ddeep"
    }
    
    print(f"Searching Yandex with query: {search_query}")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(yandex_url, params=params, timeout=10.0)
        
    return response.text

async def extract_first_url(xml_content: str) -> List[str]:
    """
    Extract the first URL from Yandex search results
    Similar to Code14 in n8n workflow
    """
    try:
        print("Received XML content from Yandex search")
        if "<error" in xml_content:
            error_match = re.search(r'<error code="(\d+)">([^<]+)</error>', xml_content)
            if error_match:
                error_code = error_match.group(1)
                error_message = error_match.group(2)
                print(f"Yandex API error: Code {error_code}, Message: {error_message}")
                return []
                
        root = ET.fromstring(xml_content)
        urls = []
        
        # Debug: Count the number of groups and docs
        groups = root.findall(".//group")
        print(f"Found {len(groups)} groups in XML response")
        
        # First try to find URLs in doc elements
        for group in groups:
            for doc in group.findall(".//doc"):
                url_elem = doc.find(".//url")
                if url_elem is not None and url_elem.text:
                    print(f"Found URL: {url_elem.text}")
                    urls.append(url_elem.text)
                    if len(urls) >= 1:  # We only need the first URL
                        return urls
        
        # If no URLs found, try to find them in other elements
        if not urls:
            for elem in root.findall(".//*"):
                if elem.tag == "url" and elem.text and "://" in elem.text:
                    print(f"Found URL in alternative element: {elem.text}")
                    urls.append(elem.text)
                    if len(urls) >= 1:
                        return urls
        
        if not urls:
            print("No URLs found in the XML response")
            
        return urls
    except Exception as e:
        print(f"Error parsing XML: {e}")
        # Print a small part of the XML for debugging
        print(f"XML snippet: {xml_content[:200]}...")
        return []

async def fetch_webpage_content(url: str) -> str:
    """
    Fetch and extract content from a webpage
    Similar to HTTP Request5 and Code13 in n8n workflow
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            content = response.text
            return content
        except Exception as e:
            print(f"Error fetching URL {url}: {e}")
            return ""

async def clean_html_content(html_content: str) -> str:
    """
    Clean HTML content
    Similar to Code15 in n8n workflow
    """
    if not html_content or html_content.strip() == '':
        return ""
    
    # Use BeautifulSoup to clean HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text
    text = soup.get_text()
    
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)
    
    return text

async def generate_ai_description(cleaned_text: str) -> str:
    """
    Generate AI description using OpenAI
    Similar to AI Agent2 in n8n workflow
    """
    if not cleaned_text or cleaned_text.strip() == '':
        return "Извините, не удалось получить достаточно информации о сайте."
        
    prompt = f"""
    Роль:
    ТЫ — AI-бот 
    Твоя главная задача — давать краткое описание компании из 'Контекст'.
    Если информации недостаточно, не придумывайте ответ, а прямо сообщите, что информации недостаточно.

    Основные правила:

    1.Используй только предоставленные источники:
    -Отвечай, используя информацию из "Контекста".
    -Запрещено использовать общие знания или любую другую информацию, не содержащуюся в "Контексте".
    -Находи не только точное совпадение, но и: синонимы, однокоренные слова, схожие словосочетания, смежные формулировки.
    -Не пиши системные ошибки в чат
    -Если слово многозначное, попробуй определить его значение, ориентируясь на 'Контекст'. 

    2. Структура и формат ответа:
    -Краткость: давай лаконичные ответы.
    -Читабельность: пиши понятно и удобно для восприятия.
    -Четкость: если информации недостаточно, прямо сообщи об этом.

    3. Ограничения:
    -Не отправляй пользователю системные ошибки.

    ВАЖНО:
    -Всегда проверяйте, следуете ли вы инструкциям!
    -Не используйте свой собственный разум или знания, отвечайте только на основе 'Контекст'.
    -Максимально полно используй доступную информацию!

    Формат вывода: 
    Я - AI-консультант компании (возьми из контекста). Напиши краткое описание компании сайта (возьми информацию из контекста). Какие услуги вы хотите, чтобы я вам предложил?
     
    Передаю данные для твоей работы:
    'Контекст' - "{cleaned_text}"
    """
    
    try:
        response = await generate_openai_response(prompt)
        return response
    except Exception as e:
        print(f"Error generating AI description: {e}")
        return "Извините, не удалось сгенерировать описание."

async def generate_openai_response(prompt: str) -> str:
    """
    Generate a response using OpenAI
    """
    if not openai_client:
        return "Сервис искусственного интеллекта временно недоступен."
        
    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return "Произошла ошибка при генерации ответа." 