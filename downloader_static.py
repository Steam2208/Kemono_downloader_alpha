import requests
from bs4 import BeautifulSoup
import os
import json
import urllib3
import re
import urllib.parse

# Отключаем предупреждения SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Статический User-Agent вместо fake-useragent
STATIC_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

HEADERS = {
    "User-Agent": STATIC_USER_AGENT,
    "Referer": "https://kemono.cr/", 
    "Accept": "text/css",  # Критично важный заголовок!
    "Accept-Language": "en-US,en;q=0.9", 
    "Accept-Encoding": "gzip, deflate",  
    "Connection": "keep-alive"
}

# Конвертирует thumbnail URL в полный URL изображения
def convert_thumbnail_to_full(url):
    """Конвертирует //img.kemono.cr/thumbnail/data/... в https://n3.kemono.cr/data/..."""
    if not url:
        return None
    
    # Обрабатываем относительные URL
    if url.startswith('//'):
        url = 'https:' + url
    elif url.startswith('/'):
        url = 'https://kemono.cr' + url
    
    # Конвертируем thumbnail в полное изображение
    if 'thumbnail/data/' in url:
        # Заменяем //img.kemono.cr/thumbnail/data/ на https://n3.kemono.cr/data/
        # Пример: //img.kemono.cr/thumbnail/data/ce/15/ce152b1d...png -> https://n3.kemono.cr/data/ce/15/ce152b1d...png
        full_url = url.replace('//img.kemono.cr/thumbnail/data/', 'https://n3.kemono.cr/data/')
        full_url = full_url.replace('https://img.kemono.cr/thumbnail/data/', 'https://n3.kemono.cr/data/')
        
        # Добавляем параметр ?f= если есть имя файла в конце
        if '.' in os.path.basename(full_url):
            filename = os.path.basename(full_url)
            if '?' not in full_url:
                full_url += f'?f={filename}'
        
        return full_url
    
    return url

def get_creator_posts(creator_url):
    """Получает все посты автора через API с пагинацией"""
    print("🔄 Извлекаем информацию из URL...")
    
    # Парсим URL для получения service и creator_id
    if 'kemono.cr' in creator_url or 'kemono.party' in creator_url:
        parts = creator_url.split('/')
        if 'user' in parts:
            user_idx = parts.index('user')
            if user_idx + 1 < len(parts):
                service_idx = user_idx - 1
                if service_idx >= 0:
                    service = parts[service_idx]
                    creator_id = parts[user_idx + 1]
                    
                    print(f"🎯 Service: {service}")
                    print(f"👤 Creator ID: {creator_id}")
                    
                    posts = []
                    offset = 0
                    limit = 50
                    
                    while True:
                        try:
                            url = f"https://kemono.cr/api/v1/{service}/user/{creator_id}/posts?o={offset}"
                            print(f"Запрос к API: {url}")
                            
                            response = requests.get(url, headers=HEADERS, verify=False, timeout=30)
                            
                            if response.status_code != 200:
                                print(f"  ❌ Ошибка API: {response.status_code}")
                                break
                            
                            data = response.json()
                            
                            if not data or len(data) == 0:
                                print(f"  ✅ Достигнут конец списка постов")
                                break
                            
                            # Извлекаем ID постов
                            batch_posts = [post['id'] for post in data if 'id' in post]
                            posts.extend(batch_posts)
                            
                            print(f"  📊 Получено постов: {len(batch_posts)}, всего: {len(posts)}")
                            
                            # Если получили меньше limit, значит это последняя страница
                            if len(data) < limit:
                                break
                            
                            offset += limit
                            
                        except Exception as e:
                            print(f"  ❌ Ошибка запроса: {e}")
                            break
                    
                    print(f"  ✅ Итого постов: {len(posts)}")
                    
                    # Возвращаем URL для каждого поста
                    post_urls = []
                    for post_id in posts:
                        post_url = f"https://kemono.cr/{service}/user/{creator_id}/post/{post_id}"
                        post_urls.append(post_url)
                    
                    return post_urls
    
    print("❌ Неверный формат URL")
    return []

