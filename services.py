import httpx
import re
from bs4 import BeautifulSoup
from openai import OpenAI
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import datetime
import json
import logging

from config import YANDEX_FOLDERID, YANDEX_API_KEY, OPENAI_API_KEY
from database import UrlChat

logger = logging.getLogger(__name__)

try:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {e}")
    openai_client = None


async def parse_url_from_message(message_text: str, dialog_id: int) -> Dict[str, Any]:
    # Ensure cleaned_text is a string
    if message_text is None:
        message_text = ""
    original_text = message_text
    logger.debug(f"Parsing message: {message_text}")
    
    # Handle /start command
    if message_text.lower().startswith("/start"):
        message_text = message_text[6:].strip()
        logger.debug(f"After removing /start: {message_text}")
        if not message_text:  # Empty after /start
            return {"type": "start_empty", "dialog_id": dialog_id}
    
    # Special case for domains without dots (like 'wikilect_com')
    if '_' in message_text and not '.' in message_text:
        # Replace underscores with dots
        domain_part = message_text.split()[0]  # Get the first word
        domain_with_dots = domain_part.replace('_', '.')
        rest_of_message = message_text[len(domain_part):].strip()
        
        message_text = domain_with_dots + (' ' + rest_of_message if rest_of_message else '')
        logger.debug(f"Converted underscore domain: {message_text}")
    
    # Check if message contains a URL/domain
    # This regex matches domains with or without http/https and captures any text after it as query
    url_match = re.match(
        r'^((?:https?:\/\/)?(?:www\.)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?:\/[^\s]*)?)(?:\s+(.*))?$',
        message_text
    )
    
    # If no match found with standard regex, try a more lenient approach
    # This will match almost anything that could be a domain
    if not url_match:
        logger.debug(f"No standard URL match, trying lenient match")
        # If it contains no spaces, treat the entire text as a potential domain
        if ' ' not in message_text and len(message_text) > 3:
            # Add .com if it doesn't have a TLD
            if '.' not in message_text:
                message_text = message_text + '.com'
                logger.debug(f"Added .com: {message_text}")
            
            # Try the regex match again
            url_match = re.match(
                r'^((?:https?:\/\/)?(?:www\.)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?:\/[^\s]*)?)(?:\s+(.*))?$',
                message_text
            )
    
    if url_match:
        full_site = url_match.group(1)  # The domain/URL part
        query = url_match.group(3)  # Any text after the URL
        
        logger.debug(f"URL match found: {full_site}")
        
        # Ensure URL has proper scheme
        if not (full_site.startswith('http://') or full_site.startswith('https://')):
            full_site = 'https://' + full_site
            
        # Create result with site info
        result = {"site": full_site, "type": "site", "dialog_id": dialog_id}
        
        # Add query if present
        if query and query.strip():
            result["query"] = query.strip()
            
        logger.debug(f"Returning site result: {result}")
        return result
    
    # If no URL was found, treat as a question query
    logger.debug(f"No URL found, treating as query: {original_text}")
    return {"query": original_text, "type": "query", "dialog_id": dialog_id}


async def save_url_to_db(db: Session, dialog_id: int, website: str) -> None:
    logger.debug(f"save_url_to_db called with website: {website} for dialog_id: {dialog_id}")
    
    # Fetch website content regardless of caching
    content = await fetch_webpage_content(website)
    cleaned_text = await clean_html_content(content)
    logger.debug(f"Fetched and cleaned website content. Size: {len(content)} bytes, cleaned: {len(cleaned_text)} bytes")
    
    # ALWAYS search for company information using Yandex API
    logger.debug(f"Calling Yandex API for website {website}...")
    company_info = await search_with_yandex("информация о компании", website)
    logger.debug(f"Received Yandex API response. Company name: {company_info.get('company_name', 'Unknown')}")
    
    # Combine the information - use cleaned text and add the company info
    combined_text = cleaned_text
    if company_info:
        company_info_str = json.dumps(company_info, ensure_ascii=False)
        combined_text = f"{cleaned_text}\n\nYANDEX_COMPANY_INFO: {company_info_str}"
    
    # Check if we already have information about this website for this user
    existing = db.query(UrlChat).filter(
        UrlChat.dialog_id == dialog_id,
        UrlChat.website == website
    ).first()

    # Save data to database (update existing or create new)
    if existing:
        logger.debug(f"Updating existing record for {website}")
        existing.created_at = datetime.datetime.utcnow()
        existing.cleaned_content = combined_text
        db.commit()
    else:
        logger.debug(f"Creating new record for {website}")
        new_url = UrlChat(
            dialog_id=dialog_id,
            website=website,
            cleaned_content=combined_text
        )
        db.add(new_url)
        db.commit()
    
    logger.debug(f"Successfully saved company information to database for {website}")
    # Return value to indicate success
    return


