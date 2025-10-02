#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KemonoDownloader GUI v2.7 Multithread - Универсальный поиск + многопоточное скачивание
Новое в v2.7:
- МНОГОПОТОЧНОЕ СКАЧИВАНИЕ! До 3х потоков одновременно
- АВТОМАТИЧЕСКОЕ СКАЧИВАНИЕ ИЗ ОБЛАЧНЫХ ХРАНИЛИЩ!
- УНИВЕРСАЛЬНЫЙ поиск ВСЕХ типов файлов (61 формат)
- Поддержка Google Drive, MEGA, Dropbox, MediaFire
- Поддержка 3D моделей: GLB, GLTF, BLEND, FBX, OBJ
- Расширенный поиск архивов, документов, аудио
- Unity ресурсы: UNITY, UNITYPACKAGE, PREFAB
- Текстуры и материалы: DDS, HDR, EXR, MAT
- Облачные файлы сохраняются в ту же папку, что и медиа
- Значительно увеличена скорость скачивания
"""

import sys
import os
import time
import threading
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, 
                           QProgressBar, QSpinBox, QDoubleSpinBox, QCheckBox,
                           QFileDialog, QGroupBox, QGridLayout, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QSettings
from PyQt6.QtGui import QFont, QIcon

# Импорт нашего улучшенного движка без fake-useragent (с автопоиском доменов)
sys.path.append(os.path.dirname(__file__))
from downloader_static import (get_creator_posts, get_post_media, download_file, 
                              load_download_progress, save_download_progress, 
                              download_creator_posts, show_download_status,
                              detect_cloud_links, download_cloud_files)
import requests
import urllib3
import hashlib
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DownloaderWorker(QThread):
    """Рабочий поток для скачивания"""
    progress = pyqtSignal(int, int)  # текущий, всего
    log = pyqtSignal(str)
    finished = pyqtSignal(int)  # количество скачанных файлов
    
    def __init__(self, creator_url, settings):
        super().__init__()
        self.creator_url = creator_url
        self.settings = settings
        self.running = True
        
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
            self.log.emit("🚀 Начинаем скачивание...")
            
            # Извлекаем информацию об авторе
            service, creator_id = self.extract_creator_info(self.creator_url)
            if not service or not creator_id:
                self.log.emit("❌ Неверный формат URL!")
                self.finished.emit(0)
                return
            
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
            all_posts = get_creator_posts(self.creator_url)
            
            if not all_posts:
                self.log.emit("❌ Посты не найдены!")
                self.finished.emit(0)
                return
            
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
                self.finished.emit(completed_files)
                return
            
            self.log.emit(f"📋 К обработке: {len(pending_posts)} новых постов (из {len(posts)} общих)")
            
            # Многопоточная обработка постов
            total_downloaded = len(progress_data.get('completed_files', {}))  # Уже скачанные файлы
            
            self.log.emit(f"� Начинаем многопоточную обработку {len(pending_posts)} постов")
            
            for i, post_url in enumerate(pending_posts):
                if not self.running:
                    break
                    
                self.progress.emit(i, len(pending_posts))
                    
                try:
                    # Создаем ID поста для отслеживания
                    post_id = hashlib.md5(post_url.encode()).hexdigest()
                    
                    self.log.emit(f"📄 [{i + 1}/{len(pending_posts)}] Обрабатываем пост...")
                    
                    # Используем рабочий метод получения медиа
                    media_links = get_post_media(post_url, enhanced_search=True, save_dir=save_dir)
                    
                    if media_links:
                        self.log.emit(f"   Найдено {len(media_links)} файлов")
                        
                        post_files_downloaded = 0
                        for j, link in enumerate(media_links):
                            if not self.running:
                                break
                                
                            # Получаем имя файла
                            if '?f=' in link:
                                filename = link.split('?f=')[-1]
                            else:
                                filename = link.split('/')[-1].split('?')[0]
                            
                            # Скачиваем файл с поддержкой прогресса
                            success = download_file(link, save_dir, progress_data)
                            if success:
                                total_downloaded += 1
                                post_files_downloaded += 1
                                self.log.emit(f"   ✅ {filename}")
                            else:
                                self.log.emit(f"   ❌ Ошибка: {filename}")
                            
                            time.sleep(0.1)  # Небольшая пауза между файлами
                        
                        # Облачные файлы уже обрабатываются в get_post_media
                        
                        # Отмечаем пост как завершенный
                        if 'completed_posts' not in progress_data:
                            progress_data['completed_posts'] = []
                        
                        progress_data['completed_posts'].append(post_id)
                        save_download_progress(save_dir, progress_data)
                        
                        self.log.emit(f"   📄 Пост завершен: {post_files_downloaded} файлов")
                    else:
                        self.log.emit(f"   ⚠️ Медиа не найдено")
                        # Все равно отмечаем как обработанный
                        if 'completed_posts' not in progress_data:
                            progress_data['completed_posts'] = []
                        progress_data['completed_posts'].append(post_id)
                        save_download_progress(save_dir, progress_data)
                        
                except Exception as e:
                    self.log.emit(f"❌ Ошибка поста {i + 1}: {e}")
            
            if self.running:
                self.log.emit(f"\n🎉 ЗАВЕРШЕНО! Скачано {total_downloaded} файлов")
                self.log.emit(f"📁 Все файлы в: {save_dir}")
            else:
                self.log.emit(f"\n⏹️ ОСТАНОВЛЕНО. Скачано {total_downloaded} файлов")
            
            self.finished.emit(total_downloaded)
            
        except Exception as e:
            self.log.emit(f"❌ Критическая ошибка: {e}")
            self.finished.emit(0)

class KemonoDownloaderGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.settings = QSettings("KemonoDownloader", "GUI")
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        self.setWindowTitle("🦊 KemonoDownloader GUI v2.7 Multithread")
        self.setGeometry(100, 100, 800, 700)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Заголовок
        title = QLabel("🦊 KemonoDownloader GUI v2.7 Multithread")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("QLabel { color: #4fc3f7; padding: 15px; }")
        layout.addWidget(title)
        
        # Группа настроек URL
        url_group = QGroupBox("📝 URL автора")
        url_layout = QVBoxLayout(url_group)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://kemono.cr/patreon/user/12345678")
        url_layout.addWidget(self.url_input)
        
        layout.addWidget(url_group)
        
        # Группа настроек скачивания
        settings_group = QGroupBox("⚙️ Настройки")
        settings_layout = QGridLayout(settings_group)
        
        # Папка загрузок
        settings_layout.addWidget(QLabel("📁 Папка загрузок:"), 0, 0)
        self.download_dir_input = QLineEdit()
        self.download_dir_input.setText(os.path.join(os.getcwd(), "downloads"))
        settings_layout.addWidget(self.download_dir_input, 0, 1)
        
        self.browse_btn = QPushButton("📂 Обзор")
        self.browse_btn.clicked.connect(self.browse_directory)
        settings_layout.addWidget(self.browse_btn, 0, 2)
        
        # Лимит постов
        settings_layout.addWidget(QLabel("🎯 Лимит постов (0 = все):"), 1, 0)
        self.post_limit_input = QSpinBox()
        self.post_limit_input.setRange(0, 10000)
        self.post_limit_input.setValue(0)
        self.post_limit_input.setSpecialValueText("Все посты")
        self.post_limit_input.valueChanged.connect(self.save_settings)
        settings_layout.addWidget(self.post_limit_input, 1, 1)
        
        # Темная тема
        settings_layout.addWidget(QLabel("🌙 Темная тема:"), 2, 0)
        self.dark_theme_checkbox = QCheckBox("Включено")
        self.dark_theme_checkbox.setChecked(True)  # По умолчанию темная
        self.dark_theme_checkbox.stateChanged.connect(self.toggle_theme)
        settings_layout.addWidget(self.dark_theme_checkbox, 2, 1)
        
        layout.addWidget(settings_group)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 Начать скачивание")
        self.start_btn.clicked.connect(self.start_download)
        self.start_btn.setProperty("class", "success")
        buttons_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Остановить")
        self.stop_btn.clicked.connect(self.stop_download)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setProperty("class", "danger")
        buttons_layout.addWidget(self.stop_btn)
        
        self.open_folder_btn = QPushButton("📂 Открыть папку")
        self.open_folder_btn.clicked.connect(self.open_download_folder)
        self.open_folder_btn.setProperty("class", "primary")
        buttons_layout.addWidget(self.open_folder_btn)
        
        self.status_btn = QPushButton("📊 Статус загрузки")
        self.status_btn.clicked.connect(self.show_download_status)
        self.status_btn.setProperty("class", "info")
        buttons_layout.addWidget(self.status_btn)
        
        self.formats_btn = QPushButton("📋 Форматы файлов")
        self.formats_btn.clicked.connect(self.show_supported_formats)
        self.formats_btn.setProperty("class", "primary")
        buttons_layout.addWidget(self.formats_btn)
        
        layout.addLayout(buttons_layout)
        
        # Прогресс
        progress_group = QGroupBox("📊 Прогресс")
        progress_layout = QVBoxLayout(progress_group)
        
        # Прогресс постов
        self.post_progress_label = QLabel("Посты: 0 / 0")
        progress_layout.addWidget(self.post_progress_label)
        
        self.post_progress = QProgressBar()
        progress_layout.addWidget(self.post_progress)
        
        layout.addWidget(progress_group)
        
        # Лог
        log_group = QGroupBox("📋 Лог скачивания")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(250)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        # Статус бар
        self.statusBar().showMessage("Готов к работе")
    
    def load_settings(self):
        """Загружает сохраненные настройки"""
        self.download_dir_input.setText(
            self.settings.value("download_dir", os.path.join(os.getcwd(), "downloads"))
        )
        self.post_limit_input.setValue(
            int(self.settings.value("post_limit", 0))
        )
        
        # Загружаем настройку темы
        dark_theme = self.settings.value("dark_theme", True, type=bool)
        self.dark_theme_checkbox.setChecked(dark_theme)
        self.apply_theme(dark_theme)
        
    def save_settings(self):
        """Сохраняет текущие настройки"""
        self.settings.setValue("download_dir", self.download_dir_input.text())
        self.settings.setValue("post_limit", self.post_limit_input.value())
        self.settings.setValue("dark_theme", self.dark_theme_checkbox.isChecked())
    
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
        """Возвращает CSS для темной темы"""
        return """
        /* Основная темная тема */
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        
        /* Группы */
        QGroupBox {
            font-weight: bold;
            color: #ffffff;
            border: 2px solid #555555;
            border-radius: 8px;
            margin-top: 1ex;
            padding-top: 12px;
            background-color: #3a3a3a;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
            color: #4fc3f7;
        }
        
        /* Поля ввода */
        QLineEdit, QSpinBox, QDoubleSpinBox {
            background-color: #404040;
            border: 2px solid #555555;
            border-radius: 6px;
            padding: 8px;
            color: #ffffff;
            font-size: 10pt;
        }
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
            border-color: #4fc3f7;
            background-color: #4a4a4a;
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
        
        /* Прогресс бары */
        QProgressBar {
            background-color: #404040;
            border: 2px solid #555555;
            border-radius: 6px;
            text-align: center;
            color: #ffffff;
            font-weight: bold;
        }
        QProgressBar::chunk {
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4fc3f7, stop:1 #29b6f6);
            border-radius: 4px;
        }
        
        /* Текстовые области */
        QTextEdit {
            background-color: #1e1e1e;
            border: 2px solid #555555;
            border-radius: 6px;
            color: #ffffff;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 9pt;
            padding: 5px;
        }
        
        /* Labels */
        QLabel {
            color: #ffffff;
            font-size: 10pt;
        }
        
        /* Статус бар */
        QStatusBar {
            background-color: #3a3a3a;
            color: #ffffff;
            border-top: 1px solid #555555;
        }
        
        /* Скроллбары */
        QScrollBar:vertical {
            background-color: #404040;
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background-color: #666666;
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #777777;
        }
        
        /* Специальные стили для цветных кнопок */
        QPushButton[class="success"] {
            background-color: #2e7d32;
            border-color: #4caf50;
        }
        QPushButton[class="success"]:hover {
            background-color: #388e3c;
        }
        
        QPushButton[class="danger"] {
            background-color: #c62828;
            border-color: #f44336;
        }
        QPushButton[class="danger"]:hover {
            background-color: #d32f2f;
        }
        
        QPushButton[class="primary"] {
            background-color: #1565c0;
            border-color: #2196f3;
        }
        QPushButton[class="primary"]:hover {
            background-color: #1976d2;
        }
        
        QPushButton[class="info"] {
            background-color: #0288d1;
            border-color: #03a9f4;
        }
        QPushButton[class="info"]:hover {
            background-color: #0277bd;
        }
        """
    
    def get_light_theme_style(self):
        """Возвращает CSS для светлой темы"""
        return """
        /* Основная светлая тема */
        QMainWindow {
            background-color: #f5f5f5;
            color: #000000;
        }
        
        QWidget {
            background-color: #f5f5f5;
            color: #000000;
        }
        
        /* Группы */
        QGroupBox {
            font-weight: bold;
            color: #000000;
            border: 2px solid #cccccc;
            border-radius: 8px;
            margin-top: 1ex;
            padding-top: 12px;
            background-color: #ffffff;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
            color: #1976d2;
        }
        
        /* Поля ввода */
        QLineEdit, QSpinBox, QDoubleSpinBox {
            background-color: #ffffff;
            border: 2px solid #ddd;
            border-radius: 6px;
            padding: 8px;
            color: #000000;
            font-size: 10pt;
        }
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
            border-color: #1976d2;
            background-color: #f8f9fa;
        }
        
        /* Чекбоксы */
        QCheckBox {
            color: #000000;
            font-size: 10pt;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
        }
        QCheckBox::indicator:unchecked {
            background-color: #ffffff;
            border: 2px solid #ddd;
            border-radius: 3px;
        }
        QCheckBox::indicator:checked {
            background-color: #1976d2;
            border: 2px solid #1976d2;
            border-radius: 3px;
        }
        
        /* Кнопки */
        QPushButton {
            background-color: #ffffff;
            border: 2px solid #ddd;
            border-radius: 6px;
            padding: 8px 15px;
            color: #000000;
            font-weight: bold;
            font-size: 10pt;
        }
        QPushButton:hover {
            background-color: #f0f0f0;
            border-color: #bbb;
        }
        QPushButton:pressed {
            background-color: #e0e0e0;
        }
        QPushButton:disabled {
            background-color: #f5f5f5;
            color: #999999;
            border-color: #e0e0e0;
        }
        
        /* Прогресс бары */
        QProgressBar {
            background-color: #ffffff;
            border: 2px solid #ddd;
            border-radius: 6px;
            text-align: center;
            color: #000000;
            font-weight: bold;
        }
        QProgressBar::chunk {
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1976d2, stop:1 #42a5f5);
            border-radius: 4px;
        }
        
        /* Текстовые области */
        QTextEdit {
            background-color: #ffffff;
            border: 2px solid #ddd;
            border-radius: 6px;
            color: #000000;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 9pt;
            padding: 5px;
        }
        
        /* Labels */
        QLabel {
            color: #000000;
            font-size: 10pt;
        }
        
        /* Статус бар */
        QStatusBar {
            background-color: #ffffff;
            color: #000000;
            border-top: 1px solid #ddd;
        }
        
        /* Скроллбары */
        QScrollBar:vertical {
            background-color: #f0f0f0;
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background-color: #c0c0c0;
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #a0a0a0;
        }
        
        /* Специальные стили для цветных кнопок */
        QPushButton[class="success"] {
            background-color: #4caf50;
            border-color: #4caf50;
            color: #ffffff;
        }
        QPushButton[class="success"]:hover {
            background-color: #45a049;
        }
        
        QPushButton[class="danger"] {
            background-color: #f44336;
            border-color: #f44336;
            color: #ffffff;
        }
        QPushButton[class="danger"]:hover {
            background-color: #da190b;
        }
        
        QPushButton[class="primary"] {
            background-color: #2196f3;
            border-color: #2196f3;
            color: #ffffff;
        }
        QPushButton[class="primary"]:hover {
            background-color: #0b7dda;
        }
        
        QPushButton[class="info"] {
            background-color: #03a9f4;
            border-color: #03a9f4;
            color: #ffffff;
        }
        QPushButton[class="info"]:hover {
            background-color: #0288d1;
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
    
    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Ошибка", "Введите URL автора!")
            return
        
        # Создаем папку загрузок если не существует
        download_dir = self.download_dir_input.text()
        os.makedirs(download_dir, exist_ok=True)
        
        # Настройки
        settings = {
            'download_dir': download_dir,
            'post_limit': self.post_limit_input.value() if self.post_limit_input.value() > 0 else None
        }
        
        # Запускаем рабочий поток
        self.worker = DownloaderWorker(url, settings)
        self.worker.progress.connect(self.update_post_progress)
        self.worker.log.connect(self.add_log)
        self.worker.finished.connect(self.download_finished)
        
        self.worker.start()
        
        # Обновляем интерфейс
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.statusBar().showMessage("Скачивание...")
        self.log_text.clear()
        
    def stop_download(self):
        if self.worker:
            self.worker.stop()
            self.add_log("⏹️ Остановка...")
            
    def update_post_progress(self, current, total):
        self.post_progress.setMaximum(total)
        self.post_progress.setValue(current)
        self.post_progress_label.setText(f"Посты: {current} / {total}")
        

    def add_log(self, message):
        self.log_text.append(message)
        # Автоскролл вниз
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def download_finished(self, files_count):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if files_count > 0:
            self.statusBar().showMessage(f"Завершено! Скачано {files_count} файлов")
            # Показываем диалог с возможностью открыть папку
            reply = QMessageBox.question(
                self, 
                "Успех", 
                f"Скачивание завершено!\nСкачано файлов: {files_count}\n\nОткрыть папку с файлами?",
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
    app.setApplicationName("KemonoDownloader GUI v2.7 Multithread")
    
    # Создаем окно (тема будет применена в load_settings)
    window = KemonoDownloaderGUI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()