#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🦊 KemonoDownloader v2.8 Cloud Auto - Cloud Files Downloader
===========================================================
Автоматическое скачивание файлов из облачных хранилищ
"""

import re
import requests
import os
from urllib.parse import urlparse, parse_qs
import time
import json

class CloudDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        })
        
    def download_from_cloud(self, url, save_dir, filename_hint=None):
        """
        Универсальная функция для скачивания из облачных сервисов
        """
        print(f"🌐 Анализируем облачную ссылку: {url[:80]}...")
        
        if 'drive.google.com' in url:
            return self._download_google_drive(url, save_dir, filename_hint)
        elif 'dropbox.com' in url:
            return self._download_dropbox(url, save_dir, filename_hint)
        elif 'mediafire.com' in url:
            return self._download_mediafire(url, save_dir, filename_hint)
        elif 'mega.nz' in url or 'mega.co.nz' in url:
            if '/folder/' in url:
                return self._download_mega_folder(url, save_dir, filename_hint)
            else:
                return self._download_mega(url, save_dir, filename_hint)
        else:
            print(f"❌ Автоскачивание для этого сервиса пока не поддерживается")
            return False
    
    def _download_google_drive(self, url, save_dir, filename_hint=None):
        """
        Скачивание файлов с Google Drive
        """
        print("📁 Google Drive: получаем прямую ссылку...")
        
        # Извлекаем file_id из разных форматов ссылок
        file_id = None
        
        # Формат: https://drive.google.com/file/d/FILE_ID/view?usp=sharing
        match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
        if match:
            file_id = match.group(1)
        
        # Формат: https://drive.google.com/open?id=FILE_ID
        if not file_id:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            if 'id' in query_params:
                file_id = query_params['id'][0]
        
        if not file_id:
            print("❌ Не удалось извлечь file_id из ссылки Google Drive")
            return False
        
        print(f"🔑 File ID: {file_id}")
        
        # Сначала получаем информацию о файле
        info_url = f"https://drive.google.com/file/d/{file_id}/view"
        try:
            response = self.session.get(info_url)
            if response.status_code != 200:
                print(f"❌ Ошибка получения информации: {response.status_code}")
                return False
            
            # Ищем имя файла в HTML
            filename = filename_hint or f"gdrive_file_{file_id}"
            title_match = re.search(r'<title>([^<]+)</title>', response.text)
            if title_match:
                title = title_match.group(1).strip()
                if title and title != "Google Drive":
                    filename = title.replace(' - Google Drive', '')
                    # Очищаем имя файла от недопустимых символов
                    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            
            print(f"📄 Имя файла: {filename}")
            
        except Exception as e:
            print(f"⚠️ Ошибка получения информации: {e}")
            filename = filename_hint or f"gdrive_file_{file_id}"
        
        # Прямая ссылка для скачивания
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        return self._download_file(download_url, save_dir, filename, handle_redirects=True)
    
    def _download_dropbox(self, url, save_dir, filename_hint=None):
        """
        Скачивание файлов с Dropbox (ИСПРАВЛЕНО: добавлено определение расширения)
        """
        print("📦 Dropbox: получаем прямую ссылку...")
        
        # Преобразуем обычную ссылку в прямую
        if '?dl=0' in url:
            direct_url = url.replace('?dl=0', '?dl=1')
        elif '?dl=1' not in url:
            direct_url = url + '?dl=1'
        else:
            direct_url = url
        
        # Извлекаем имя файла из URL
        filename = filename_hint
        if not filename:
            path_parts = urlparse(url).path.split('/')
            for part in reversed(path_parts):
                if part and '.' in part:
                    filename = part
                    break
            if not filename:
                filename = f"dropbox_file_{int(time.time())}"
        
        # НОВОЕ: Если в имени файла нет расширения, пытаемся определить его
        if '.' not in filename or filename.endswith('_'):
            print(f"⚠️ Файл без расширения: {filename}, пытаемся определить...")
            
            try:
                # Делаем HEAD запрос для получения заголовков
                head_response = self.session.head(direct_url, timeout=10)
                
                if head_response.status_code == 200:
                    # Пытаемся извлечь имя файла из заголовка Content-Disposition
                    content_disposition = head_response.headers.get('Content-Disposition', '')
                    if 'filename=' in content_disposition:
                        cd_filename = content_disposition.split('filename=')[-1].strip('"\'')
                        if cd_filename and '.' in cd_filename:
                            filename = cd_filename
                            print(f"✅ Имя файла из заголовка: {filename}")
                    
                    # Если все еще нет расширения, определяем по Content-Type
                    if '.' not in filename:
                        content_type = head_response.headers.get('Content-Type', '').lower()
                        extension = self._get_extension_from_mime_type(content_type)
                        if extension:
                            filename += extension
                            print(f"✅ Добавлено расширение по MIME: {filename}")
                        else:
                            filename += '.bin'  # Общее расширение для неизвестных файлов
                            print(f"⚠️ Неизвестный тип файла, добавлено .bin: {filename}")
                            
            except Exception as e:
                print(f"⚠️ Ошибка определения расширения: {e}")
                if '.' not in filename:
                    filename += '.bin'
        
        print(f"📄 Финальное имя файла: {filename}")
        
        return self._download_file(direct_url, save_dir, filename)
    
    def _download_mediafire(self, url, save_dir, filename_hint=None):
        """
        Скачивание файлов с MediaFire
        """
        print("🔥 MediaFire: получаем прямую ссылку...")
        
        try:
            # Получаем страницу файла
            response = self.session.get(url)
            if response.status_code != 200:
                print(f"❌ Ошибка получения страницы: {response.status_code}")
                return False
            
            # Ищем прямую ссылку для скачивания
            download_match = re.search(r'href="(https://download\d+\.mediafire\.com/[^"]+)"', response.text)
            if not download_match:
                print("❌ Не удалось найти прямую ссылку для скачивания")
                return False
            
            direct_url = download_match.group(1)
            
            # Ищем имя файла
            filename = filename_hint
            if not filename:
                filename_match = re.search(r'<div class="filename">([^<]+)</div>', response.text)
                if filename_match:
                    filename = filename_match.group(1).strip()
                else:
                    filename = f"mediafire_file_{int(time.time())}"
            
            print(f"📄 Имя файла: {filename}")
            print(f"🔗 Прямая ссылка: {direct_url[:80]}...")
            
            return self._download_file(direct_url, save_dir, filename)
            
        except Exception as e:
            print(f"❌ Ошибка обработки MediaFire: {e}")
            return False
    
    def _download_mega(self, url, save_dir, filename_hint=None):
        """
        Скачивание файлов с MEGA (базовая реализация)
        """
        print("🔒 MEGA: пробуем базовое скачивание...")
        print("⚠️ Для полной поддержки MEGA нужна библиотeka mega.py")
        print("💡 Установите: pip install mega.py")
        
        try:
            import mega
            print("✅ Библиотека mega.py найдена!")
            
            # Пробуем скачать через mega.py
            m = mega.Mega()
            m = m.login()  # Анонимный вход
            
            # Скачиваем файл
            filename = m.download_url(url, save_dir)
            if filename:
                print(f"✅ MEGA файл скачан: {filename}")
                return True
            else:
                print("❌ Не удалось скачать файл с MEGA")
                return False
                
        except ImportError:
            print("⚠️ Библиотека mega.py не установлена")
            print("💡 Установите командой: pip install mega.py")
            return False
        except Exception as e:
            print(f"❌ Ошибка скачивания с MEGA: {e}")
            return False
            
    def _download_mega_folder(self, url, save_dir, filename_hint=None):
        """
        Скачивание папок с MEGA через megalink или сохранение ссылки
        """
        print("📁 MEGA папка: пробуем скачать...")
        
        try:
            # Сначала пробуем megalink (альтернативная библиотека)
            try:
                import megalink
                print("✅ Библиотека megalink найдена!")
                
                # Создаем папку для MEGA скачиваний
                mega_folder = os.path.join(save_dir, "MEGA_folder")
                os.makedirs(mega_folder, exist_ok=True)
                
                # Пробуем скачать папку через megalink
                downloader = megalink.MegaDownloader()
                files = downloader.download(url, mega_folder)
                
                if files and len(files) > 0:
                    print(f"✅ MEGA папка скачана в: {mega_folder}")
                    print(f"📦 Скачано файлов: {len(files)}")
                    return True
                else:
                    raise Exception("Megalink не смог скачать файлы")
                    
            except ImportError:
                # Если megalink не установлен, пробуем mega.py
                import mega
                print("✅ Библиотека mega.py найдена (резервная)!")
                
                # Создаем папку для MEGA скачиваний
                mega_folder = os.path.join(save_dir, "MEGA_folder")
                os.makedirs(mega_folder, exist_ok=True)
                
                # Пробуем скачать папку - используем более простой подход
                m = mega.Mega()
                # Не используем login для анонимного доступа
                
                # Пробуем скачать папку
                files = m.download_url(url, mega_folder)
                if files:
                    print(f"✅ MEGA папка скачана в: {mega_folder}")
                    return True
                else:
                    raise Exception("Mega.py не смог скачать файлы")
                    
        except ImportError:
            print("⚠️ Библиотеки mega.py и megalink не установлены")
            print("💡 Установите одну из них:")
            print("   pip install mega.py")
            print("   pip install megalink")
            
        except Exception as e:
            print(f"❌ Ошибка скачивания MEGA папки: {e}")
            print("💡 Возможные решения:")
            print("   1. Установите: pip install megalink")
            print("   2. Или скачайте вручную: откройте ссылку в браузере")
        
        # В любом случае сохраняем ссылку в файл для ручного скачивания
        cloud_links_file = os.path.join(save_dir, "cloud_links.txt")
        with open(cloud_links_file, "a", encoding="utf-8") as f:
            f.write(f"MEGA папка (1.86 GB, 19 файлов, 7 папок): {url}\n")
            f.write(f"  📂 Инструкция: откройте ссылку в браузере и скачайте вручную\n")
            f.write(f"  📁 Рекомендуемая папка: {os.path.join(save_dir, 'MEGA_folder')}\n\n")
        print(f"📝 Ссылка сохранена в: {cloud_links_file}")
        print(f"📂 Откройте ссылку в браузере для ручного скачивания")
        return False
    
    def _download_file(self, url, save_dir, filename, handle_redirects=False):
        """
        Универсальная функция для скачивания файла
        """
        try:
            os.makedirs(save_dir, exist_ok=True)
            file_path = os.path.join(save_dir, filename)
            
            print(f"⬇️ Скачиваем: {filename}")
            
            # Специальная обработка для Google Drive редиректов
            if handle_redirects:
                response = self.session.get(url, stream=True, allow_redirects=False)
                
                # Обработка больших файлов Google Drive (virus scan warning)
                if response.status_code == 302 or 'Location' in response.headers:
                    redirect_url = response.headers.get('Location', url)
                    response = self.session.get(redirect_url, stream=True)
                elif 'virus scan warning' in response.text.lower():
                    # Ищем ссылку подтверждения
                    confirm_match = re.search(r'/uc\?export=download&amp;confirm=([^&]+)&amp;id=([^"]+)', response.text)
                    if confirm_match:
                        confirm_code = confirm_match.group(1)
                        file_id = confirm_match.group(2) 
                        confirm_url = f"https://drive.google.com/uc?export=download&confirm={confirm_code}&id={file_id}"
                        response = self.session.get(confirm_url, stream=True)
                        
            else:
                response = self.session.get(url, stream=True)
            
            if response.status_code != 200:
                print(f"❌ Ошибка скачивания: HTTP {response.status_code}")
                return False
            
            # Получаем размер файла если доступен
            total_size = int(response.headers.get('Content-Length', 0))
            
            with open(file_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Простой прогресс-бар
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\r📥 Прогресс: {progress:.1f}% ({downloaded}/{total_size} байт)", end='')
            
            print(f"\n✅ Файл скачан: {filename} ({downloaded} байт)")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка скачивания файла: {e}")
            return False
    
    def _get_extension_from_mime_type(self, mime_type):
        """
        НОВЫЙ: Определяет расширение файла по MIME-типу
        """
        mime_extensions = {
            # Изображения
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg', 
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'image/bmp': '.bmp',
            'image/tiff': '.tiff',
            'image/svg+xml': '.svg',
            
            # Видео
            'video/mp4': '.mp4',
            'video/avi': '.avi',
            'video/quicktime': '.mov',
            'video/x-msvideo': '.avi',
            'video/webm': '.webm',
            'video/x-flv': '.flv',
            
            # Аудио
            'audio/mpeg': '.mp3',
            'audio/mp3': '.mp3',
            'audio/wav': '.wav',
            'audio/x-wav': '.wav',
            'audio/flac': '.flac',
            'audio/ogg': '.ogg',
            
            # Архивы
            'application/zip': '.zip',
            'application/x-zip-compressed': '.zip',
            'application/x-rar-compressed': '.rar',
            'application/x-7z-compressed': '.7z',
            'application/x-tar': '.tar',
            'application/gzip': '.gz',
            
            # Документы
            'application/pdf': '.pdf',
            'application/msword': '.doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'text/plain': '.txt',
            'text/rtf': '.rtf',
            
            # 3D и прочее
            'model/gltf+json': '.gltf',
            'model/gltf-binary': '.glb',
            'application/octet-stream': '.bin',  # Общий тип для неизвестных файлов
        }
        
        return mime_extensions.get(mime_type.split(';')[0].strip(), None)

def test_cloud_downloader():
    """
    Тестирование облачного загрузчика
    """
    print("🧪 Тестируем CloudDownloader")
    print("=" * 50)
    
    downloader = CloudDownloader()
    test_dir = "cloud_test"
    
    # Тестовые ссылки (замените на реальные для тестирования)
    test_urls = [
        # "https://drive.google.com/file/d/YOUR_FILE_ID/view?usp=sharing",
        # "https://www.dropbox.com/s/YOUR_LINK/filename.zip?dl=0",
        # "https://www.mediafire.com/file/YOUR_LINK/filename.zip/file"
    ]
    
    for url in test_urls:
        print(f"\n🔗 Тестируем: {url}")
        success = downloader.download_from_cloud(url, test_dir)
        print(f"Результат: {'✅ Успех' if success else '❌ Ошибка'}")
    
    print("\n🎉 Тестирование завершено!")

if __name__ == "__main__":
    test_cloud_downloader()