async def get_latest_url(db: Session, dialog_id: int) -> Optional[UrlChat]:
    return db.query(UrlChat).filter(
        UrlChat.dialog_id == dialog_id
    ).order_by(UrlChat.created_at.desc()).first()


async def fetch_webpage_content(url: str) -> str:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            return response.text
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}")
            return ""


async def search_with_yandex(query: str, url: str = None) -> Dict[str, Any]:
    """Search for company information using Yandex Search API
    
    Args:
        query: The search query
        url: Optional website URL to focus the search
        
    Returns:
        Dict containing search results and extracted information
    """
    print(f"[YANDEX API] Making Yandex API call for query: {query}, url: {url}")
    # Print stack trace to see where this is called from
    import traceback
    print("[YANDEX API] Call stack:")
    traceback.print_stack(limit=5)
    
    if not YANDEX_API_KEY or not YANDEX_FOLDERID:
        print("Yandex API credentials are missing")
        return {
            "company_name": "Unknown",
            "description": "Не удалось получить информацию о компании: отсутствуют учетные данные API.",
            "services": [],
            "contact": {}
        }
    
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "x-folder-id": YANDEX_FOLDERID,
        "Content-Type": "application/json"
    }
    
    # If URL is provided, focus search on that domain
    search_query = query
    if url:
        # Extract domain from URL, handling different URL formats
        domain_match = re.search(r'(?:https?://)?(?:www\.)?((?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,})', url)
        if domain_match:
            domain = domain_match.group(1)
            search_query = f"{query} site:{domain}"
            print(f"Using domain-specific search query: {search_query}")
        else:
            print(f"Could not extract domain from URL: {url}")
    
    yandex_search_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    
    payload = {
        "modelUri": "gpt://b1gvge5pe35lrn55nnhd/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": 1500
        },
        "messages": [
            {
                "role": "system",
                "text": "You are a research assistant that extracts accurate information about companies from search results."
            },
            {
                "role": "user",
                "text": f"Search the web for: {search_query}\n\nFind the following information about the company: company name, description, services offered, contact information. Format as JSON."
            }
        ]
    }
    
    try:
        print("Sending request to Yandex API")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(yandex_search_url, headers=headers, json=payload, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                
                print(f"Received response from Yandex API: Status {response.status_code}")
                
                # Extract the result text and parse it
                result_text = result.get("result", {}).get("alternatives", [{}])[0].get("message", {}).get("text", "")
                
                if not result_text:
                    print("Warning: Empty result text from Yandex API")
                    return {
                        "company_name": "Unknown",
                        "description": "Информация о компании не найдена.",
                        "services": [],
                        "contact": {}
                    }
                
                # Try to extract JSON from the text response
                try:
                    # Find JSON-like content
                    json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        parsed_data = json.loads(json_str)
                        print(f"Successfully parsed JSON from Yandex response. Company name: {parsed_data.get('company_name', 'Unknown')}")
                        return parsed_data
                    else:
                        print("No JSON content found in Yandex response, using raw text")
                        # Return structured format if no JSON found
                        return {
                            "company_name": "Unknown",
                            "description": result_text,
                            "services": [],
                            "contact": {}
                        }
                except json.JSONDecodeError as json_err:
                    print(f"Failed to parse JSON from Yandex response: {json_err}")
                    # If we can't parse JSON, return the text
                    return {
                        "company_name": "Unknown",
                        "description": result_text,
                        "services": [],
                        "contact": {}
                    }
            except httpx.HTTPStatusError as http_err:
                print(f"HTTP error occurred when calling Yandex API: {http_err}")
                return {
                    "company_name": "Unknown",
                    "description": f"Ошибка при запросе к API: {http_err.response.status_code}",
                    "services": [],
                    "contact": {}
                }
            except httpx.RequestError as req_err:
                print(f"Request error occurred when calling Yandex API: {req_err}")
                return {
                    "company_name": "Unknown",
                    "description": "Ошибка сетевого запроса при обращении к API.",
                    "services": [],
                    "contact": {}
                }
                
    except Exception as e:
        print(f"Unexpected error in Yandex search: {e}")
        import traceback
        traceback.print_exc()
        return {
            "company_name": "Unknown",
            "description": "Непредвиденная ошибка при получении информации о компании.",
            "services": [],
            "contact": {}
        }


async def clean_html_content(html_content: str) -> str:
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, 'html.parser')
    for script in soup(["script", "style"]):
        script.decompose()

    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return ' '.join(chunk for chunk in chunks if chunk)