def get_post_media(post_url, enhanced_search=True):
    """Enhanced поиск медиа в посте через API"""
    print(f"  📄 Получаем медиа через API: {post_url}")
    
    # Извлекаем service, creator_id и post_id из URL
    try:
        parts = post_url.split('/')
        if 'kemono.cr' in post_url and 'user' in parts and 'post' in parts:
            service_idx = parts.index('kemono.cr') + 1
            user_idx = parts.index('user')
            post_idx = parts.index('post')
            
            service = parts[service_idx]
            creator_id = parts[user_idx + 1]
            post_id = parts[post_idx + 1]
            
            print(f"  📄 Получаем медиа через API: {service}/{creator_id}/post/{post_id}")
            
            api_url = f"https://kemono.cr/api/v1/{service}/user/{creator_id}/post/{post_id}"
            response = requests.get(api_url, headers=HEADERS, verify=False, timeout=30)
            
            print(f"  📶 API Status: {response.status_code}")
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            
            print(f"  🔍 Enhanced API Search ВКЛЮЧЕН - ищем ВСЕ медиа (файлы + вложения + контент)")
            
            media_links = []
            
            # 1. Основной файл поста (в post.file)
            post_data = data.get('post', {})
            if 'file' in post_data and post_data['file']:
                filename = post_data['file'].get('name', 'unknown')
                file_path = post_data['file'].get('path', '')
                if file_path:
                    # Поддерживаем разные домены (n3, n4, etc.)
                    file_url = f"https://n3.kemono.cr/data{file_path}?f={filename}"
                    print(f"    📁 Основной файл: {filename}")
                    print(f"       URL: {file_url}")
                    media_links.append(file_url)
            
            # 1.1. Основной файл поста (прямо в data.file, если есть)
            if 'file' in data and data['file']:
                filename = data['file'].get('name', 'unknown')
                file_path = data['file'].get('path', '')
                if file_path:
                    file_url = f"https://n3.kemono.cr/data{file_path}?f={filename}"
                    print(f"    📁 Дополнительный файл: {filename}")
                    print(f"       URL: {file_url}")
                    if file_url not in media_links:
                        media_links.append(file_url)
            
            # 2. Вложения поста (в post.attachments)
            if 'attachments' in post_data and post_data['attachments']:
                print(f"  📎 Найдено вложений в post: {len(post_data['attachments'])}")
                for attachment in post_data['attachments']:
                    filename = attachment.get('name', 'unknown')
                    file_path = attachment.get('path', '')
                    if file_path:
                        # Поддерживаем разные домены kemono
                        file_url = f"https://n3.kemono.cr/data{file_path}?f={filename}"
                        print(f"      • {filename}")
                        print(f"        URL: {file_url}")
                        media_links.append(file_url)
            
            # 2.1. Вложения поста (прямо в data.attachments)
            if 'attachments' in data and data['attachments']:
                print(f"  📎 Найдено корневых вложений: {len(data['attachments'])}")
                for attachment in data['attachments']:
                    filename = attachment.get('name', 'unknown')
                    file_path = attachment.get('path', '')
                    if file_path:
                        file_url = f"https://n3.kemono.cr/data{file_path}?f={filename}"
                        print(f"      • {filename}")
                        print(f"        URL: {file_url}")
                        if file_url not in media_links:
                            media_links.append(file_url)
            
            # 2.2. Превью файлы (data.previews)
            if 'previews' in data and data['previews']:
                print(f"  🖼️ Найдено превью: {len(data['previews'])}")
                for preview in data['previews']:
                    if isinstance(preview, dict):
                        filename = preview.get('name', 'unknown')
                        file_path = preview.get('path', '')
                        server = preview.get('server', 'https://n1.kemono.cr')
                        if file_path:
                            # Используем указанный сервер или n1 по умолчанию
                            if server and server.startswith('http'):
                                file_url = f"{server}/data{file_path}?f={filename}"
                            else:
                                file_url = f"https://n1.kemono.cr/data{file_path}?f={filename}"
                            print(f"      🖼️ {filename}")
                            print(f"        URL: {file_url}")
                            if file_url not in media_links:
                                media_links.append(file_url)
            
            # 3. Дополнительные вложения из других мест
            for key in ['attachments', 'file']:
                if key in data and isinstance(data[key], list):
                    for item in data[key]:
                        if isinstance(item, dict):
                            filename = item.get('name', 'unknown')
                            file_path = item.get('path', '')
                            if file_path and file_path not in [link.split('?')[0].replace('https://n3.kemono.cr/data', '') for link in media_links]:
                                file_url = f"https://n3.kemono.cr/data{file_path}?f={filename}"
                                media_links.append(file_url)
            
            # 4. Корневые вложения
            if isinstance(data, dict):
                root_attachments = []
                for key, value in data.items():
                    if key == 'attachments' and isinstance(value, list):
                        root_attachments.extend(value)
                
                if root_attachments:
                    print(f"  📎 Найдено корневых вложений: {len(root_attachments)}")
                    for attachment in root_attachments:
                        if isinstance(attachment, dict):
                            filename = attachment.get('name', 'unknown')
                            print(f"      • {filename}")
                        elif isinstance(attachment, str):
                            print(f"      • {attachment}")
            
            print(f"  ✅ Enhanced режим: основные файлы и вложения уже обработаны")
            
            # 5. Enhanced поиск в контенте и других местах
            content = data.get('content', '') or ''
            if not content and data.get('post'):
                content = data['post'].get('content', '') or ''
            
            print(f"  🔍 Enhanced: анализируем контент ({len(content)} символов)")
            
            # Ищем ссылки в контенте
            if content:
                content_links = find_media_links_in_content(content)
                if content_links:
                    print(f"  🔗 Enhanced: найдено ссылок в контенте: {len(content_links)}")
                    for link in content_links:
                        if link not in media_links:
                            media_links.append(link)
                            filename = link.split('/')[-1].split('?')[0][:50]
                            print(f"      🔗 Контент ссылка: {filename}...")
            
        # 6. Проверка всех секций на видео файлы
        all_video_sources = []
        
        # Проверяем post.attachments
        if data.get('post', {}).get('attachments'):
            all_video_sources.extend(data['post']['attachments'])
        
        # Проверяем корневые attachments
        if data.get('attachments'):
            all_video_sources.extend(data['attachments'])
            
        # Проверяем videos секцию
        if data.get('videos'):
            all_video_sources.extend(data['videos'])
            
        # Проверяем previews (могут содержать видео)
        if data.get('previews'):
            all_video_sources.extend(data['previews'])
        
        video_count = 0
        for item in all_video_sources:
            if isinstance(item, dict):
                name = item.get('name', '').lower()
                if any(ext in name for ext in ['.mp4', '.avi', '.mkv', '.mov', '.webm', '.gif']):
                    video_count += 1
        
        if video_count > 0:
            print(f"  🎬 Enhanced: найдено видео файлов: {video_count}")
            for item in all_video_sources:
                if isinstance(item, dict):
                    name = item.get('name', '')
                    if any(ext in name.lower() for ext in ['.mp4', '.avi', '.mkv', '.mov', '.webm', '.gif']):
                        print(f"      🎬 Видео: {name}")
                        
                        # Добавляем видео файлы в список если их еще нет
                        file_path = item.get('path', '')
                        if file_path:
                            file_url = f"https://n3.kemono.cr/data{file_path}?f={name}"
                            if file_url not in media_links:
                                media_links.append(file_url)
                                print(f"        📎 Добавлено: {file_url}")
            
        # Удаляем дубликаты
        unique_links = list(dict.fromkeys(media_links))
        
        if len(unique_links) > 0:
            print(f"   📎 Скачиваю {len(unique_links)} файлов:")
            for f in unique_links:
                # Получаем имя файла для отображения
                if '?f=' in f:
                    display_name = f.split('?f=')[-1]
                else:
                    display_name = f.split('/')[-1]
                print(f"     • {display_name}")
        else:
            print(f"   ⚠️ API не нашел медиа, пробуем HTML парсинг...")
            # Если API не нашел медиа, пробуем HTML
            html_media = get_post_media_from_html_fallback(post_url)
            if html_media:
                print(f"   ✅ HTML парсинг нашел {len(html_media)} файлов!")
                return html_media
            else:
                print(f"   ❌ Медиа не найдено")
            
        return unique_links
            
    except Exception as e:
        print(f"  ❌ Ошибка парсинга URL или API: {e}")
        # Пробуем HTML fallback если API не сработал
        print(f"  🔄 Переключаемся на HTML парсинг...")
        return get_post_media_from_html_fallback(post_url)

