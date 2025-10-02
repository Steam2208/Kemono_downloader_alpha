import requests
from bs4 import BeautifulSoup
import os
import json
import urllib3
import re
import urllib.parse
import hashlib
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Попытка импорта CloudDownloader для автоскачивания облачных файлов
try:
    from cloud_downloader import CloudDownloader
    CLOUD_AUTO_ENABLED = True
    print("✅ CloudDownloader загружен - автоскачивание облачных файлов включено")
except ImportError:
    CloudDownloader = None
    CLOUD_AUTO_ENABLED = False
    print("⚠️ cloud_downloader.py не найден - автоскачивание облачных файлов отключено")

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

# Список всех поддерживаемых расширений файлов
SUPPORTED_EXTENSIONS = {
    # 3D модели и файлы Blender
    '.glb', '.gltf', '.blend', '.fbx', '.obj', '.dae', '.3ds', '.max', '.ma', '.mb',
    # Видео форматы
    '.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg',
    # Изображения
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tga', '.psd', '.webp', '.svg',
    # Архивы
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
    # Документы
    '.pdf', '.doc', '.docx', '.txt', '.rtf',
    # Аудио
    '.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac',
    # Другие форматы
    '.exe', '.msi', '.dmg', '.apk', '.ipa',
    # Unity и игровые ресурсы
    '.unity', '.unitypackage', '.prefab', '.asset',
    # Текстуры и материалы
    '.dds', '.hdr', '.exr', '.mat'
}

def is_supported_file(filename):
    """Проверяет, поддерживается ли файл по расширению"""
    if not filename:
        return False
    
    # Получаем расширение файла
    ext = os.path.splitext(filename.lower())[1]
    return ext in SUPPORTED_EXTENSIONS or len(filename) > 3  # Поддерживаем все файлы с именем

def detect_cloud_links(content):
    """Обнаруживает ссылки на облачные сервисы в контенте"""
    cloud_links = []
    
    # Паттерны для различных облачных сервисов
    cloud_patterns = {
        'Google Drive': [
            r'https://drive\.google\.com/[^\s<>"]+',
            r'https://docs\.google\.com/[^\s<>"]+',
        ],
        'MEGA': [
            r'https://mega\.nz/[^\s<>"]+',
            r'https://mega\.co\.nz/[^\s<>"]+',
        ],
        'Dropbox': [
            r'https://(?:www\.)?dropbox\.com/[^\s<>"]+',
            r'https://dl\.dropboxusercontent\.com/[^\s<>"]+',
        ],
        'OneDrive': [
            r'https://onedrive\.live\.com/[^\s<>"]+',
            r'https://1drv\.ms/[^\s<>"]+',
        ],
        'MediaFire': [
            r'https://(?:www\.)?mediafire\.com/[^\s<>"]+',
        ],
        'WeTransfer': [
            r'https://(?:we\.tl|wetransfer\.com)/[^\s<>"]+',
        ],
        'pCloud': [
            r'https://(?:my\.)?pcloud\.com/[^\s<>"]+',
        ],
        'Yandex Disk': [
            r'https://disk\.yandex\.[^\s<>"/]+/[^\s<>"]+',
        ],
        'Box': [
            r'https://(?:app\.)?box\.com/[^\s<>"]+',
        ],
        'iCloud': [
            r'https://(?:www\.)?icloud\.com/[^\s<>"]+',
        ]
    }
    
    for service_name, patterns in cloud_patterns.items():
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Очищаем ссылку от лишних символов
                clean_link = match.rstrip('.,;:)"}')
                if clean_link not in [link['url'] for link in cloud_links]:
                    cloud_links.append({
                        'service': service_name,
                        'url': clean_link
                    })
    
    return cloud_links

