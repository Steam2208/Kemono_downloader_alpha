#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KemonoDownloader GUI v2.3 - Images Fixed - Версия без fake-useragent для exe
Улучшения v2.3:
- Исправлена работа с MP4 и видео файлами
- Автопоиск файлов на разных доменах (n1-n6.kemono.cr)
- HTML fallback при проблемах с API
- Улучшенный поиск медиа во всех секциях
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
from downloader_static import get_creator_posts, get_post_media, download_file
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DownloaderWorker(QThread):
    """Рабочий поток для скачивания"""
    progress = pyqtSignal(int, int)  # текущий, всего
    log = pyqtSignal(str)
    finished = pyqtSignal(int)  # количество скачанных файлов
    batch_progress = pyqtSignal(int, int)  # текущая пачка, всего пачек
    
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
            
            # Пачковая загрузка
            batch_size = self.settings['batch_size']
            batch_pause = self.settings['batch_pause']
            total_batches = (len(posts) + batch_size - 1) // batch_size
            total_downloaded = 0
            
            self.log.emit(f"📦 Пачек: {total_batches} по {batch_size} постов")
            
            for batch_num in range(total_batches):
                if not self.running:
                    break
                    
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(posts))
                batch_posts = posts[start_idx:end_idx]
                
                self.batch_progress.emit(batch_num + 1, total_batches)
                self.log.emit(f"\n📦 ПАЧКА {batch_num + 1}/{total_batches} (посты {start_idx + 1}-{end_idx})")
                
                batch_downloaded = 0
                
                for i, post_url in enumerate(batch_posts):
                    if not self.running:
                        break
                        
                    global_idx = start_idx + i
                    self.progress.emit(global_idx, len(posts))
                    
                    try:
                        # Используем рабочий метод получения медиа
                        media_links = get_post_media(post_url, enhanced_search=True)
                        
                        if media_links:
                            self.log.emit(f"  📄 [{global_idx + 1}/{len(posts)}] Найдено {len(media_links)} файлов")
                            
                            for j, link in enumerate(media_links):
                                if not self.running:
                                    break
                                    
                                # Получаем имя файла
                                if '?f=' in link:
                                    filename = link.split('?f=')[-1]
                                else:
                                    filename = link.split('/')[-1].split('?')[0]
                                
                                # Скачиваем файл прямо в папку автора
                                success = download_file(link, save_dir)
                                if success:
                                    total_downloaded += 1
                                    batch_downloaded += 1
                                    self.log.emit(f"    ✅ {filename}")
                                else:
                                    self.log.emit(f"    ❌ Ошибка: {filename}")
                                
                                time.sleep(0.1)  # Небольшая пауза между файлами
                        else:
                            self.log.emit(f"  📄 [{global_idx + 1}/{len(posts)}] Медиа не найдено")
                            
                    except Exception as e:
                        self.log.emit(f"  ❌ Ошибка поста {global_idx + 1}: {e}")
                
                self.log.emit(f"✅ Пачка {batch_num + 1} завершена: {batch_downloaded} файлов")
                
                # Пауза между пачками
                if batch_num < total_batches - 1 and self.running:
                    self.log.emit(f"⏸️ Пауза {batch_pause}с...")
                    time.sleep(batch_pause)
            
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
        self.setWindowTitle("🦊 KemonoDownloader GUI v2.3 - Images Fixed")
        self.setGeometry(100, 100, 800, 700)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Заголовок
        title = QLabel("🦊 KemonoDownloader GUI v2.3 - Images Fixed")
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
        
        # Размер пачки
        settings_layout.addWidget(QLabel("📦 Размер пачки:"), 1, 0)
        self.batch_size_input = QSpinBox()
        self.batch_size_input.setRange(1, 50)
        self.batch_size_input.setValue(5)
        self.batch_size_input.valueChanged.connect(self.save_settings)
        settings_layout.addWidget(self.batch_size_input, 1, 1)
        
        # Пауза между пачками
        settings_layout.addWidget(QLabel("⏱️ Пауза между пачками (сек):"), 2, 0)
        self.batch_pause_input = QDoubleSpinBox()
        self.batch_pause_input.setRange(0.1, 60.0)
        self.batch_pause_input.setValue(2.0)
        self.batch_pause_input.setSingleStep(0.5)
        self.batch_pause_input.valueChanged.connect(self.save_settings)
        settings_layout.addWidget(self.batch_pause_input, 2, 1)
        
        # Лимит постов
        settings_layout.addWidget(QLabel("🎯 Лимит постов (0 = все):"), 3, 0)
        self.post_limit_input = QSpinBox()
        self.post_limit_input.setRange(0, 10000)
        self.post_limit_input.setValue(0)
        self.post_limit_input.setSpecialValueText("Все посты")
        self.post_limit_input.valueChanged.connect(self.save_settings)
        settings_layout.addWidget(self.post_limit_input, 3, 1)
        
        # Темная тема
        settings_layout.addWidget(QLabel("🌙 Темная тема:"), 4, 0)
        self.dark_theme_checkbox = QCheckBox("Включено")
        self.dark_theme_checkbox.setChecked(True)  # По умолчанию темная
        self.dark_theme_checkbox.stateChanged.connect(self.toggle_theme)
        settings_layout.addWidget(self.dark_theme_checkbox, 4, 1)
        
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
        
        layout.addLayout(buttons_layout)
        
        # Прогресс
        progress_group = QGroupBox("📊 Прогресс")
        progress_layout = QVBoxLayout(progress_group)
        
        # Прогресс постов
        self.post_progress_label = QLabel("Посты: 0 / 0")
        progress_layout.addWidget(self.post_progress_label)
        
        self.post_progress = QProgressBar()
        progress_layout.addWidget(self.post_progress)
        
        # Прогресс пачек
        self.batch_progress_label = QLabel("Пачки: 0 / 0")
        progress_layout.addWidget(self.batch_progress_label)
        
        self.batch_progress = QProgressBar()
        progress_layout.addWidget(self.batch_progress)
        
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
        self.batch_size_input.setValue(
            int(self.settings.value("batch_size", 5))
        )
        self.batch_pause_input.setValue(
            float(self.settings.value("batch_pause", 2.0))
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
        self.settings.setValue("batch_size", self.batch_size_input.value())
        self.settings.setValue("batch_pause", self.batch_pause_input.value())
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
            'batch_size': self.batch_size_input.value(),
            'batch_pause': self.batch_pause_input.value(),
            'post_limit': self.post_limit_input.value() if self.post_limit_input.value() > 0 else None
        }
        
        # Запускаем рабочий поток
        self.worker = DownloaderWorker(url, settings)
        self.worker.progress.connect(self.update_post_progress)
        self.worker.batch_progress.connect(self.update_batch_progress)
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
        
    def update_batch_progress(self, current, total):
        self.batch_progress.setMaximum(total)
        self.batch_progress.setValue(current)
        self.batch_progress_label.setText(f"Пачки: {current} / {total}")
        
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
    app.setApplicationName("KemonoDownloader GUI v2.3 - Images Fixed")
    
    # Создаем окно (тема будет применена в load_settings)
    window = KemonoDownloaderGUI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()