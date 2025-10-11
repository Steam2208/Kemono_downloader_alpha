#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🦊 KemonoDownloader v2.8.5 Queue Edition - Multi-threaded File Downloader with Batch Processing

🆕 Новое в v2.8.5 Queue Edition:
- 📋 ОЧЕРЕДЬ АВТОРОВ - добавляйте множество авторов для пакетной загрузки!
- 🔄 Автоматическое переключение между авторами
- 💾 Сохранение и восстановление очереди при перезапуске
- 📊 Отдельные прогресс-бары для очереди авторов
- 🎯 Статусы авторов: ожидание, скачивание, завершено, ошибка
- ⚡ Возможность добавлять/удалять авторов прямо из GUI

Предыдущие возможности:
- 📊 Визуализация прогресса каждого потока в реальном времени
- 🚄 До 5 потоков скачивания одновременно
- 📈 Общий прогресс-бар скачивания файлов  
- 🔍 Чистый лог только с ошибками и важными сообщениями
- ☁️ АВТОМАТИЧЕСКОЕ СКАЧИВАНИЕ ИЗ ОБЛАЧНЫХ ХРАНИЛИЩ!
- 🗂️ УНИВЕРСАЛЬНЫЙ поиск ВСЕХ типов файлов (61 формат)
- 🌐 Поддержка Google Drive, MEGA, Dropbox, MediaFire
- 🎨 Поддержка 3D моделей: GLB, GLTF, BLEND, FBX, OBJ
- 🎮 Unity ресурсы: UNITY, UNITYPACKAGE, PREFAB
- 📁 Облачные файлы сохраняются в ту же папку, что и медиа
"""

import sys
import os
import time
import threading
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, 
                           QProgressBar, QSpinBox, QDoubleSpinBox, QCheckBox,
                           QFileDialog, QGroupBox, QGridLayout, QMessageBox, QListWidget, 
                           QListWidgetItem, QTabWidget, QSplitter)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QSettings
from PyQt6.QtGui import QFont, QIcon

# Импорт нашего улучшенного движка без fake-useragent (с автопоиском доменов)
sys.path.append(os.path.dirname(__file__))
from downloader_static import (get_creator_posts, get_post_media, download_file, 
                              load_download_progress, save_download_progress, 
                              download_creator_posts, show_download_status,
                              detect_cloud_links, download_cloud_files,
                              download_files_parallel)
import requests
import urllib3
import hashlib
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class QueueManager:
    """Класс для управления очередью авторов"""
    
    def __init__(self, queue_file="authors_queue.json"):
        self.queue_file = queue_file
        self.authors_queue = []
        self.current_index = 0
        self.load_queue()
    
    def add_author(self, author_url, author_name=None):
        """Добавляет автора в очередь"""
        if not author_name:
            author_name = self._extract_author_name(author_url)
        
        # Проверяем, что автор не дублируется
        for author in self.authors_queue:
            if author['url'] == author_url:
                return False, f"Автор уже в очереди: {author['name']}"
        
        author_data = {
            'url': author_url,
            'name': author_name,
            'status': 'pending',  # pending, downloading, completed, error
            'added_time': datetime.now().isoformat()
        }
        
        self.authors_queue.append(author_data)
        self.save_queue()
        return True, f"Добавлен: {author_name}"
    
    def remove_author(self, index):
        """Удаляет автора из очереди по индексу"""
        if 0 <= index < len(self.authors_queue):
            removed = self.authors_queue.pop(index)
            if index <= self.current_index and self.current_index > 0:
                self.current_index -= 1
            self.save_queue()
            return True, f"Удален: {removed['name']}"
        return False, "Неверный индекс"
    
    def clear_queue(self):
        """Очищает всю очередь"""
        self.authors_queue.clear()
        self.current_index = 0
        self.save_queue()
    
    def get_next_author(self):
        """Получает следующего автора для скачивания"""
        if self.current_index < len(self.authors_queue):
            author = self.authors_queue[self.current_index]
            if author['status'] in ['pending', 'error']:
                return author
            else:
                self.current_index += 1
                return self.get_next_author()
        return None
    
    def mark_current_completed(self):
        """Отмечает текущего автора как завершенного"""
        if self.current_index < len(self.authors_queue):
            self.authors_queue[self.current_index]['status'] = 'completed'
            self.current_index += 1
            self.save_queue()
    
    def mark_current_error(self, error_msg=""):
        """Отмечает текущего автора как ошибочного"""
        if self.current_index < len(self.authors_queue):
            self.authors_queue[self.current_index]['status'] = 'error'
            self.authors_queue[self.current_index]['error'] = error_msg
            self.save_queue()
    
    def mark_current_downloading(self):
        """Отмечает текущего автора как скачивающегося"""
        if self.current_index < len(self.authors_queue):
            self.authors_queue[self.current_index]['status'] = 'downloading'
            self.save_queue()
    
    def get_queue_status(self):
        """Возвращает статистику очереди"""
        total = len(self.authors_queue)
        completed = sum(1 for a in self.authors_queue if a['status'] == 'completed')
        pending = sum(1 for a in self.authors_queue if a['status'] == 'pending')
        error = sum(1 for a in self.authors_queue if a['status'] == 'error')
        downloading = sum(1 for a in self.authors_queue if a['status'] == 'downloading')
        
        return {
            'total': total,
            'completed': completed,
            'pending': pending,
            'error': error,
            'downloading': downloading,
            'current_index': self.current_index
        }
    
    def has_pending_authors(self):
        """Проверяет, есть ли авторы для скачивания"""
        return any(author['status'] in ['pending', 'error'] 
                  for author in self.authors_queue[self.current_index:])
    
    def reset_queue(self):
        """Сбрасывает очередь к началу"""
        self.current_index = 0
        for author in self.authors_queue:
            if author['status'] in ['downloading', 'error']:
                author['status'] = 'pending'
        self.save_queue()
    
    def save_queue(self):
        """Сохраняет очередь в файл"""
        try:
            queue_data = {
                'authors': self.authors_queue,
                'current_index': self.current_index,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump(queue_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения очереди: {e}")
    
    def load_queue(self):
        """Загружает очередь из файла"""
        try:
            if os.path.exists(self.queue_file):
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    queue_data = json.load(f)
                    self.authors_queue = queue_data.get('authors', [])
                    self.current_index = queue_data.get('current_index', 0)
        except Exception as e:
            print(f"Ошибка загрузки очереди: {e}")
            self.authors_queue = []
            self.current_index = 0
    
    def _extract_author_name(self, url):
        """Извлекает имя автора из URL"""
        try:
            # Парсим URL для извлечения service и creator_id
            parts = url.split('/')
            if 'user' in parts:
                user_idx = parts.index('user')
                if user_idx + 1 < len(parts):
                    service_idx = user_idx - 1
                    if service_idx >= 0:
                        service = parts[service_idx]
                        creator_id = parts[user_idx + 1]
                        return f"{service}_{creator_id}"
            return f"author_{hash(url) % 10000}"
        except:
            return f"author_{hash(url) % 10000}"

class DownloaderWorker(QThread):
    """Рабочий поток для скачивания"""
    progress = pyqtSignal(int, int)  # текущий, всего
    thread_progress = pyqtSignal(int, str, int, int)  # thread_id, filename, current, total 
    overall_progress = pyqtSignal(int, int)  # completed_files, total_files
    log = pyqtSignal(str)  # только ошибки и важные сообщения
    finished = pyqtSignal(int)  # количество скачанных файлов
    queue_progress = pyqtSignal(int, int, str)  # current_author_index, total_authors, current_author_name
    
    def __init__(self, settings, queue_manager):
        super().__init__()
        self.settings = settings
        self.queue_manager = queue_manager
        self.running = True
        self.is_queue_mode = True  # Всегда используем режим очереди
        
    def stop(self):
        self.running = False
        
    def extract_creator_info(self, url):
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
    
    def get_creator_info(self, service, creator_id):
        """Получает информацию автора через API"""
        try:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://kemono.cr/',
                'Accept': 'text/css',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            })
            
            url = f"https://kemono.cr/api/v1/{service}/user/{creator_id}"
            response = session.get(url, verify=False, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                name = data.get('name', f'Unknown_{creator_id}')
                # Очищаем имя от запрещенных символов для папки
                safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_name = safe_name.replace(' ', '_')  # Заменяем пробелы на подчеркивания
                if not safe_name:
                    safe_name = f'Creator_{creator_id}'
                
                return {
                    'name': name,  # Оригинальное имя для отображения
                    'safe_name': safe_name,  # Безопасное имя для папки
                    'service': data.get('service', service),
                    'id': creator_id
                }
            
        except Exception as e:
            self.log.emit(f"❌ Ошибка получения информации автора: {e}")
        
        return {
            'name': f'Creator {creator_id}',
            'safe_name': f'Creator_{creator_id}',
            'service': service,
            'id': creator_id
        }
    
    def run(self):
        try:
            if self.is_queue_mode:
                # Режим очереди авторов
                self.log.emit("� Запускаем очередь авторов...")
                self.run_queue()
            else:
                # Режим одного автора
                self.log.emit("�🚀 Начинаем скачивание одного автора...")
                self.run_single_author(self.creator_url)
                
        except Exception as e:
            self.log.emit(f"❌ Критическая ошибка: {e}")
            self.finished.emit(0)
    
    def run_queue(self):
        """Запускает скачивание очереди авторов"""
        total_downloaded = 0
        queue_status = self.queue_manager.get_queue_status()
        
        self.log.emit(f"📋 Очередь: {queue_status['total']} авторов")
        self.log.emit(f"   Ожидают: {queue_status['pending']}")
        self.log.emit(f"   Завершено: {queue_status['completed']}")
        self.log.emit(f"   Ошибки: {queue_status['error']}")
        
        # Обрабатываем авторов по очереди
        while self.running and self.queue_manager.has_pending_authors():
            # Получаем следующего автора
            current_author = self.queue_manager.get_next_author()
            if not current_author:
                break
            
            # Обновляем прогресс очереди
            queue_status = self.queue_manager.get_queue_status()
            self.queue_progress.emit(
                queue_status['current_index'], 
                queue_status['total'], 
                current_author['name']
            )
            
            self.log.emit(f"\n👤 Скачиваем автора: {current_author['name']}")
            self.log.emit(f"🔗 URL: {current_author['url']}")
            
            # Отмечаем автора как скачивающегося
            self.queue_manager.mark_current_downloading()
            
            try:
                # Скачиваем автора
                author_downloaded = self.run_single_author(current_author['url'])
                total_downloaded += author_downloaded
                
                # Отмечаем автора как завершенного
                self.queue_manager.mark_current_completed()
                self.log.emit(f"✅ Автор {current_author['name']} завершен! Скачано файлов: {author_downloaded}")
                
            except Exception as e:
                # Отмечаем автора как ошибочного
                error_msg = str(e)
                self.queue_manager.mark_current_error(error_msg)
                self.log.emit(f"❌ Ошибка автора {current_author['name']}: {error_msg}")
        
        # Финальная статистика
        final_status = self.queue_manager.get_queue_status()
        self.log.emit(f"\n🎉 ОЧЕРЕДЬ ЗАВЕРШЕНА!")
        self.log.emit(f"   Всего авторов: {final_status['total']}")
        self.log.emit(f"   Завершено: {final_status['completed']}")
        self.log.emit(f"   Ошибок: {final_status['error']}")
        self.log.emit(f"   Всего файлов скачано: {total_downloaded}")
        
        self.finished.emit(total_downloaded)
    
    def run_single_author(self, creator_url):
        """Скачивает одного автора и возвращает количество скачанных файлов"""
        # Извлекаем информацию об авторе
        service, creator_id = self.extract_creator_info(creator_url)
        if not service or not creator_id:
            self.log.emit("❌ Неверный формат URL!")
            return 0
        
        self.log.emit(f"🎯 Service: {service}, Creator ID: {creator_id}")
        
        # Получаем информацию об авторе
        creator_info = self.get_creator_info(service, creator_id)
        self.log.emit(f"👤 Автор: {creator_info['name']}")
        self.log.emit(f"🏷️ Service: {creator_info['service']}")
        
        # Создаем структуру папок: downloads/service/author_name_id/
        service_dir = os.path.join(self.settings['download_dir'], creator_info['service'])
        folder_name = f"{creator_info['safe_name']}_{creator_info['id']}"
        save_dir = os.path.join(service_dir, folder_name)
        os.makedirs(save_dir, exist_ok=True)
        self.log.emit(f"📁 Папка: {save_dir}")
        
        # Загружаем прогресс загрузки
        progress_data = load_download_progress(save_dir)
        
        if not progress_data.get('started_at'):
            progress_data['started_at'] = datetime.now().isoformat()
            self.log.emit("🆕 Новая загрузка автора")
        else:
            completed_posts = len(progress_data.get('completed_posts', []))
            completed_files = len(progress_data.get('completed_files', {}))
            self.log.emit(f"🔄 Продолжаем загрузку автора")
            self.log.emit(f"   Уже обработано постов: {completed_posts}")
            self.log.emit(f"   Уже скачано файлов: {completed_files}")
        
        # Получаем все посты автора
        self.log.emit("🔍 Получаем список постов...")
        all_posts = get_creator_posts(creator_url)
        
        if not all_posts:
            self.log.emit("❌ Посты не найдены!")
            return 0
        
        # Применяем лимит если указан
        if self.settings['post_limit'] and self.settings['post_limit'] > 0:
            posts = all_posts[:self.settings['post_limit']]
            self.log.emit(f"🎯 Ограничиваем до {len(posts)} постов из {len(all_posts)}")
        else:
            posts = all_posts
            self.log.emit(f"🎯 Обрабатываем ВСЕ {len(posts)} постов")
        
        # Фильтруем уже обработанные посты
        completed_post_ids = progress_data.get('completed_posts', [])
        pending_posts = []
        
        for post_url in posts:
            post_id = hashlib.md5(post_url.encode()).hexdigest()
            if post_id not in completed_post_ids:
                pending_posts.append(post_url)
        
        if not pending_posts:
            self.log.emit("✅ Все посты уже обработаны!")
            completed_files = len(progress_data.get('completed_files', {}))
            return completed_files
        
        self.log.emit(f"📋 К обработке: {len(pending_posts)} новых постов (из {len(posts)} общих)")
        
        # НОВАЯ ЛОГИКА: Сначала собираем ВСЕ файлы, потом скачиваем массово
        total_downloaded = len(progress_data.get('completed_files', {}))  # Уже скачанные файлы
        
        self.log.emit(f"🔍 Шаг 1: Собираем файлы из {len(pending_posts)} постов...")
        
        # Собираем все файлы из всех постов
        all_media_links = []
        processed_posts = []
        
        for i, post_url in enumerate(pending_posts):
            if not self.running:
                break
                
            self.progress.emit(i, len(pending_posts))
            self.log.emit(f"📄 [{i + 1}/{len(pending_posts)}] Анализируем пост...")
                
            try:
                post_id = hashlib.md5(post_url.encode()).hexdigest()
                
                # Получаем файлы из поста
                media_links = get_post_media(post_url, enhanced_search=True, save_dir=save_dir)
                
                if media_links:
                    self.log.emit(f"   📎 Найдено {len(media_links)} файлов")
                    all_media_links.extend(media_links)
                    processed_posts.append(post_id)
                else:
                    self.log.emit(f"   ⚠️ Медиа не найдено")
                    processed_posts.append(post_id)  # Все равно отмечаем как обработанный
                    
            except Exception as e:
                self.log.emit(f"❌ Ошибка поста {i + 1}: {e}")
        
        # Проверяем, есть ли файлы для скачивания
        if not all_media_links:
            self.log.emit("⚠️ Не найдено файлов для скачивания")
            # Отмечаем все посты как завершенные
            if 'completed_posts' not in progress_data:
                progress_data['completed_posts'] = []
            progress_data['completed_posts'].extend(processed_posts)
            save_download_progress(save_dir, progress_data)
            return 0
        else:
            # Получаем количество потоков из настроек
            max_workers = self.settings.get('threads_count', 5)
            self.log.emit(f"🚀 Шаг 2: Многопоточное скачивание {len(all_media_links)} файлов в {max_workers} потоков!")
            
            # МАССОВОЕ многопоточное скачивание ВСЕХ файлов
            downloaded_count = download_files_parallel(
                all_media_links, 
                save_dir, 
                progress_data, 
                max_workers=max_workers,
                thread_callback=self.thread_progress.emit,
                overall_callback=self.overall_progress.emit,
                stop_check=lambda: not self.running
            )
            
            total_downloaded += downloaded_count
            
            # Отмечаем все посты как завершенные
            if 'completed_posts' not in progress_data:
                progress_data['completed_posts'] = []
            progress_data['completed_posts'].extend(processed_posts)
            save_download_progress(save_dir, progress_data)
            
            self.log.emit(f"✅ Массовое скачивание завершено: {downloaded_count} файлов")
            
            # НОВОЕ: Скачиваем облачные файлы после обычных (если включено)
            if self.running and self.settings.get('download_cloud', True):
                self.log.emit("🌐 Шаг 3: Проверяем облачные файлы...")
                cloud_links_file = os.path.join(save_dir, "cloud_links.txt")
                if os.path.exists(cloud_links_file):
                    try:
                        # Читаем облачные ссылки из файла
                        with open(cloud_links_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Парсим облачные ссылки
                        from downloader_static import detect_cloud_links
                        cloud_links = detect_cloud_links(content)
                        
                        if cloud_links:
                            self.log.emit(f"☁️ Найдено {len(cloud_links)} облачных ссылок для скачивания")
                            
                            # Скачиваем облачные файлы
                            from downloader_static import download_cloud_files
                            cloud_downloaded = download_cloud_files(save_dir, cloud_links, "batch_download")
                            
                            if cloud_downloaded:
                                self.log.emit(f"✅ Облачных файлов скачано: {len(cloud_downloaded)}")
                                total_downloaded += len(cloud_downloaded)
                            else:
                                self.log.emit("⚠️ Облачные файлы не скачались")
                        else:
                            self.log.emit("ℹ️ Облачных ссылок не найдено")
                    except Exception as e:
                        self.log.emit(f"⚠️ Ошибка обработки облачных файлов: {e}")
                else:
                    self.log.emit("ℹ️ Файл cloud_links.txt не найден")
            elif self.running:
                self.log.emit("⚙️ Скачивание облачных файлов отключено в настройках")
        
        if self.running:
            self.log.emit(f"✅ Автор завершен! Скачано {total_downloaded} файлов")
            self.log.emit(f"📁 Все файлы в: {save_dir}")
        else:
            self.log.emit(f"⏹️ Автор остановлен. Скачано {total_downloaded} файлов")
        
        return total_downloaded

class KemonoDownloaderGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.settings = QSettings("KemonoDownloader", "GUI")
        self.queue_manager = QueueManager()
        self.init_ui()
        self.load_settings()
        self.update_queue_display()
        
    def init_ui(self):
        self.setWindowTitle("KemonoDownloader v2.8.5 - Compact Mode")
        self.setGeometry(100, 100, 900, 550)  # Компактный: шире, но ниже
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # ГЛАВНЫЙ горизонтальный layout (логи слева, остальное справа)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(8, 8, 8, 8)
        
        # ========== ЛЕВАЯ ПАНЕЛЬ - ЛОГИ ==========
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        
        # Лог (слева, во всю высоту)
        log_group = QGroupBox("Лог")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(6, 12, 6, 6)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumWidth(300)  # Фиксированная ширина логов
        self.log_text.setStyleSheet("font-size: 9px;")  # Мелкий шрифт для экономии места
        log_layout.addWidget(self.log_text)
        
        left_layout.addWidget(log_group)
        left_panel.setMaximumWidth(320)  # Ограничиваем ширину левой панели
        
        # ========== ПРАВАЯ ПАНЕЛЬ - ОСНОВНОЙ ИНТЕРФЕЙС ==========
        right_panel = QWidget()
        layout = QVBoxLayout(right_panel)  # Это будет основной layout для правой части
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # URL ввод - многострочное поле для множества авторов
        url_group = QGroupBox("URLs авторов")
        url_layout = QVBoxLayout(url_group)
        url_layout.setContentsMargins(8, 16, 8, 8)
        url_layout.setSpacing(4)
        
        # Инструкция
        instruction_label = QLabel("Введите URL авторов (по одному на строку):")
        instruction_label.setStyleSheet("color: #666; font-size: 11px;")
        url_layout.addWidget(instruction_label)
        
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText("https://kemono.cr/patreon/user/12345678\nhttps://kemono.cr/fanbox/user/87654321\nhttps://kemono.cr/subscribestar/user/11111111")
        self.url_input.setFixedHeight(60)  # Компактнее
        self.url_input.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 10px;")
        url_layout.addWidget(self.url_input)
        
        # Статус (автоматическая обработка)
        self.queue_status_label = QLabel("📝 Вставьте URL авторов выше, затем нажмите 'Скачать' ↓")
        self.queue_status_label.setStyleSheet("color: #666; font-size: 11px; text-align: center; padding: 8px;")
        url_layout.addWidget(self.queue_status_label)
        
        # Список авторов в очереди (компактный)
        self.queue_list = QListWidget()
        self.queue_list.setMaximumHeight(45)  # Еще компактнее
        self.queue_list.setStyleSheet("font-size: 9px;")  # Мелкий шрифт
        # Убрана связь с кнопкой удаления (кнопок больше нет)
        url_layout.addWidget(self.queue_list)
        
        # Прогресс очереди
        queue_progress_layout = QHBoxLayout()
        queue_progress_layout.setSpacing(8)
        
        self.queue_progress_label = QLabel("Очередь: 0/0")
        queue_progress_layout.addWidget(self.queue_progress_label)
        
        self.queue_progress = QProgressBar()
        self.queue_progress.setFixedHeight(16)
        queue_progress_layout.addWidget(self.queue_progress)
        
        url_layout.addLayout(queue_progress_layout)
        
        layout.addWidget(url_group)
        
        # Настройки
        settings_group = QGroupBox("Настройки")
        settings_layout = QGridLayout(settings_group)
        settings_layout.setContentsMargins(8, 16, 8, 8)
        settings_layout.setHorizontalSpacing(8)
        settings_layout.setVerticalSpacing(6)
        
        # --- Современная секция выбора папки ---
        folder_label = QLabel("Папка:")
        folder_label.setMinimumWidth(50)
        settings_layout.addWidget(folder_label, 0, 0)

        self.download_dir_input = QLineEdit()
        self.download_dir_input.setText(os.path.join(os.getcwd(), "downloads"))
        self.download_dir_input.setMinimumHeight(32)
        self.download_dir_input.setMinimumWidth(350)
        self.download_dir_input.setStyleSheet("QLineEdit { font-size: 12px; padding-left: 10px; padding-right: 10px; }")
        settings_layout.addWidget(self.download_dir_input, 0, 1)

        self.browse_btn = QPushButton("Обзор")
        self.browse_btn.setMinimumHeight(32)
        self.browse_btn.setMinimumWidth(70)
        self.browse_btn.setStyleSheet("QPushButton { font-size: 12px; padding: 0 12px; }")
        self.browse_btn.clicked.connect(self.browse_directory)
        settings_layout.addWidget(self.browse_btn, 0, 2)
        
        # Лимит постов
        settings_layout.addWidget(QLabel("Лимит:"), 1, 0)
        self.post_limit_input = QSpinBox()
        self.post_limit_input.setRange(0, 10000)
        self.post_limit_input.setValue(0)
        self.post_limit_input.setSpecialValueText("Все")
        self.post_limit_input.setFixedHeight(28)
        self.post_limit_input.valueChanged.connect(self.save_settings)
        settings_layout.addWidget(self.post_limit_input, 1, 1)
        
        # Количество потоков
        settings_layout.addWidget(QLabel("Потоки:"), 2, 0)
        self.threads_count_input = QSpinBox()
        self.threads_count_input.setRange(1, 10)
        self.threads_count_input.setValue(5)
        self.threads_count_input.setFixedHeight(28)
        self.threads_count_input.valueChanged.connect(self.update_thread_bars)
        self.threads_count_input.valueChanged.connect(self.save_settings)
        settings_layout.addWidget(self.threads_count_input, 2, 1)
        
        # Темная тема
        settings_layout.addWidget(QLabel("Тема:"), 3, 0)
        self.dark_theme_checkbox = QCheckBox("Темная")
        self.dark_theme_checkbox.setChecked(True)
        self.dark_theme_checkbox.stateChanged.connect(self.toggle_theme)
        settings_layout.addWidget(self.dark_theme_checkbox, 3, 1)
        
        # Скачивание облачных файлов
        settings_layout.addWidget(QLabel("Облако:"), 4, 0)
        self.download_cloud_checkbox = QCheckBox("Скачивать")
        self.download_cloud_checkbox.setChecked(True)  # По умолчанию включено
        self.download_cloud_checkbox.setToolTip("Скачивать файлы из облачных сервисов (Dropbox, Google Drive, MEGA)")
        self.download_cloud_checkbox.stateChanged.connect(self.save_settings)
        settings_layout.addWidget(self.download_cloud_checkbox, 4, 1)
        
        layout.addWidget(settings_group)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(6)
        
        # Одна главная кнопка - автоматически обрабатывает авторов из текстового поля
        self.start_btn = QPushButton("Скачать")
        self.start_btn.clicked.connect(self.auto_process_and_download)
        self.start_btn.setProperty("class", "success")
        self.start_btn.setFixedHeight(32)
        self.start_btn.setToolTip("Автоматически обрабатывает URL авторов и запускает скачивание")
        buttons_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Стоп")
        self.stop_btn.clicked.connect(self.stop_download)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setProperty("class", "danger")
        self.stop_btn.setFixedHeight(32)
        buttons_layout.addWidget(self.stop_btn)
        
        self.open_folder_btn = QPushButton("Папка")
        self.open_folder_btn.clicked.connect(self.open_download_folder)
        self.open_folder_btn.setProperty("class", "primary")
        self.open_folder_btn.setFixedHeight(32)
        buttons_layout.addWidget(self.open_folder_btn)
        
        self.status_btn = QPushButton("Статус")
        self.status_btn.clicked.connect(self.show_download_status)
        self.status_btn.setProperty("class", "info")
        self.status_btn.setFixedHeight(32)
        buttons_layout.addWidget(self.status_btn)
        
        self.formats_btn = QPushButton("Форматы")
        self.formats_btn.clicked.connect(self.show_supported_formats)
        self.formats_btn.setProperty("class", "primary")
        self.formats_btn.setFixedHeight(32)
        buttons_layout.addWidget(self.formats_btn)
        
        layout.addLayout(buttons_layout)
        
        # Прогресс
        progress_group = QGroupBox("Прогресс")
        progress_main_layout = QVBoxLayout(progress_group)
        progress_main_layout.setContentsMargins(8, 16, 8, 8)
        progress_main_layout.setSpacing(4)
        
        # Горизонтальная компоновка
        progress_horizontal = QHBoxLayout()
        progress_horizontal.setSpacing(12)
        
        # Основные прогресс-бары
        main_progress_container = QWidget()
        main_progress_layout = QVBoxLayout(main_progress_container)
        main_progress_layout.setContentsMargins(0, 0, 0, 0)
        main_progress_layout.setSpacing(4)
        
        # Файлы
        self.overall_progress_label = QLabel("Файлы: 0/0")
        main_progress_layout.addWidget(self.overall_progress_label)
        
        self.overall_progress = QProgressBar()
        self.overall_progress.setFixedHeight(18)
        main_progress_layout.addWidget(self.overall_progress)
        
        # Посты
        self.post_progress_label = QLabel("Посты: 0/0") 
        main_progress_layout.addWidget(self.post_progress_label)
        
        self.post_progress = QProgressBar()
        self.post_progress.setFixedHeight(18)
        main_progress_layout.addWidget(self.post_progress)
        
        progress_horizontal.addWidget(main_progress_container)
        
        # Потоки
        threads_container = QWidget()
        threads_layout = QVBoxLayout(threads_container)
        threads_layout.setContentsMargins(0, 0, 0, 0)
        threads_layout.setSpacing(2)
        
        threads_label = QLabel("Потоки:")
        threads_label.setFixedHeight(14)
        threads_layout.addWidget(threads_label)
        
        self.threads_bars_container = QWidget()
        self.threads_bars_layout = QHBoxLayout(self.threads_bars_container)
        self.threads_bars_layout.setContentsMargins(0, 0, 0, 0)
        self.threads_bars_layout.setSpacing(3)
        
        self.thread_progress_bars = []
        self.thread_labels = []
        
        self.create_thread_bars(5)
        
        threads_layout.addWidget(self.threads_bars_container)
        progress_horizontal.addWidget(threads_container)
        
        # Добавляем горизонтальную компоновку в основной layout
        progress_main_layout.addLayout(progress_horizontal)
        
        layout.addWidget(progress_group)
        
        # ========== СБОРКА ПАНЕЛЕЙ ==========
        # Добавляем панели в главный горизонтальный layout
        main_layout.addWidget(left_panel)   # Логи слева
        main_layout.addWidget(right_panel)  # Интерфейс справа
        
        # Статус бар
        self.statusBar().showMessage("Готов - Компактный режим")
    
    def create_thread_bars(self, count):
        """Создает указанное количество прогресс-баров потоков"""
        self.clear_thread_bars()
        
        for i in range(count):
            thread_progress = QProgressBar()
            thread_progress.setOrientation(Qt.Orientation.Vertical)
            thread_progress.setFixedWidth(8)
            thread_progress.setFixedHeight(44)
            thread_progress.setTextVisible(False)
            thread_progress.setValue(0)
            thread_progress.setMaximum(100)
            self.thread_progress_bars.append(thread_progress)
            
            thread_label = QLabel("Ожидание...")
            thread_label.setVisible(False)
            self.thread_labels.append(thread_label)
            
            self.threads_bars_layout.addWidget(thread_progress)
    
    def clear_thread_bars(self):
        """Удаляет все существующие прогресс-бары потоков"""
        # Удаляем виджеты из layout и памяти
        for progress_bar in self.thread_progress_bars:
            self.threads_bars_layout.removeWidget(progress_bar)
            progress_bar.deleteLater()
        
        # Очищаем списки
        self.thread_progress_bars.clear()
        self.thread_labels.clear()
    
    def update_thread_bars(self):
        """Обновляет количество прогресс-баров потоков согласно настройке"""
        new_count = self.threads_count_input.value()
        self.create_thread_bars(new_count)

    def load_settings(self):
        """Загружает сохраненные настройки"""
        self.download_dir_input.setText(
            self.settings.value("download_dir", os.path.join(os.getcwd(), "downloads"))
        )
        self.post_limit_input.setValue(
            int(self.settings.value("post_limit", 0))
        )
        
        # Загружаем количество потоков
        threads_count = int(self.settings.value("threads_count", 5))
        self.threads_count_input.setValue(threads_count)
        self.create_thread_bars(threads_count)  # Создаем нужное количество баров
        
        # Загружаем настройку темы
        dark_theme = self.settings.value("dark_theme", True, type=bool)
        self.dark_theme_checkbox.setChecked(dark_theme)
        self.apply_theme(dark_theme)
        
        # Загружаем настройку скачивания облачных файлов
        download_cloud = self.settings.value("download_cloud", True, type=bool)
        self.download_cloud_checkbox.setChecked(download_cloud)
        
    def save_settings(self):
        """Сохраняет текущие настройки"""
        self.settings.setValue("download_dir", self.download_dir_input.text())
        self.settings.setValue("post_limit", self.post_limit_input.value())
        self.settings.setValue("threads_count", self.threads_count_input.value())
        self.settings.setValue("dark_theme", self.dark_theme_checkbox.isChecked())
        self.settings.setValue("download_cloud", self.download_cloud_checkbox.isChecked())
    
    # ========== МЕТОДЫ ОЧЕРЕДИ АВТОРОВ ==========
    
    # ========== СТАРЫЕ НЕИСПОЛЬЗУЕМЫЕ МЕТОДЫ (закомментированы) ==========
    # def add_author_to_queue(self): ...
    # def add_all_and_start(self): ...
    
    def remove_author_from_queue(self):
        """Удаляет выбранного автора из очереди"""
        selected_items = self.queue_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Предупреждение", "Выберите автора для удаления!")
            return
        
        # Получаем индекс выбранного элемента
        row = self.queue_list.row(selected_items[0])
        
        reply = QMessageBox.question(
            self, 
            "Подтверждение", 
            "Удалить выбранного автора из очереди?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success, message = self.queue_manager.remove_author(row)
            if success:
                self.log_text.append(f"🗑️ {message}")
                self.update_queue_display()
            else:
                QMessageBox.warning(self, "Ошибка", message)
    
    def clear_queue(self):
        """Очищает всю очередь"""
        if not self.queue_manager.authors_queue:
            QMessageBox.information(self, "Информация", "Очередь уже пуста!")
            return
        
        reply = QMessageBox.question(
            self, 
            "Подтверждение", 
            "Очистить всю очередь авторов?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.queue_manager.clear_queue()
            self.log_text.append("🧹 Очередь очищена")
            self.update_queue_display()
    
    def auto_process_and_download(self):
        """🎯 АВТОМАТИЧЕСКИ обрабатывает URL авторов и запускает скачивание"""
        urls_text = self.url_input.toPlainText().strip()
        
        if not urls_text:
            QMessageBox.warning(self, "Предупреждение", "Введите URL авторов!")
            return
        
        # Разбиваем текст построчно и очищаем
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        
        if not urls:
            QMessageBox.warning(self, "Предупреждение", "Введите корректные URL авторов!")
            return
        
        self.log_text.append(f"🎯 Автоматическая обработка {len(urls)} авторов...")
        
        # Очищаем старую очередь
        self.queue_manager.clear_queue()
        
        # Добавляем всех авторов
        added_count = 0
        for url in urls:
            success, message = self.queue_manager.add_author(url)
            if success:
                added_count += 1
            else:
                self.log_text.append(f"⚠️ {message}")
        
        if added_count == 0:
            QMessageBox.warning(self, "Ошибка", "Не удалось добавить ни одного автора!")
            return
        
        # Обновляем отображение
        self.update_queue_display()
        self.url_input.clear()  # Очищаем поле
        
        self.log_text.append(f"✅ Добавлено {added_count} авторов. Запуск скачивания...")
        
        # Сразу запускаем скачивание
        self.start_download_worker()
        
        # Обновляем интерфейс
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.statusBar().showMessage("Автоматическое скачивание...")
        
        # Сбрасываем прогресс-бары
        self.reset_progress_bars()

    def start_queue_download(self):
        """Запускает скачивание очереди авторов"""
        if not self.queue_manager.authors_queue:
            QMessageBox.warning(self, "Предупреждение", "Очередь авторов пуста!")
            return
        
        if not self.queue_manager.has_pending_authors():
            reply = QMessageBox.question(
                self,
                "Повтор очереди",
                "Все авторы уже обработаны. Запустить очередь заново?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.queue_manager.reset_queue()
            else:
                return
        
        # Запускаем рабочий поток
        self.start_download_worker()
        
        # Обновляем интерфейс
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.statusBar().showMessage("Скачивание очереди...")
        self.log_text.clear()
        
        # Сбрасываем прогресс-бары
        self.reset_progress_bars()
    
    # ========== СТАРЫЕ МЕТОДЫ ОБРАБОТКИ КНОПОК (закомментированы) ==========
    # def on_queue_selection_changed(self): ...
    
    def update_queue_display(self):
        """Обновляет отображение очереди"""
        # Очищаем список
        self.queue_list.clear()
        
        # Добавляем авторов в список
        for i, author in enumerate(self.queue_manager.authors_queue):
            status_icon = {
                'pending': '⏳',
                'downloading': '📥', 
                'completed': '✅',
                'error': '❌'
            }.get(author['status'], '❓')
            
            display_name = f"{status_icon} {author['name']}"
            item = QListWidgetItem(display_name)
            
            # Устанавливаем цвет в зависимости от статуса
            if author['status'] == 'completed':
                item.setBackground(Qt.GlobalColor.darkGreen)
            elif author['status'] == 'error':
                item.setBackground(Qt.GlobalColor.darkRed)
            elif author['status'] == 'downloading':
                item.setBackground(Qt.GlobalColor.darkBlue)
            
            # Добавляем URL в tooltip
            item.setToolTip(f"URL: {author['url']}\nСтатус: {author['status']}")
            
            self.queue_list.addItem(item)
        
        # Обновляем статус очереди
        queue_status = self.queue_manager.get_queue_status()
        if queue_status['total'] == 0:
            self.queue_status_label.setText("Очередь пуста")
        else:
            status_text = f"Всего: {queue_status['total']} | "
            status_text += f"Ожидают: {queue_status['pending']} | "
            status_text += f"Завершено: {queue_status['completed']}"
            if queue_status['error'] > 0:
                status_text += f" | Ошибки: {queue_status['error']}"
            self.queue_status_label.setText(status_text)
        
        # Обновляем прогресс очереди
        if queue_status['total'] > 0:
            progress_value = int((queue_status['completed'] / queue_status['total']) * 100)
            self.queue_progress.setValue(progress_value)
            self.queue_progress_label.setText(f"Очередь: {queue_status['completed']}/{queue_status['total']}")
        else:
            self.queue_progress.setValue(0)
            self.queue_progress_label.setText("Очередь: 0/0")
    
    def on_queue_progress_update(self, current_index, total_authors, current_author_name):
        """Обрабатывает обновление прогресса очереди"""
        self.queue_progress_label.setText(f"Очередь: {current_index + 1}/{total_authors}")
        progress_value = int(((current_index + 1) / total_authors) * 100) if total_authors > 0 else 0
        self.queue_progress.setValue(progress_value)
        
        # Обновляем отображение списка
        self.update_queue_display()
        
        # Обновляем лог
        self.log_text.append(f"📋 Обрабатываем автора {current_index + 1}/{total_authors}: {current_author_name}")
    
    def closeEvent(self, event):
        """Обрабатывает закрытие окна"""
        self.save_settings()
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, 
                "Подтверждение", 
                "Скачивание в процессе. Остановить и выйти?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                if self.worker:
                    self.worker.stop()
                    self.worker.wait()  # Ждем завершения потока
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
    
    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Выберите папку для загрузок")
        if directory:
            self.download_dir_input.setText(directory)
            self.save_settings()
    
    def toggle_theme(self):
        """Переключает тему"""
        dark_theme = self.dark_theme_checkbox.isChecked()
        self.apply_theme(dark_theme)
        self.save_settings()
    
    def apply_theme(self, dark_theme=True):
        """Применяет выбранную тему"""
        if dark_theme:
            self.apply_dark_theme()
        else:
            self.apply_light_theme()
    
    def apply_dark_theme(self):
        """Применяет темную тему"""
        QApplication.instance().setStyleSheet(self.get_dark_theme_style())
    
    def apply_light_theme(self):
        """Применяет светлую тему"""
        QApplication.instance().setStyleSheet(self.get_light_theme_style())
    
    def get_dark_theme_style(self):
        """Возвращает CSS для темной минималистичной темы"""
        return """
        /* Минималистичная темная тема - осветленная */
        QMainWindow {
            background-color: #2d2d2d;
            color: #ffffff;
        }
        
        QWidget {
            background-color: #2d2d2d;
            color: #ffffff;
        }
        
        /* Группы - минималистичный стиль без фона */
        QGroupBox {
            font-weight: 500;
            color: #ffffff;
            border: 1px solid #404040;
            border-radius: 4px;
            margin-top: 12px;
            padding-top: 16px;
            padding-bottom: 8px;
            background-color: transparent;
            font-size: 11px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 8px;
            padding: 2px 6px 2px 6px;
            color: #ffffff;
            background-color: #2d2d2d;
        }
        
        /* Поля ввода */
        QLineEdit {
            background-color: #404040;
            border: 2px solid #555555;
            border-radius: 6px;
            padding: 8px;
            color: #ffffff;
            font-size: 10pt;
        }
        QLineEdit:focus {
            border-color: #4fc3f7;
            background-color: #4a4a4a;
        }
        
        /* SpinBox - современный стиль для темной темы */
        QSpinBox, QDoubleSpinBox {
            border: 1px solid #555;
            border-radius: 8px;
            background-color: #2a2a2a;
            color: white;
            padding: 5px;
            font-size: 12px;
        }
        QSpinBox:focus, QDoubleSpinBox:focus {
            border-color: #4fc3f7;
            background-color: #3a3a3a;
        }
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
            border: none;
            background-color: #444;
            width: 16px;
            border-radius: 4px;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover,
        QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
            background-color: #555;
        }
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 4px solid #00aaff;
            width: 0px;
            height: 0px;
        }
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 4px solid #00aaff;
            width: 0px;
            height: 0px;
        }
        
        /* Чекбоксы */
        QCheckBox {
            color: #ffffff;
            font-size: 10pt;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
        }
        QCheckBox::indicator:unchecked {
            background-color: #404040;
            border: 2px solid #555555;
            border-radius: 3px;
        }
        QCheckBox::indicator:checked {
            background-color: #4fc3f7;
            border: 2px solid #4fc3f7;
            border-radius: 3px;
        }
        
        /* Кнопки */
        QPushButton {
            background-color: #404040;
            border: 2px solid #666666;
            border-radius: 6px;
            padding: 8px 15px;
            color: #ffffff;
            font-weight: bold;
            font-size: 10pt;
        }
        QPushButton:hover {
            background-color: #505050;
            border-color: #777777;
        }
        QPushButton:pressed {
            background-color: #353535;
        }
        QPushButton:disabled {
            background-color: #2a2a2a;
            color: #666666;
            border-color: #444444;
        }
        
        /* Прогресс бары - минималистичные */
        QProgressBar {
            border: 1px solid #505050;
            border-radius: 1px;
            background-color: #3a3a3a;
            text-align: center;
            color: #ffffff;
            font-size: 9px;
        }
        QProgressBar::chunk {
            background-color: #0078d4;
            border-radius: 0px;
        }
        
        /* Текстовые области - минималистичные с легким фоном */
        QTextEdit {
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid #404040;
            border-radius: 2px;
            color: #ffffff;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 10px;
            padding: 8px;
            margin: 2px;
            line-height: 1.3;
        }
        
        /* Labels - минималистичные */
        QLabel {
            color: #ffffff;
            font-size: 10px;
        }
        
        /* Статус бар - минималистичный */
        QStatusBar {
            background-color: #3a3a3a;
            color: #ffffff;
            border-top: 1px solid #404040;
            font-size: 9px;
        }
        
        /* Скроллбары - минималистичные */
        QScrollBar:vertical {
            background-color: #2a2a2a;
            width: 10px;
            border-radius: 0px;
        }
        QScrollBar::handle:vertical {
            background-color: #505050;
            border-radius: 0px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #606060;
        }
        
        /* Специальные стили для цветных кнопок - минималистичные */
        QPushButton[class="success"] {
            background-color: #107c10;
            border-color: #107c10;
        }
        QPushButton[class="success"]:hover {
            background-color: #0e6e0e;
        }
        
        QPushButton[class="danger"] {
            background-color: #d13438;
            border-color: #d13438;
        }
        QPushButton[class="danger"]:hover {
            background-color: #b92b2b;
        }
        
        QPushButton[class="primary"] {
            background-color: #0078d4;
            border-color: #0078d4;
        }
        QPushButton[class="primary"]:hover {
            background-color: #106ebe;
        }
        
        QPushButton[class="info"] {
            background-color: #0078d4;
            border-color: #0078d4;
        }
        QPushButton[class="info"]:hover {
            background-color: #106ebe;
        }
        """
    
    def get_light_theme_style(self):
        """Возвращает CSS для светлой минималистичной темы"""
        return """
        /* Минималистичная светлая тема */
        QMainWindow {
            background-color: #fafafa;
            color: #000000;
        }
        
        QWidget {
            background-color: #fafafa;
            color: #000000;
        }
        
        /* Группы - минималистичный стиль без фона */
        QGroupBox {
            font-weight: 500;
            color: #000000;
            border: 1px solid #d0d0d0;
            border-radius: 4px;
            margin-top: 12px;
            padding-top: 16px;
            padding-bottom: 8px;
            background-color: transparent;
            font-size: 11px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 8px;
            padding: 2px 6px 2px 6px;
            color: #000000;
            background-color: #fafafa;
        }
        
        /* Поля ввода - минималистичные с легким фоном */
        QLineEdit {
            background-color: rgba(0, 0, 0, 0.02);
            border: 1px solid #d0d0d0;
            border-radius: 2px;
            padding: 10px 12px;
            margin: 2px;
            color: #000000;
            font-size: 11px;
            min-height: 16px;
        }
        QLineEdit:focus {
            border-color: #0078d4;
            background-color: rgba(0, 0, 0, 0.04);
        }
        
        /* SpinBox - минималистичный светлый стиль */
        QSpinBox, QDoubleSpinBox {
            border: 1px solid #d0d0d0;
            border-radius: 2px;
            background-color: #ffffff;
            color: black;
            padding: 4px 6px;
            font-size: 10px;
        }
        QSpinBox:focus, QDoubleSpinBox:focus {
            border-color: #0078d4;
            background-color: #ffffff;
        }
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
            border: none;
            background-color: #e8e8e8;
            width: 14px;
            border-radius: 1px;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover,
        QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
            background-color: #d8d8d8;
        }
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
            image: none;
            border-left: 3px solid transparent;
            border-right: 3px solid transparent;
            border-bottom: 3px solid #000000;
            width: 0px;
            height: 0px;
        }
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
            image: none;
            border-left: 3px solid transparent;
            border-right: 3px solid transparent;
            border-top: 3px solid #000000;
            width: 0px;
            height: 0px;
        }
        
        /* Чекбоксы - минималистичные */
        QCheckBox {
            color: #000000;
            font-size: 10px;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
        }
        QCheckBox::indicator:unchecked {
            background-color: #ffffff;
            border: 1px solid #d0d0d0;
            border-radius: 2px;
        }
        QCheckBox::indicator:checked {
            background-color: #0078d4;
            border: 1px solid #0078d4;
            border-radius: 2px;
        }
        
        /* Кнопки - минималистичные */
        QPushButton {
            background-color: #ffffff;
            border: 1px solid #d0d0d0;
            border-radius: 2px;
            padding: 6px 12px;
            color: #000000;
            font-weight: 400;
            font-size: 10px;
        }
        QPushButton:hover {
            background-color: #f0f0f0;
            border-color: #c0c0c0;
        }
        QPushButton:pressed {
            background-color: #e8e8e8;
        }
        QPushButton:disabled {
            background-color: #f8f8f8;
            color: #999999;
            border-color: #e0e0e0;
        }
        
        /* Прогресс бары - минималистичные */
        QProgressBar {
            border: 1px solid #d0d0d0;
            border-radius: 1px;
            background-color: #f8f8f8;
            text-align: center;
            color: #000000;
            font-size: 9px;
        }
        QProgressBar::chunk {
            background-color: #0078d4;
            border-radius: 0px;
        }
        
        /* Текстовые области - минималистичные с легким фоном */
        QTextEdit {
            background-color: rgba(0, 0, 0, 0.01);
            border: 1px solid #d0d0d0;
            border-radius: 2px;
            color: #000000;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 10px;
            padding: 8px;
            margin: 2px;
            line-height: 1.3;
        }
        
        /* Labels - минималистичные */
        QLabel {
            color: #000000;
            font-size: 10px;
        }
        
        /* Статус бар - минималистичный */
        QStatusBar {
            background-color: #f0f0f0;
            color: #000000;
            border-top: 1px solid #d0d0d0;
            font-size: 9px;
        }
        
        /* Скроллбары - минималистичные */
        QScrollBar:vertical {
            background-color: #f8f8f8;
            width: 10px;
            border-radius: 0px;
        }
        QScrollBar::handle:vertical {
            background-color: #c0c0c0;
            border-radius: 0px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #a0a0a0;
        }
        
        /* Специальные стили для цветных кнопок - минималистичные */
        QPushButton[class="success"] {
            background-color: #107c10;
            border-color: #107c10;
            color: #ffffff;
        }
        QPushButton[class="success"]:hover {
            background-color: #0e6e0e;
        }
        
        QPushButton[class="danger"] {
            background-color: #d13438;
            border-color: #d13438;
            color: #ffffff;
        }
        QPushButton[class="danger"]:hover {
            background-color: #b92b2b;
        }
        
        QPushButton[class="primary"] {
            background-color: #0078d4;
            border-color: #0078d4;
            color: #ffffff;
        }
        QPushButton[class="primary"]:hover {
            background-color: #106ebe;
        }
        
        QPushButton[class="info"] {
            background-color: #0078d4;
            border-color: #0078d4;
            color: #ffffff;
        }
        QPushButton[class="info"]:hover {
            background-color: #106ebe;
        }
        """
    
    def open_download_folder(self):
        """Открывает папку с загрузками"""
        download_dir = self.download_dir_input.text()
        if os.path.exists(download_dir):
            import subprocess
            import platform
            
            if platform.system() == "Windows":
                os.startfile(download_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", download_dir])
            else:  # Linux
                subprocess.call(["xdg-open", download_dir])
        else:
            QMessageBox.warning(self, "Ошибка", "Папка загрузок не существует!")
    
    def show_download_status(self):
        """Показывает статус загрузки в текущей папке"""
        download_dir = self.download_dir_input.text()
        
        if not os.path.exists(download_dir):
            QMessageBox.warning(self, "Ошибка", "Папка загрузок не существует!")
            return
        
        # Ищем все подпапки с файлами прогресса
        status_info = []
        
        for root, dirs, files in os.walk(download_dir):
            if '.kemono_progress.json' in files:
                try:
                    progress_file = os.path.join(root, '.kemono_progress.json')
                    with open(progress_file, 'r', encoding='utf-8') as f:
                        progress_data = json.load(f)
                    
                    relative_path = os.path.relpath(root, download_dir)
                    completed_posts = len(progress_data.get('completed_posts', []))
                    completed_files = len(progress_data.get('completed_files', {}))
                    started_at = progress_data.get('started_at', 'Неизвестно')
                    
                    # Подсчитываем общий размер скачанных файлов
                    total_size = 0
                    for file_info in progress_data.get('completed_files', {}).values():
                        total_size += file_info.get('size', 0)
                    
                    size_mb = total_size / (1024 * 1024)
                    
                    status_info.append({
                        'path': relative_path,
                        'posts': completed_posts,
                        'files': completed_files,
                        'size_mb': size_mb,
                        'started': started_at[:19] if started_at != 'Неизвестно' else started_at
                    })
                except Exception as e:
                    continue
        
        if not status_info:
            QMessageBox.information(self, "Статус", "В папке загрузок не найдено активных или завершенных загрузок.")
            return
        
        # Формируем сообщение со статусом
        message = "📊 СТАТУС ЗАГРУЗОК\n" + "="*50 + "\n\n"
        
        for info in status_info:
            message += f"📁 {info['path']}\n"
            message += f"   📄 Постов: {info['posts']}\n"
            message += f"   📁 Файлов: {info['files']}\n"
            message += f"   💾 Размер: {info['size_mb']:.1f} MB\n"
            message += f"   📅 Начато: {info['started']}\n\n"
        
        # Показываем в диалоге
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("📊 Статус загрузок")
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
    
    def show_supported_formats(self):
        """Показывает список поддерживаемых форматов файлов"""
        message = """🎯 УНИВЕРСАЛЬНЫЙ ПОИСК ВСЕХ ФАЙЛОВ
        