def save_cloud_links(save_dir, cloud_links, post_url):
    """Сохраняет найденные облачные ссылки в файл"""
    if not cloud_links:
        return
    
    # Создаем папку если не существует
    os.makedirs(save_dir, exist_ok=True)
    cloud_file = os.path.join(save_dir, 'cloud_links.txt')
    
    try:
        # Читаем существующие ссылки если файл есть
        existing_links = set()
        if os.path.exists(cloud_file):
            with open(cloud_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith('http') or '] http' in line:
                        # Извлекаем URL из строки формата "[Service] URL"
                        if '] ' in line:
                            url_part = line.split('] ', 1)[-1].strip()
                            existing_links.add(url_part)
                        elif line.strip().startswith('http'):
                            existing_links.add(line.strip())
        
        # Проверяем, есть ли новые ссылки
        new_links = []
        for link_info in cloud_links:
            if link_info['url'] not in existing_links:
                new_links.append(link_info)
        
        if not new_links:
            print(f"    ℹ️ Все облачные ссылки уже сохранены")
            return
        
        # Добавляем новые ссылки
        with open(cloud_file, 'a', encoding='utf-8') as f:
            # Добавляем заголовок для нового поста
            f.write(f"\n=== {post_url} ===\n")
            f.write(f"Найдено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for link_info in new_links:
                f.write(f"[{link_info['service']}] {link_info['url']}\n")
                existing_links.add(link_info['url'])
            
            f.write("\n")
        
        print(f"    💾 Облачных ссылок сохранено: {len(new_links)} в cloud_links.txt")
        
    except Exception as e:
        print(f"    ⚠️ Ошибка сохранения облачных ссылок: {e}")

def download_cloud_files(save_dir, cloud_links, post_url):
    """
    Автоматически скачивает файлы из облачных хранилищ
    """
    if not cloud_links or not CLOUD_AUTO_ENABLED:
        return []
    
    print(f"\n🌐 Автоскачивание облачных файлов: {len(cloud_links)}")
    
    downloader = CloudDownloader()
    downloaded_files = []
    
    # Создаем папку для облачных файлов (в той же папке, что и медиа файлы)
    cloud_dir = save_dir
    os.makedirs(cloud_dir, exist_ok=True)
    
    for i, link_info in enumerate(cloud_links, 1):
        service = link_info['service']
        url = link_info['url']
        
        print(f"\n[{i}/{len(cloud_links)}] {service}: {url[:60]}...")
        
        try:
            success = downloader.download_from_cloud(url, cloud_dir)
            if success:
                downloaded_files.append({'service': service, 'url': url})
                print(f"✅ {service} файл скачан")
            else:
                print(f"❌ Не удалось скачать {service} файл")
        except Exception as e:
            print(f"❌ Ошибка скачивания {service}: {e}")
        
        # Минимальная пауза для стабильности
        time.sleep(0.1)
    
    if downloaded_files:
        print(f"\n✅ Успешно скачано облачных файлов: {len(downloaded_files)}")
        
        # Сохраняем лог успешных скачиваний
        log_file = os.path.join(save_dir, "cloud_downloads.log")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n=== {post_url} ===\n")
            f.write(f"Скачано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for file_info in downloaded_files:
                f.write(f"[{file_info['service']}] {file_info['url']}\n")
            f.write("\n")
    
    return downloaded_files

def get_file_type(filename):
    """Определяет тип файла по расширению"""
    if not filename:
        return "неизвестный"
    
    ext = os.path.splitext(filename.lower())[1]
    
    # 3D модели и файлы Blender
    if ext in ['.glb', '.gltf', '.blend', '.fbx', '.obj', '.dae', '.3ds', '.max', '.ma', '.mb']:
        return "3D модель"
    # Видео
    elif ext in ['.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg']:
        return "видео"
    # Изображения
    elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tga', '.psd', '.webp', '.svg']:
        return "изображение"
    # Архивы
    elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz']:
        return "архив"
    # Документы
    elif ext in ['.pdf', '.doc', '.docx', '.txt', '.rtf']:
        return "документ"
    # Аудио
    elif ext in ['.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac']:
        return "аудио"
    # Unity и игровые ресурсы
    elif ext in ['.unity', '.unitypackage', '.prefab', '.asset']:
        return "Unity ресурс"
    # Текстуры и материалы
    elif ext in ['.dds', '.hdr', '.exr', '.mat']:
        return "текстура"
    # Исполняемые файлы
    elif ext in ['.exe', '.msi', '.dmg', '.apk', '.ipa']:
        return "приложение"
    else:
        return f"файл {ext}" if ext else "файл"

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
                    
                    page = 1
                    while True:
                        try:
                            url = f"https://kemono.cr/api/v1/{service}/user/{creator_id}/posts?o={offset}"
                            print(f"📄 Загружаем страницу {page} (offset {offset})...")
                            
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
                            
                            print(f"  📊 Страница {page}: получено {len(batch_posts)} постов, всего: {len(posts)}")
                            
                            # Если получили меньше limit, значит это последняя страница
                            if len(data) < limit:
                                print(f"  🏁 Последняя страница (получено {len(data)} < {limit})")
                                break
                            
                            offset += limit
                            page += 1
                            
                            # Небольшая пауза между запросами для снижения нагрузки на сервер
                            import time
                            time.sleep(0.5)
                            
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

def get_post_media(post_url, enhanced_search=True, save_dir=None):
    """Universal поиск ВСЕХ файлов в посте через API"""
    print(f"  📄 Получаем ВСЕ файлы через API: {post_url}")
    
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
            
            print(f"  📄 Получаем все файлы через API: {service}/{creator_id}/post/{post_id}")
            
            api_url = f"https://kemono.cr/api/v1/{service}/user/{creator_id}/post/{post_id}"
            response = requests.get(api_url, headers=HEADERS, verify=False, timeout=15)
            
            print(f"  📶 API Status: {response.status_code}")
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            
            print(f"  🔍 UNIVERSAL SEARCH - ищем ВСЕ типы файлов (3D, архивы, документы, медиа)")
            
            media_links = []
            found_files = []  # Для подсчета типов файлов
            
            # Отслеживаем уже добавленные файлы по пути, чтобы избежать дубликатов
            added_file_paths = set()
            
            # 1. Основной файл поста (в post.file)
            post_data = data.get('post', {})
            if 'file' in post_data and post_data['file']:
                filename = post_data['file'].get('name', 'unknown')
                file_path = post_data['file'].get('path', '')
                
                # Проверяем, не является ли filename прямой ссылкой
                if isinstance(filename, str) and ('http' in filename or 'mega.nz' in filename or 'drive.google.com' in filename):
                    print(f"    ⚠️ Пропускаем прямую ссылку в filename: {filename[:60]}...")
                elif file_path and is_supported_file(filename):
                    # Поддерживаем разные домены (n3, n4, etc.)
                    file_url = f"https://n3.kemono.cr/data{file_path}?f={filename}"
                    file_type = get_file_type(filename)
                    print(f"    📁 Основной файл ({file_type}): {filename}")
                    found_files.append(file_type)
                    media_links.append(file_url)
                    added_file_paths.add(file_path)
            
            # 1.1. Основной файл поста (прямо в data.file, если есть)
            if 'file' in data and data['file']:
                filename = data['file'].get('name', 'unknown')
                file_path = data['file'].get('path', '')
                
                # Проверяем, не является ли filename прямой ссылкой
                if isinstance(filename, str) and ('http' in filename or 'mega.nz' in filename or 'drive.google.com' in filename):
                    print(f"    ⚠️ Пропускаем прямую ссылку в filename: {filename[:60]}...")
                elif file_path and is_supported_file(filename) and file_path not in added_file_paths:
                    file_url = f"https://n3.kemono.cr/data{file_path}?f={filename}"
                    file_type = get_file_type(filename)
                    print(f"    📁 Дополнительный файл ({file_type}): {filename}")
                    found_files.append(file_type)
                    media_links.append(file_url)
                    added_file_paths.add(file_path)
            
            # 2. Вложения поста (в post.attachments) - УНИВЕРСАЛЬНЫЙ ПОИСК
            if 'attachments' in post_data and post_data['attachments']:
                print(f"  📎 Анализируем вложения в post: {len(post_data['attachments'])}")
                for attachment in post_data['attachments']:
                    filename = attachment.get('name', 'unknown')
                    file_path = attachment.get('path', '')
                    if file_path and filename != 'unknown' and file_path not in added_file_paths:
                        file_url = f"https://n3.kemono.cr/data{file_path}?f={filename}"
                        file_type = get_file_type(filename)
                        
                        # Проверяем все файлы, не только известные расширения
                        if is_supported_file(filename) or '.' in filename:
                            print(f"      📎 {file_type}: {filename}")
                            found_files.append(file_type)
                            media_links.append(file_url)
                            added_file_paths.add(file_path)
                        else:
                            print(f"      ⚠️ Неизвестный тип: {filename}")
            
            # 2.1. Вложения поста (прямо в data.attachments) - УНИВЕРСАЛЬНЫЙ ПОИСК
            if 'attachments' in data and data['attachments']:
                print(f"  📎 Анализируем корневые вложения: {len(data['attachments'])}")
                for attachment in data['attachments']:
                    filename = attachment.get('name', 'unknown')
                    file_path = attachment.get('path', '')
                    if file_path and filename != 'unknown' and file_path not in added_file_paths:
                        file_url = f"https://n3.kemono.cr/data{file_path}?f={filename}"
                        file_type = get_file_type(filename)
                        
                        if (is_supported_file(filename) or '.' in filename):
                            print(f"      📎 {file_type}: {filename}")
                            found_files.append(file_type)
                            media_links.append(file_url)
                            added_file_paths.add(file_path)
            
            # 2.2. Превью файлы (data.previews) - УНИВЕРСАЛЬНЫЙ ПОИСК
            if 'previews' in data and data['previews']:
                print(f"  🖼️ Анализируем превью: {len(data['previews'])}")
                for preview in data['previews']:
                    if isinstance(preview, dict):
                        filename = preview.get('name', 'unknown')
                        file_path = preview.get('path', '')
                        server = preview.get('server', 'https://n1.kemono.cr')
                        
                        # Проверяем, не является ли filename прямой ссылкой
                        if isinstance(filename, str) and ('http' in filename or 'mega.nz' in filename or 'drive.google.com' in filename):
                            print(f"      ⚠️ Пропускаем прямую ссылку в preview filename: {filename[:60]}...")
                            continue
                            
                        if file_path and filename != 'unknown' and file_path not in added_file_paths:
                            # Используем указанный сервер или n1 по умолчанию
                            if server and server.startswith('http'):
                                file_url = f"{server}/data{file_path}?f={filename}"
                            else:
                                file_url = f"https://n1.kemono.cr/data{file_path}?f={filename}"
                            
                            file_type = get_file_type(filename)
                            if (is_supported_file(filename) or '.' in filename):
                                print(f"      🖼️ {file_type}: {filename}")
                                found_files.append(file_type)
                                media_links.append(file_url)
                                added_file_paths.add(file_path)
            
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
            
            # Ищем облачные ссылки в контенте
            cloud_links = []
            if content:
                cloud_links = detect_cloud_links(content)
                if cloud_links:
                    print(f"  ☁️ Найдено облачных ссылок: {len(cloud_links)}")
                    cloud_stats = {}
                    for link_info in cloud_links:
                        service = link_info['service']
                        cloud_stats[service] = cloud_stats.get(service, 0) + 1
                    
                    for service, count in cloud_stats.items():
                        print(f"      ☁️ {service}: {count}")
            
            # Ищем ссылки на файлы в контенте (исключая облачные)
            if content:
                content_links = find_media_links_in_content(content)
                if content_links:
                    # Фильтруем облачные ссылки, чтобы не скачивать их как файлы
                    cloud_domains = ['drive.google.com', 'mega.nz', 'mega.co.nz', 'dropbox.com', 
                                   'onedrive.live.com', '1drv.ms', 'mediafire.com', 'we.tl', 
                                   'wetransfer.com', 'pcloud.com', 'disk.yandex.', 'box.com', 'icloud.com']
                    
                    filtered_links = []
                    for link in content_links:
                        is_cloud = any(domain in link.lower() for domain in cloud_domains)
                        if not is_cloud and link not in media_links:
                            filtered_links.append(link)
                    
                    if filtered_links:
                        print(f"  🔗 Enhanced: найдено файловых ссылок в контенте: {len(filtered_links)}")
                        for link in filtered_links:
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
            
        # Удаляем дубликаты и пересчитываем статистику
        unique_links = list(dict.fromkeys(media_links))
        
        # Пересчитываем статистику файлов без дубликатов
        found_files = []
        for link in unique_links:
            if '?f=' in link:
                filename = link.split('?f=')[-1]
            else:
                filename = link.split('/')[-1].split('?')[0]
            file_type = get_file_type(filename)
            found_files.append(file_type)
        
        if len(unique_links) > 0:
            # Подсчитываем статистику по типам файлов
            file_stats = {}
            for file_type in found_files:
                file_stats[file_type] = file_stats.get(file_type, 0) + 1
            
            print(f"   🎯 Найдено {len(unique_links)} файлов:")
            for file_type, count in file_stats.items():
                print(f"     • {file_type}: {count}")
            
            print(f"   📋 Список файлов:")
            for f in unique_links:
                # Получаем имя файла для отображения
                if '?f=' in f:
                    display_name = f.split('?f=')[-1]
                else:
                    display_name = f.split('/')[-1]
                file_type = get_file_type(display_name)
                print(f"     📎 {display_name} ({file_type})")
        else:
            print(f"   ⚠️ API не нашел файлы, пробуем HTML парсинг...")
            # Если API не нашел медиа, пробуем HTML
            html_media = get_post_media_from_html_fallback(post_url)
            if html_media:
                print(f"   ✅ HTML парсинг нашел {len(html_media)} файлов!")
                return html_media
            else:
                print(f"   ❌ Файлы не найдены")
            
        # Сохраняем облачные ссылки если найдены
        # Обрабатываем облачные ссылки и добавляем их к медиа файлам
        if 'cloud_links' in locals() and cloud_links and CLOUD_AUTO_ENABLED:
            try:
                print(f"  ☁️ Найдено облачных ссылок: {len(cloud_links)}")
                # Скачиваем облачные файлы в указанную папку
                if save_dir:
                    downloads_dir = save_dir
                else:
                    downloads_dir = os.path.join(os.getcwd(), "downloads")
                    
                # Сохраняем ссылки для истории
                save_cloud_links(downloads_dir, cloud_links, post_url)
                
                # Скачиваем облачные файлы
                downloader = CloudDownloader()
                for i, link_info in enumerate(cloud_links, 1):
                    service = link_info['service']
                    url = link_info['url']
                    print(f"    [{i}/{len(cloud_links)}] {service}: {url[:60]}...")
                    
                    try:
                        success = downloader.download_from_cloud(url, downloads_dir)
                        if success:
                            print(f"    ✅ {service} файл скачан")
                        else:
                            print(f"    ❌ Не удалось скачать {service} файл")
                    except Exception as e:
                        print(f"    ❌ Ошибка скачивания {service}: {e}")
                        
            except Exception as e:
                print(f"  ⚠️ Ошибка обработки облачных ссылок: {e}")
        
        return unique_links
            
    except Exception as e:
        print(f"  ❌ Ошибка парсинга URL или API: {e}")
        # Пробуем HTML fallback если API не сработал
        print(f"  🔄 Переключаемся на HTML парсинг...")
        return get_post_media_from_html_fallback(post_url)

def is_file_complete(filepath, expected_size=None):
    """Проверяет, что файл скачан полностью"""
    if not os.path.exists(filepath):
        return False
    
    file_size = os.path.getsize(filepath)
    
    # Файл считается неполным если он меньше 1KB (может быть обрезан)
    if file_size < 1024:
        return False
    
    # Если знаем ожидаемый размер, проверяем соответствие
    if expected_size and file_size != expected_size:
        return False
    
    return True

def get_download_progress_file(save_dir):
    """Возвращает путь к файлу прогресса загрузки"""
    return os.path.join(save_dir, '.kemono_progress.json')

def load_download_progress(save_dir):
    """Загружает прогресс загрузки из JSON файла"""
    progress_file = get_download_progress_file(save_dir)
    
    if not os.path.exists(progress_file):
        return {'completed_posts': [], 'completed_files': {}, 'started_at': None, 'last_update': None}
    
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Ошибка загрузки прогресса: {e}")
        return {'completed_posts': [], 'completed_files': {}, 'started_at': None, 'last_update': None}

def save_download_progress(save_dir, progress):
    """Сохраняет прогресс загрузки в JSON файл"""
    progress_file = get_download_progress_file(save_dir)
    progress['last_update'] = datetime.now().isoformat()
    
    try:
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Ошибка сохранения прогресса: {e}")

def download_files_parallel(media_links, save_dir, progress_data=None, max_workers=4, 
                           thread_callback=None, overall_callback=None, stop_check=None):
    """
    Скачивает файлы параллельно в несколько потоков
    thread_callback(thread_id, filename, progress, max_progress) - для обновления прогресса потоков
    overall_callback(current, total) - для обновления общего прогресса
    stop_check() - функция для проверки нужно ли остановить скачивание
    """
    if not media_links:
        return 0
    
    print(f"🚀 Многопоточное скачивание: {len(media_links)} файлов в {max_workers} потоков")
    
    success_count = 0
    total_count = len(media_links)
    completed_files = 0
    lock = threading.Lock()
    
    def download_with_progress(args):
        nonlocal completed_files, success_count
        url, index = args
        thread_id = index % max_workers  # Логический ID потока (0-4)
        
        # Проверяем нужно ли остановиться
        if stop_check and stop_check():
            return False
        
        # Получаем имя файла для отображения
        if '?f=' in url:
            filename = url.split('?f=')[-1]
        else:
            filename = url.split('/')[-1].split('?')[0]
        
        # Уведомляем GUI о начале скачивания файла в потоке
        if thread_callback:
            thread_callback(thread_id, filename, 0, 100)
            
        print(f"🔄 Поток-{thread_id}: Начинаем {filename[:40]}...")
        
        # Проверяем еще раз перед скачиванием
        if stop_check and stop_check():
            return False
            
        result = download_file(url, save_dir, progress_data)
        
        with lock:
            completed_files += 1
            if result:
                success_count += 1
            
            # Обновляем общий прогресс
            if overall_callback:
                overall_callback(completed_files, total_count)
            
            # Завершаем прогресс потока
            if thread_callback:
                thread_callback(thread_id, filename, 100, 100)
            
            status = '✅' if result else '❌'
            print(f"📥 [{completed_files}/{total_count}] Поток-{thread_id}: {status} {filename[:40]}")
        
        return result
    
    # Подготавливаем задачи
    tasks = [(url, i) for i, url in enumerate(media_links)]
    
    # Выполняем параллельно
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download_with_progress, task) for task in tasks]
        
        # Ждем завершения всех задач
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"❌ Ошибка в потоке: {e}")
    
    print(f"📊 Многопоточное скачивание завершено: {success_count}/{total_count} файлов")
    return success_count