def download_file(url, save_dir):
    """Скачивает файл по URL"""
    try:
        # Создаем папку если не существует
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        # Получаем имя файла
        if '?f=' in url:
            filename = url.split('?f=')[-1]
        else:
            filename = url.split('/')[-1].split('?')[0]
        
        # Безопасное имя файла
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        if not safe_filename:
            safe_filename = 'unknown_file'
        
        filepath = os.path.join(save_dir, safe_filename)
        
        # Проверяем существование файла
        if os.path.exists(filepath):
            print(f"✅ Скачано: {safe_filename}")
            return True
        
        # Пробуем скачать с оригинального URL
        response = requests.get(url, headers=HEADERS, verify=False, timeout=30, stream=True)
        
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(filepath)
            print(f"    ✅ Скачано: {safe_filename} ({file_size} байт)")
            return True
        
        # Если оригинальный не работает, пробуем другие домены
        print(f"    ⚠️ Оригинал недоступен ({response.status_code}), ищем на других доменах...")
        
        # Извлекаем путь из URL
        import re
        match = re.search(r'n\d+\.kemono\.cr(/data/.*)', url)
        if match:
            data_path = match.group(1)
            
            # Пробуем разные домены kemono
            domains = ['n1', 'n2', 'n3', 'n4', 'n5', 'n6']
            
            for domain in domains:
                try:
                    test_url = f"https://{domain}.kemono.cr{data_path}"
                    
                    # Быстрая проверка HEAD запросом
                    head_response = requests.head(test_url, headers=HEADERS, verify=False, timeout=15)
                    
                    if head_response.status_code == 200:
                        # Если HEAD успешен, скачиваем файл
                        response = requests.get(test_url, headers=HEADERS, verify=False, timeout=30, stream=True)
                        
                        if response.status_code == 200:
                            with open(filepath, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            
                            file_size = os.path.getsize(filepath)
                            print(f"    ✅ Найдено на {domain}: {safe_filename} ({file_size} байт)")
                            return True
                
                except Exception:
                    continue
        
        print(f"    ❌ Файл недоступен на всех доменах: {safe_filename}")
        return False
            
    except Exception as e:
        print(f"❌ Ошибка скачивания {url}: {e}")
        return False

def extract_creator_info(url):
    """Извлекает информацию об авторе из URL"""
    url = url.strip()
    
    if 'kemono.cr' in url or 'kemono.party' in url:
        parts = url.split('/')
        if 'user' in parts:
            user_idx = parts.index('user')
            if user_idx + 1 < len(parts):
                service_idx = user_idx - 1
                if service_idx >= 0:
                    service = parts[service_idx]
                    creator_id = parts[user_idx + 1]
                    return service, creator_id
    
    return None, None

def find_media_links_in_content(content):
    """Находит ссылки на медиа файлы в тексте контента"""
    media_links = []
    
    # 1. Парсим HTML теги <a href="..."> и <figure>
    html_patterns = [
        # fileThumb image-link href="..."
        r'<a[^>]*class="[^"]*fileThumb[^"]*image-link[^"]*"[^>]*href="([^"]+)"',
        # Любые img src="..." с kemono доменами
        r'<img[^>]*src="([^"]*(?:kemono\.cr|kemono\.party)[^"]*)"',
        # Любые a href="..." с медиа файлами
        r'<a[^>]*href="([^"]*(?:\.mp4|\.avi|\.mkv|\.mov|\.webm|\.zip|\.rar|\.jpg|\.png|\.gif|\.jpeg)[^"]*)"',
        # Любые ссылки на data/ папки kemono
        r'<[^>]*(?:href|src)="([^"]*(?:kemono\.cr|kemono\.party)[^"]*/data/[^"]*)"',
    ]
    
    for pattern in html_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
        for match in matches:
            # Очищаем от HTML entities и лишних символов
            match = match.replace('&amp;', '&').rstrip('.,;:)')
            # Добавляем https:// если ссылка начинается с //
            if match.startswith('//'):
                match = 'https:' + match
            if match not in media_links and 'kemono.cr' in match:
                media_links.append(match)
                print(f"      📸 HTML тег: {match.split('/')[-1][:50]}...")
    
    # 2. Паттерны для поиска обычных ссылок в тексте
    url_patterns = [
        r'https?://[^\s<>"]+\.(?:mp4|avi|mkv|mov|webm|zip|rar|jpg|png|gif|jpeg)',
        r'https?://[^\s<>"]*(?:drive\.google\.com|mega\.nz|dropbox\.com|mediafire\.com|onedrive\.live\.com)[^\s<>"]*',
        r'https?://[^\s<>"]*(?:kemono\.cr|kemono\.party)[^\s<>"]*/data/[^\s<>"]*',
    ]
    
    for pattern in url_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            # Очищаем от лишних символов в конце
            match = match.rstrip('.,;:)')
            if match not in media_links:
                media_links.append(match)
                print(f"      🔗 Текст ссылка: {match.split('/')[-1][:50]}...")
    
    return media_links

def get_post_media_from_html_fallback(post_url):
    """Резервный метод получения медиа из HTML страницы"""
    print(f"  🌐 Пробуем HTML парсинг: {post_url}")
    
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': STATIC_USER_AGENT,
            'Referer': 'https://kemono.cr/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        
        response = session.get(post_url, verify=False, timeout=30)
        
        if response.status_code != 200:
            print(f"  ❌ HTML ошибка: {response.status_code}")
            return []
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        media_links = []
        
        # 1. Ищем ссылки для скачивания (post__attachment-link)
        download_links = soup.find_all('a', class_='post__attachment-link')
        for link in download_links:
            href = link.get('href', '')
            filename = link.get('download', '')
            if href:
                media_links.append(href)
                print(f"    📎 HTML скачивание: {filename}")
        
        # 2. Ищем видео теги
        video_tags = soup.find_all('video')
        for video in video_tags:
            sources = video.find_all('source')
            for source in sources:
                src = source.get('src', '')
                if src and src not in media_links:
                    media_links.append(src)
                    filename = src.split('/')[-1].split('?')[0]
                    print(f"    🎬 HTML видео: {filename}")
        
        # 3. Ищем обычные ссылки на медиа
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            if any(ext in href.lower() for ext in ['.mp4', '.avi', '.mkv', '.mov', '.webm', '.zip', '.rar']):
                if href.startswith('/'):
                    href = f"https://kemono.cr{href}"
                elif not href.startswith('http'):
                    continue
                
                if href not in media_links:
                    media_links.append(href)
                    filename = href.split('/')[-1].split('?')[0]
                    print(f"    🔗 HTML ссылка: {filename}")
        
        if media_links:
            print(f"  ✅ HTML парсинг нашел {len(media_links)} файлов")
        else:
            print(f"  ❌ HTML парсинг не нашел медиа")
        
        return media_links
        
    except Exception as e:
        print(f"  ❌ Ошибка HTML парсинга: {e}")
        return []

# =====================================
# КОНСОЛЬНЫЙ ИНТЕРФЕЙС
# =====================================

def console_interface():
    """Консольный интерфейс для программы"""
    print("🦊 KemonoDownloader v2.3 Final - Console Edition")
    print("="*50)
    print("Поддерживаемые форматы:")
    print("🎬 Видео: MP4, MOV, AVI, MKV, WEBM")
    print("🖼️ Изображения: PNG, JPG, JPEG, GIF")
    print("📦 Архивы: ZIP, RAR")
    print("="*50)
    
    while True:
        try:
            print("\n🔗 Введите ссылку на:")
            print("   • Автора: https://kemono.cr/patreon/user/12345")
            print("   • Пост: https://kemono.cr/patreon/user/12345/post/67890")
            print("   • Или 'exit' для выхода")
            
            url = input("\n👉 Ссылка: ").strip()
            
            if url.lower() in ['exit', 'quit', 'выход', 'q']:
                print("👋 До свидания!")
                break
            
            if not url:
                print("❌ Ссылка не может быть пустой!")
                continue
            
            if 'kemono.cr' not in url:
                print("❌ Поддерживаются только ссылки kemono.cr!")
                continue
            
            print(f"\n📁 Где сохранить файлы?")
            print("   • Введите путь к папке")
            print("   • Или нажмите Enter для текущей папки")
            
            download_folder = input("👉 Папка: ").strip()
            
            if not download_folder:
                download_folder = "downloads"
            
            # Создаем папку если её нет
            import os
            if not os.path.exists(download_folder):
                os.makedirs(download_folder)
                print(f"📁 Создана папка: {download_folder}")
            
            print(f"\n🚀 Начинаем загрузку...")
            print(f"🔗 URL: {url}")
            print(f"📁 Папка: {download_folder}")
            print("="*50)
            
            # Определяем тип ссылки и запускаем загрузку
            if '/post/' in url:
                print("📄 Обнаружен пост, загружаем...")
                success = download_post_media(url, download_folder)
                if success:
                    print(f"\n✅ Пост успешно загружен в: {download_folder}")
                else:
                    print(f"\n❌ Не удалось загрузить пост")
            else:
                print("👤 Обнаружен автор, загружаем все посты...")
                success = download_creator_posts(url, download_folder)
                if success:
                    print(f"\n✅ Автор успешно загружен в: {download_folder}")
                else:
                    print(f"\n❌ Не удалось загрузить автора")
            
            print("\n" + "="*50)
            input("📌 Нажмите Enter для продолжения...")
            
        except KeyboardInterrupt:
            print("\n\n👋 Программа остановлена пользователем. До свидания!")
            break
        except Exception as e:
            print(f"\n❌ Произошла ошибка: {e}")
            input("📌 Нажмите Enter для продолжения...")

if __name__ == "__main__":
    console_interface()