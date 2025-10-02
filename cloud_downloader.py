#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🦊 KemonoDownloader v2.6 Cloud Auto - Cloud Files Downloader
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
        Скачивание файлов с Dropbox
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
        
        print(f"📄 Имя файла: {filename}")
        
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