def download_file(url, save_dir, progress_data=None):
    """Скачивает файл по URL с поддержкой резюме"""
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
        
        # Создаем уникальный ID файла для отслеживания
        file_id = hashlib.md5(url.encode()).hexdigest()
        
        # Проверяем существование и полноту файла
        if os.path.exists(filepath):
            if is_file_complete(filepath):
                print(f"✅ Уже скачано: {safe_filename}")
                
                # Обновляем прогресс
                if progress_data:
                    progress_data['completed_files'][file_id] = {
                        'url': url,
                        'filename': safe_filename,
                        'filepath': filepath,
                        'size': os.path.getsize(filepath),
                        'completed_at': datetime.now().isoformat()
                    }
                    save_download_progress(save_dir, progress_data)
                
                return True
            else:
                print(f"⚠️ Файл поврежден, перекачиваем: {safe_filename}")
                os.remove(filepath)
        
        # Пробуем скачать с оригинального URL
        start_time = time.time()
        response = requests.get(url, headers=HEADERS, verify=False, timeout=15, stream=True)
        
        if response.status_code == 200:
            # Получаем размер файла если доступен
            total_size = response.headers.get('content-length')
            if total_size:
                total_size = int(total_size)
                print(f"    📊 Размер: {total_size / 1024 / 1024:.1f} MB")
            
            with open(filepath, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=65536):  # 64KB chunks для скорости
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
            
            file_size = os.path.getsize(filepath)
            download_time = time.time() - start_time
            speed_mbps = (file_size / 1024 / 1024) / download_time if download_time > 0 else 0
            
            # Проверяем что файл скачался полностью
            if is_file_complete(filepath):
                print(f"    ✅ Скачано: {safe_filename} ({file_size / 1024 / 1024:.1f} MB, {speed_mbps:.1f} MB/s)")
                
                # Обновляем прогресс
                if progress_data:
                    progress_data['completed_files'][file_id] = {
                        'url': url,
                        'filename': safe_filename,
                        'filepath': filepath,
                        'size': file_size,
                        'completed_at': datetime.now().isoformat()
                    }
                    save_download_progress(save_dir, progress_data)
                
                return True
            else:
                print(f"    ❌ Файл скачался неполностью: {safe_filename}")
                os.remove(filepath)  # Удаляем поврежденный файл
                return False
        
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
                            
                            # Проверяем целостность
                            if is_file_complete(filepath):
                                print(f"    ✅ Найдено на {domain}: {safe_filename} ({file_size} байт)")
                                
                                # Обновляем прогресс
                                if progress_data:
                                    progress_data['completed_files'][file_id] = {
                                        'url': url,
                                        'filename': safe_filename,
                                        'filepath': filepath,
                                        'size': file_size,
                                        'completed_at': datetime.now().isoformat(),
                                        'domain': domain
                                    }
                                    save_download_progress(save_dir, progress_data)
                                
                                return True
                            else:
                                print(f"    ❌ Файл поврежден на {domain}: {safe_filename}")
                                os.remove(filepath)
                
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
        # Относительные ссылки img src="/..." (kemono файлы)
        r'<img[^>]*src="(/[^"]*\.(?:png|jpg|jpeg|gif|webp|svg|mp4|avi|mkv|mov|webm)[^"]*)"',
        # Любые a href="..." с медиа файлами
        r'<a[^>]*href="([^"]*(?:\.mp4|\.avi|\.mkv|\.mov|\.webm|\.zip|\.rar|\.jpg|\.png|\.gif|\.jpeg)[^"]*)"',
        # Любые ссылки на data/ папки kemono
        r'<[^>]*(?:href|src)="([^"]*(?:kemono\.cr|kemono\.party)[^"]*/data/[^"]*)"',
        # Относительные ссылки на data/ папки
        r'<[^>]*(?:href|src)="(/data/[^"]*)"',
    ]
    
    for pattern in html_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
        for match in matches:
            # Очищаем от HTML entities и лишних символов
            match = match.replace('&amp;', '&').rstrip('.,;:)')
            
            # Преобразуем относительные ссылки в полные
            if match.startswith('/'):
                match = 'https://kemono.cr' + match
            elif match.startswith('//'):
                match = 'https:' + match
            
            # Проверяем, что это НЕ облачная ссылка
            cloud_domains = ['drive.google.com', 'mega.nz', 'mega.co.nz', 'dropbox.com', 
                            'onedrive.live.com', '1drv.ms', 'mediafire.com', 'we.tl', 
                            'wetransfer.com', 'pcloud.com', 'disk.yandex.', 'box.com', 
                            'icloud.com', 'patreon.com/media-u']
            
            # Фильтруем облачные ссылки
            is_cloud = any(domain in match.lower() for domain in cloud_domains)
            
            if not is_cloud and match not in media_links:
                media_links.append(match)
                print(f"      📸 HTML тег: {match.split('/')[-1][:50]}...")
    
    # 2. Паттерны для поиска файлов в тексте (ИСКЛЮЧАЯ облачные хранилища)
    # Определяем облачные домены для фильтрации
    cloud_domains = ['drive.google.com', 'mega.nz', 'mega.co.nz', 'dropbox.com', 
                    'onedrive.live.com', '1drv.ms', 'mediafire.com', 'we.tl', 
                    'wetransfer.com', 'pcloud.com', 'disk.yandex.', 'box.com', 'icloud.com']
    
    url_patterns = [
        # Все поддерживаемые расширения
        r'https?://[^\s<>"]+\.(?:glb|gltf|blend|fbx|obj|dae|3ds|max|ma|mb)',  # 3D модели
        r'https?://[^\s<>"]+\.(?:mp4|avi|mkv|mov|webm|flv|wmv|m4v|mpg|mpeg)',  # Видео
        r'https?://[^\s<>"]+\.(?:png|jpg|jpeg|gif|bmp|tiff|tga|psd|webp|svg)',  # Изображения
        r'https?://[^\s<>"]+\.(?:zip|rar|7z|tar|gz|bz2|xz)',  # Архивы
        r'https?://[^\s<>"]+\.(?:pdf|doc|docx|txt|rtf)',  # Документы
        r'https?://[^\s<>"]+\.(?:mp3|wav|flac|ogg|m4a|aac)',  # Аудио
        r'https?://[^\s<>"]+\.(?:unity|unitypackage|prefab|asset)',  # Unity
        r'https?://[^\s<>"]+\.(?:dds|hdr|exr|mat)',  # Текстуры
        r'https?://[^\s<>"]+\.(?:exe|msi|dmg|apk|ipa)',  # Приложения
        # Kemono данные (ТОЛЬКО kemono, без облачных хранилищ)
        r'https?://[^\s<>"]*(?:kemono\.cr|kemono\.party)[^\s<>"]*/data/[^\s<>"]*',
    ]
    
    for pattern in url_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            # Очищаем от лишних символов в конце
            match = match.rstrip('.,;:)')
            
            # ВАЖНО: Проверяем, что это НЕ облачная ссылка
            is_cloud = any(domain in match.lower() for domain in cloud_domains)
            
            if not is_cloud and match not in media_links:
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
        
        # 3. Ищем ВСЕ ссылки на файлы (универсальный поиск)
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            filename = href.split('/')[-1].split('?')[0]
            
            # Проверяем все файлы с расширениями
            if '.' in filename and is_supported_file(filename):
                if href.startswith('/'):
                    href = f"https://kemono.cr{href}"
                elif not href.startswith('http'):
                    continue
                
                if href not in media_links:
                    media_links.append(href)
                    file_type = get_file_type(filename)
                    print(f"    🔗 HTML файл ({file_type}): {filename}")
        
        # Ищем облачные ссылки в HTML контенте
        page_content = soup.get_text()
        cloud_links = detect_cloud_links(str(soup) + page_content)
        
        if cloud_links:
            print(f"  ☁️ HTML парсинг нашел облачных ссылок: {len(cloud_links)}")
            cloud_stats = {}
            for link_info in cloud_links:
                service = link_info['service']
                cloud_stats[service] = cloud_stats.get(service, 0) + 1
            
            for service, count in cloud_stats.items():
                print(f"      ☁️ {service}: {count}")
            
            # Сохраняем облачные ссылки
            try:
                parts = post_url.split('/')
                if 'kemono.cr' in post_url and 'user' in parts:
                    service_idx = parts.index('kemono.cr') + 1
                    user_idx = parts.index('user')
                    service = parts[service_idx]
                    creator_id = parts[user_idx + 1]
                    
                    creator_folder = f"{service}_user_{creator_id}"
                    save_cloud_links(creator_folder, cloud_links, post_url)
                    
                    # Автоматически скачиваем облачные файлы если включено
                    if CLOUD_AUTO_ENABLED:
                        download_cloud_files(creator_folder, cloud_links, post_url)
            except Exception:
                pass
        
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