async def generate_ai_description(cleaned_text: str) -> str:
    # Ensure cleaned_text is a string
    if cleaned_text is None:
        cleaned_text = ""
    if not isinstance(cleaned_text, str):
        cleaned_text = str(cleaned_text)
    
    # Extract Yandex company info if available
    company_info = {}
    try:
        yandex_info_match = re.search(r'YANDEX_COMPANY_INFO: (\{.*\})', cleaned_text, re.DOTALL)
        if yandex_info_match:
            try:
                company_info = json.loads(yandex_info_match.group(1))
                # Remove the Yandex info from cleaned text to avoid duplication
                cleaned_text = cleaned_text.replace(yandex_info_match.group(0), "")
            except json.JSONDecodeError:
                pass
    except Exception as e:
        logger.error(f"Error extracting company info in description: {e}")
        # Continue with empty company_info if there's an error
    
    company_name = company_info.get("company_name", "")
    if company_name == "Unknown":
        company_name = ""
        
    company_description = company_info.get("description", "")
    company_services = company_info.get("services", [])
    
    prompt = f"""
Роль:
ТЫ — AI-консультант компании, который общается в дружелюбном, естественном стиле.

Контекст: "{cleaned_text}"

Дополнительная информация о компании:
Название: {company_name}
Описание: {company_description}
Услуги: {', '.join(company_services) if isinstance(company_services, list) else company_services}

Твоя задача:
1. Представиться как AI-консультант компании в дружелюбной манере
2. Дать естественное и живое описание компании (2-3 предложения)
3. Перечислить 3-5 ключевых услуг/продуктов в виде простых пунктов
4. Завершить дружелюбным предложением помощи

Пример тона ответа:
"Привет! Я — AI-консультант компании [название].

Мы — [краткое описание с акцентом на ценности и подход компании].

Чем можем быть полезны:
• [услуга 1]
• [услуга 2]
• [услуга 3]

Готов ответить на ваши вопросы о компании — чем могу помочь?"

Важно: Если название компании не указано в контексте, найди его. Если не можешь найти, используй домен сайта как название.

Если контекст пустой или информации недостаточно, сообщи что нужна ссылка на сайт компании через /start example.com
"""
    return await generate_openai_response(prompt)


async def generate_ai_question_answer(cleaned_text: str, question: str) -> str:
    # Ensure cleaned_text is a string
    if cleaned_text is None:
        cleaned_text = ""
    if not isinstance(cleaned_text, str):
        cleaned_text = str(cleaned_text)
        
    # Ensure question is a string
    if question is None:
        question = ""
    if not isinstance(question, str):
        question = str(question)
    
    # Extract Yandex company info if available
    company_info = {}
    try:
        yandex_info_match = re.search(r'YANDEX_COMPANY_INFO: (\{.*\})', cleaned_text, re.DOTALL)
        if yandex_info_match:
            try:
                company_info = json.loads(yandex_info_match.group(1))
                # Remove the Yandex info from cleaned text to avoid duplication
                cleaned_text = cleaned_text.replace(yandex_info_match.group(0), "")
            except json.JSONDecodeError:
                pass
    except Exception as e:
        logger.error(f"Error extracting company info: {e}")
        # Continue with empty company_info if there's an error
    
    company_name = company_info.get("company_name", "")
    if company_name == "Unknown":
        company_name = ""
        
    company_description = company_info.get("description", "")
    company_services = company_info.get("services", [])
    
    prompt = f"""
    Роль:
    ТЫ — дружелюбный AI-консультант компании {company_name if company_name else "(название из контекста)"}
    Твоя задача отвечать ТОЛЬКО на вопросы, связанные с компанией, ее услугами и продуктами.

    Контекст о компании:
    {cleaned_text}

    Дополнительная информация о компании:
    Название: {company_name}
    Описание: {company_description}
    Услуги: {', '.join(company_services) if isinstance(company_services, list) else company_services}

    Вопрос: {question}

    Как отвечать:
    1. Говори в дружелюбном, конверсационном тоне, как реальный консультант компании
    2. Используй факты из контекста, но представляй их в естественной форме
    3. Ответы должны быть краткими и по существу (до 3 предложений)
    4. Если нет информации в контексте, честно признайся, но в дружелюбной манере

    Очень важно: 
    - Никогда не отвечай на вопросы, не относящиеся к компании (например, о политике, других компаниях, личных вопросах)
    - При этом ответ должен звучать естественно, как от реального консультанта
    
    Пример тона:
    "Да, конечно! Наша компания предлагает... Мы особенно гордимся..."

Вместо формального: "Компания предоставляет следующие услуги..."
    """
    return await generate_openai_response(prompt)


async def generate_openai_response(prompt: str) -> str:
    if not openai_client:
        return "Сервис временно недоступен."

    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "Ошибка генерации ответа."