🎭 3D МОДЕЛИ И BLENDER:
• GLB, GLTF - 3D модели для веб и игр
• BLEND - файлы Blender
• FBX, OBJ, DAE - универсальные 3D форматы
• 3DS, MAX, MA, MB - форматы 3D пакетов

🎬 ВИДЕО:
• MP4, MOV, AVI, MKV, WEBM
• FLV, WMV, M4V, MPG, MPEG

🖼️ ИЗОБРАЖЕНИЯ:
• PNG, JPG, JPEG, GIF, BMP
• TIFF, TGA, PSD, WEBP, SVG

📦 АРХИВЫ:
• ZIP, RAR, 7Z, TAR, GZ, BZ2, XZ

📄 ДОКУМЕНТЫ:
• PDF, DOC, DOCX, TXT, RTF

🎵 АУДИО:
• MP3, WAV, FLAC, OGG, M4A, AAC

🎮 UNITY И ИГРЫ:
• UNITY, UNITYPACKAGE, PREFAB, ASSET

🎨 ТЕКСТУРЫ И МАТЕРИАЛЫ:
• DDS, HDR, EXR, MAT

📱 ПРИЛОЖЕНИЯ:
• EXE, MSI, DMG, APK, IPA

☁️ ОБЛАЧНЫЕ ССЫЛКИ:
• Google Drive, MEGA, Dropbox
• OneDrive, MediaFire, WeTransfer
• pCloud, Yandex Disk, Box, iCloud
• Ссылки сохраняются в cloud_links.txt