def download_post_media(post_url, save_dir, progress_data=None):
    """Скачивает медиа из одного поста с поддержкой резюме"""
    try:
        # Создаем ID поста для отслеживания
        post_id = hashlib.md5(post_url.encode()).hexdigest()
        
        # Проверяем, был ли этот пост уже обработан
        if progress_data and post_id in progress_data.get('completed_posts', []):
            print(f"📄 Пост уже обработан ранее: {post_url}")
            return True
        
        print(f"📄 Обрабатываем пост: {post_url}")
        
        # Получаем медиа файлы из поста
        media_links = get_post_media(post_url, enhanced_search=True, save_dir=save_dir)
        
        # Облачные файлы уже обработаны в get_post_media
        
        if not media_links:
            print(f"  ⚠️ Медиа не найдено в посте")
            return False
        
        print(f"  📁 Найдено файлов: {len(media_links)}")
        
        # Многопоточное скачивание
        success_count = download_files_parallel(media_links, save_dir, progress_data, max_workers=3)
        
        # Отмечаем пост как завершенный
        if progress_data:
            if 'completed_posts' not in progress_data:
                progress_data['completed_posts'] = []
            
            progress_data['completed_posts'].append(post_id)
            save_download_progress(save_dir, progress_data)
        
        print(f"  ✅ Пост завершен: {success_count}/{total_count} файлов")
        return success_count > 0
        
    except Exception as e:
        print(f"  ❌ Ошибка обработки поста: {e}")
        return False

