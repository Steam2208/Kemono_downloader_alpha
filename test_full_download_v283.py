#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 Полный тест скачивания v2.8.3
================================
Тестируем весь процесс скачивания на одном посте
"""

import sys
import os
import shutil

# Добавляем путь к нашим модулям
sys.path.append('.')

from downloader_static import get_post_media, download_files_parallel

def test_full_download():
    """Полный тест скачивания одного поста"""
    print("🧪 ПОЛНЫЙ ТЕСТ СКАЧИВАНИЯ v2.8.3")
    print("=" * 50)
    
    # Тестовый пост с изображением
    test_url = "https://kemono.cr/patreon/user/804602/post/91974242"
    test_dir = "test_download_v283"
    
    # Очищаем тестовую папку
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)
    
    print(f"🎯 Тестируем пост: {test_url}")
    print(f"📁 Папка для теста: {test_dir}")
    print()
    
    # Шаг 1: Получаем файлы
    print("🔍 Шаг 1: Получаем список файлов...")
    media_links = get_post_media(test_url, enhanced_search=True, save_dir=test_dir)
    
    if not media_links:
        print("❌ Файлы не найдены!")
        return False
    
    print(f"✅ Найдено файлов: {len(media_links)}")
    for i, link in enumerate(media_links, 1):
        filename = link.split('/')[-1].split('?')[0]
        print(f"   {i}. {filename}")
    
    print()
    
    # Шаг 2: Скачиваем файлы
    print("📥 Шаг 2: Скачиваем файлы...")
    downloaded_count = download_files_parallel(
        media_links, 
        test_dir, 
        progress_data=None,
        max_workers=2
    )
    
    print()
    print("📊 РЕЗУЛЬТАТ ТЕСТА:")
    print(f"   Скачано файлов: {downloaded_count}/{len(media_links)}")
    
    # Проверяем реально скачанные файлы
    downloaded_files = []
    if os.path.exists(test_dir):
        for file in os.listdir(test_dir):
            if os.path.isfile(os.path.join(test_dir, file)) and not file.startswith('.'):
                size = os.path.getsize(os.path.join(test_dir, file))
                downloaded_files.append((file, size))
    
    print(f"   Реально в папке: {len(downloaded_files)} файлов")
    for file, size in downloaded_files:
        print(f"      • {file} ({size} байт)")
    
    success = downloaded_count > 0 and len(downloaded_files) > 0
    print()
    
    if success:
        print("🎉 ТЕСТ ПРОЙДЕН: Скачивание работает!")
    else:
        print("💥 ТЕСТ ПРОВАЛЕН: Файлы не скачались!")
    
    print("=" * 50)
    return success

if __name__ == "__main__":
    success = test_full_download()
    exit(0 if success else 1)