✨ Программа автоматически найдет ВСЕ файлы и ссылки в постах!"""
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("📋 Поддерживаемые форматы файлов")
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
    
    def start_download_worker(self):
        """Запускает рабочий поток для обработки очереди авторов"""
        # Создаем папку загрузок если не существует
        download_dir = self.download_dir_input.text()
        os.makedirs(download_dir, exist_ok=True)
        
        # Настройки
        settings = {
            'download_dir': download_dir,
            'post_limit': self.post_limit_input.value() if self.post_limit_input.value() > 0 else None,
            'threads_count': self.threads_count_input.value(),
            'download_cloud': self.download_cloud_checkbox.isChecked()
        }
        
        # Запускаем рабочий поток (всегда с очередью)
        self.worker = DownloaderWorker(settings, self.queue_manager)
        
        # Подключаем сигналы
        self.worker.progress.connect(self.update_post_progress)
        self.worker.log.connect(self.add_log)
        self.worker.finished.connect(self.download_finished)
        self.worker.thread_progress.connect(self.update_thread_progress)
        self.worker.overall_progress.connect(self.update_overall_progress)
        self.worker.queue_progress.connect(self.on_queue_progress_update)
        
        self.worker.start()
        
        # Обновляем интерфейс
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.statusBar().showMessage("Скачивание...")
        self.log_text.clear()
        
        # ИСПРАВЛЕНО: Сбрасываем все прогресс-бары при старте
        self.post_progress.setValue(0)
        self.post_progress.setMaximum(1)
        self.post_progress_label.setText("Посты: 0/0")
        
        self.overall_progress.setValue(0)
        self.overall_progress.setMaximum(1)
        self.overall_progress_label.setText("Файлы: 0/0")
        
        # Сбрасываем прогресс-бары потоков
        for i, progress_bar in enumerate(self.thread_progress_bars):
            progress_bar.setValue(0)
            progress_bar.setMaximum(100)
            progress_bar.setToolTip("")
    
    def reset_progress_bars(self):
        """Сбрасывает все прогресс-бары"""
        # Основные прогрессы
        self.post_progress.setValue(0)
        self.post_progress.setMaximum(1)
        self.post_progress_label.setText("Посты: 0/0")
        
        self.overall_progress.setValue(0)
        self.overall_progress.setMaximum(1)
        self.overall_progress_label.setText("Файлы: 0/0")
        
        # Прогресс очереди 
        self.queue_progress.setValue(0)
        self.queue_progress_label.setText("Очередь: 0/0")
        
        # Прогресс-бары потоков
        for i, progress_bar in enumerate(self.thread_progress_bars):
            progress_bar.setValue(0)
            progress_bar.setMaximum(100)
            progress_bar.setToolTip("")
        
    def stop_download(self):
        if self.worker:
            self.worker.stop()
            self.add_log("⏹️ Остановка...")
            
    def update_post_progress(self, current, total):
        self.post_progress.setMaximum(total)
        self.post_progress.setValue(current)
        self.post_progress_label.setText(f"Посты: {current} / {total}")
    
    def update_thread_progress(self, thread_id, filename, progress, max_progress):
        """Обновляет прогресс конкретного потока (столбики всегда видны)"""
        if 0 <= thread_id < len(self.thread_progress_bars):            
            if max_progress > 0:
                self.thread_progress_bars[thread_id].setMaximum(max_progress)
                self.thread_progress_bars[thread_id].setValue(progress)
            else:
                self.thread_progress_bars[thread_id].setMaximum(1)
                self.thread_progress_bars[thread_id].setValue(1)
            
            # Tooltip с номером потока и информацией о файле
            short_filename = filename[:25] + "..." if len(filename) > 25 else filename
            tooltip_text = f"Поток #{thread_id+1}\n{filename}\nПрогресс: {progress}%"
            self.thread_progress_bars[thread_id].setToolTip(tooltip_text)
            
            # Обновляем скрытый label для данных
            self.thread_labels[thread_id].setText(short_filename)
    
    def update_overall_progress(self, current, total):
        """Обновляет общий прогресс скачивания файлов"""
        if total > 0:
            self.overall_progress.setMaximum(total)
            self.overall_progress.setValue(current)
        else:
            self.overall_progress.setMaximum(1)
            self.overall_progress.setValue(1)
        
        self.overall_progress_label.setText(f"Файлы: {current} / {total}")
        
        # Принудительно обновляем до 100% если все файлы скачаны
        if current >= total and total > 0:
            self.overall_progress.setValue(total)  # Убеждаемся что показывает 100%

    def add_log(self, message):
        # Показываем ошибки, важные сообщения, прогресс анализа постов и прогресс скачивания
        show_keywords = [
            'ошибка', 'error', '❌', '✅ завершено', '✅', '🎯', '📋', '🎉',
            '📄', 'анализируем пост', 'analyzing post',
            '📥', '⬇️', 'скачано файлов', 'уже скачано файлов', 'files downloaded', 'завершено',
            '🚀', 'начинаем скачивание', 'начинаем', 'шаг 1', 'шаг 2', '🔍'
        ]
        if any(keyword in message.lower() for keyword in show_keywords):
            self.log_text.append(message)
            # Автоскролл вниз
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        
    def download_finished(self, files_count):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.add_and_start_btn.setEnabled(True)
        
        # Принудительно завершаем общий прогресс на 100%
        if self.overall_progress.maximum() > 0:
            self.overall_progress.setValue(self.overall_progress.maximum())
        
        # Сбрасываем прогресс-бары потоков (оставляем видимыми)
        for i, progress_bar in enumerate(self.thread_progress_bars):
            progress_bar.setValue(0)
            progress_bar.setToolTip("")  # Очищаем tooltip
            self.thread_labels[i].setText("Ожидание...")
        
        # Обновляем очередь если была в режиме очереди
        if self.worker and self.worker.is_queue_mode:
            self.update_queue_display()
            
            # Завершаем прогресс очереди
            queue_status = self.queue_manager.get_queue_status()
            self.queue_progress.setValue(100)
            self.queue_progress_label.setText(f"Очередь завершена: {queue_status['completed']}/{queue_status['total']}")
        
        if files_count > 0:
            # Определяем сообщение в зависимости от режима
            if self.worker and self.worker.is_queue_mode:
                queue_status = self.queue_manager.get_queue_status()
                message = f"Очередь авторов завершена!\n"
                message += f"Обработано авторов: {queue_status['completed']}/{queue_status['total']}\n"
                message += f"Всего скачано файлов: {files_count}\n\nОткрыть папку загрузок?"
                title = "Очередь завершена"
            else:
                message = f"Скачивание завершено!\nСкачано файлов: {files_count}\n\nОткрыть папку с файлами?"
                title = "Успех"
            
            self.statusBar().showMessage(f"Завершено! Скачано {files_count} файлов")
            
            # Показываем диалог с возможностью открыть папку
            reply = QMessageBox.question(
                self, 
                title, 
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.open_download_folder()
        else:
            self.statusBar().showMessage("Скачивание остановлено")
            
        self.worker = None

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("KemonoDownloader GUI v2.8.5 Progress")
    
    # Создаем окно (тема будет применена в load_settings)
    window = KemonoDownloaderGUI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()