def download_creator_posts(creator_url, save_dir, post_limit=None):
    """Скачивает все посты автора с поддержкой резюме"""
    try:
        print("🚀 Начинаем скачивание автора с поддержкой резюме...")
        
        # Загружаем прогресс
        progress_data = load_download_progress(save_dir)
        
        if not progress_data.get('started_at'):
            progress_data['started_at'] = datetime.now().isoformat()
            print("🆕 Новая загрузка автора")
        else:
            completed_posts = len(progress_data.get('completed_posts', []))
            completed_files = len(progress_data.get('completed_files', {}))
            print(f"🔄 Продолжаем загрузку автора")
            print(f"   Уже обработано постов: {completed_posts}")
            print(f"   Уже скачано файлов: {completed_files}")
        
        # Получаем все посты автора
        print("🔍 Получаем список постов...")
        all_posts = get_creator_posts(creator_url)
        
        if not all_posts:
            print("❌ Посты не найдены!")
            return False
        
        # Применяем лимит если указан
        if post_limit and post_limit > 0:
            posts = all_posts[:post_limit]
            print(f"🎯 Ограничиваем до {len(posts)} постов из {len(all_posts)}")
        else:
            posts = all_posts
            print(f"🎯 Обрабатываем ВСЕ {len(posts)} постов")
        
        # Фильтруем уже обработанные посты
        completed_post_ids = progress_data.get('completed_posts', [])
        pending_posts = []
        
        for post_url in posts:
            post_id = hashlib.md5(post_url.encode()).hexdigest()
            if post_id not in completed_post_ids:
                pending_posts.append(post_url)
        
        if not pending_posts:
            print("✅ Все посты уже обработаны!")
            return True
        
        print(f"📋 К обработке: {len(pending_posts)} постов (из {len(posts)} общих)")
        
        total_downloaded = 0
        
        for i, post_url in enumerate(pending_posts):
            print(f"\n📄 [{i+1}/{len(pending_posts)}] Обрабатываем пост...")
            
            if download_post_media(post_url, save_dir, progress_data):
                print(f"  ✅ Пост {i+1} завершен")
            else:
                print(f"  ⚠️ Пост {i+1} пропущен")
            
            # Минимальная пауза между постами
            if i < len(pending_posts) - 1:
                import time
                time.sleep(0.1)
        
        # Финальная статистика
        final_completed_posts = len(progress_data.get('completed_posts', []))
        final_completed_files = len(progress_data.get('completed_files', {}))
        
        print(f"\n🎉 ЗАГРУЗКА АВТОРА ЗАВЕРШЕНА!")
        print(f"   Обработано постов: {final_completed_posts}")
        print(f"   Скачано файлов: {final_completed_files}")
        print(f"📁 Все файлы в: {save_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ Критическая ошибка загрузки автора: {e}")
        return False

def show_download_status(save_dir):
    """Показывает статус текущей загрузки"""
    progress_data = load_download_progress(save_dir)
    
    if not progress_data.get('started_at'):
        print("📋 Загрузки в этой папке не найдены")
        return
    
    completed_posts = len(progress_data.get('completed_posts', []))
    completed_files = len(progress_data.get('completed_files', {}))
    started_at = progress_data.get('started_at', 'Неизвестно')
    last_update = progress_data.get('last_update', 'Неизвестно')
    
    print("📊 СТАТУС ЗАГРУЗКИ")
    print("="*50)
    print(f"📅 Начата: {started_at}")
    print(f"🔄 Последнее обновление: {last_update}")
    print(f"📄 Обработано постов: {completed_posts}")
    print(f"📁 Скачано файлов: {completed_files}")
    
    if completed_files > 0:
        print(f"\n📋 Последние скачанные файлы:")
        files = list(progress_data.get('completed_files', {}).values())
        for file_info in files[-5:]:  # Показываем последние 5
            filename = file_info.get('filename', 'unknown')
            size_mb = file_info.get('size', 0) / (1024 * 1024)
            print(f"  • {filename} ({size_mb:.1f} MB)")

def console_interface():
    """Консольный интерфейс для программы"""
    print("🦊 KemonoDownloader v2.8.1 Multithread - Console Edition")
    print("="*65)
    print("🎯 УНИВЕРСАЛЬНЫЙ ПОИСК ВСЕХ ФАЙЛОВ:")
    print("🎭 3D модели: GLB, GLTF, BLEND, FBX, OBJ, DAE, 3DS, MAX")
    print("🎬 Видео: MP4, MOV, AVI, MKV, WEBM, FLV, WMV")
    print("🖼️ Изображения: PNG, JPG, JPEG, GIF, BMP, TGA, PSD, SVG")
    print("📦 Архивы: ZIP, RAR, 7Z, TAR, GZ, BZ2, XZ")
    print("� Документы: PDF, DOC, DOCX, TXT, RTF")
    print("🎵 Аудио: MP3, WAV, FLAC, OGG, M4A, AAC")
    print("🎮 Unity: UNITY, UNITYPACKAGE, PREFAB, ASSET")
    print("🎨 Текстуры: DDS, HDR, EXR, MAT")
    print("📱 Приложения: EXE, MSI, DMG, APK, IPA")
    print("�🔄 Автоматическое продолжение после краша")
    print("="*65)
    print("")
    print("☁️ ПОДДЕРЖКА ОБЛАЧНЫХ ССЫЛОК:")
    print("🔗 Google Drive, MEGA, Dropbox, OneDrive")
    print("🔗 MediaFire, WeTransfer, pCloud, Yandex Disk")
    print("🔗 Box, iCloud и другие облачные сервисы")
    print("💾 Ссылки сохраняются в файл cloud_links.txt")
    
    print("🚄 МНОГОПОТОЧНОЕ СКАЧИВАНИЕ:")
    print("   ⚡ До 3 потоков одновременно для стабильной скорости")
    print("   📊 Прогресс отображается в реальном времени")
    
    # Показываем статус автоскачивания
    if CLOUD_AUTO_ENABLED:
        print("🚀 АВТОСКАЧИВАНИЕ ОБЛАЧНЫХ ФАЙЛОВ: ✅ ВКЛЮЧЕНО")
        print("   📁 Файлы сохраняются в ту же папку, что и медиа")
    else:
        print("⚠️ АВТОСКАЧИВАНИЕ ОБЛАЧНЫХ ФАЙЛОВ: ❌ ОТКЛЮЧЕНО")
        print("   💡 Для включения добавьте файл cloud_downloader.py")
        
    print("="*67)
    
    while True:
        try:
            print("\n🔗 Введите команду:")
            print("   • Ссылку на автора: https://kemono.cr/patreon/user/12345")
            print("   • Ссылку на пост: https://kemono.cr/patreon/user/12345/post/67890")
            print("   • 'status' - проверить статус загрузки в папке")
            print("   • 'exit' - выход")
            
            try:
                command = input("\n👉 Команда: ").strip()
            except EOFError:
                print("\n👋 До свидания!")
                break
            
            if command.lower() in ['exit', 'quit', 'выход', 'q']:
                print("👋 До свидания!")
                break
            
            if command.lower() == 'status':
                print(f"\n📁 Где проверить статус?")
                print("   • Введите путь к папке загрузок")
                print("   • Или нажмите Enter для текущей папки")
                
                try:
                    status_folder = input("👉 Папка: ").strip()
                except EOFError:
                    status_folder = "downloads"
                if not status_folder:
                    status_folder = "downloads"
                
                if os.path.exists(status_folder):
                    show_download_status(status_folder)
                else:
                    print("❌ Папка не найдена!")
                
                print("\n" + "="*50)
                try:
                    input("📌 Нажмите Enter для продолжения...")
                except (EOFError, KeyboardInterrupt):
                    break
                continue
            
            if not command:
                print("❌ Команда не может быть пустой!")
                continue
            
            # Обрабатываем как URL
            url = command
            if 'kemono.cr' not in url:
                print("❌ Поддерживаются только ссылки kemono.cr или команды!")
                continue
            
            print(f"\n📁 Где сохранить файлы?")
            print("   • Введите путь к папке")
            print("   • Или нажмите Enter для текущей папки")
            
            try:
                download_folder = input("👉 Папка: ").strip()
            except EOFError:
                download_folder = "downloads"
            
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
            try:
                input("📌 Нажмите Enter для продолжения...")
            except (EOFError, KeyboardInterrupt):
                break
            
        except KeyboardInterrupt:
            print("\n\n👋 Программа остановлена пользователем. До свидания!")
            break
        except EOFError:
            print("\n\n👋 Ввод завершен. До свидания!")
            break
        except Exception as e:
            print(f"\n❌ Произошла ошибка: {e}")
            try:
                input("📌 Нажмите Enter для продолжения...")
            except (EOFError, KeyboardInterrupt):
                print("\n👋 До свидания!")
                break

if __name__ == "__main__":
    console_interface()