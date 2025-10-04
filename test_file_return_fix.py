#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔧 Тест исправления скачивания файлов v2.8.2
========================================================
Проверяем что обычные файлы теперь возвращаются правильно
"""

import sys
import os

# Добавляем путь к нашим модулям
sys.path.append('.')

from downloader_static import get_post_media

def test_file_return():
    """Тестируем что функция возвращает обычные файлы"""
    print("🧪 ТЕСТ: Проверяем возврат обычных файлов из get_post_media")
    print("=" * 60)
    
    # Тестируем на посте который точно содержит файлы
    test_url = "https://kemono.cr/patreon/user/804602/post/91974242"  # Этот пост точно содержит изображение
    
    print(f"🎯 Тестируем пост: {test_url}")
    print()
    
    # Получаем медиа без указания save_dir (чтобы не скачивать облачные файлы)
    media_links = get_post_media(test_url, enhanced_search=True, save_dir=None)
    
    print()
    print("📊 РЕЗУЛЬТАТ ТЕСТА:")
    print(f"   Возвращено ссылок: {len(media_links) if media_links else 0}")
    
    if media_links:
        print("   ✅ УСПЕХ: Функция возвращает файлы!")
        print("   📋 Список возвращенных файлов:")
        for i, link in enumerate(media_links, 1):
            filename = link.split('/')[-1].split('?')[0]
            print(f"      {i}. {filename}")
    else:
        print("   ❌ ПРОВАЛ: Функция НЕ возвращает файлы!")
    
    print()
    print("=" * 60)
    return len(media_links) > 0 if media_links else False

if __name__ == "__main__":
    success = test_file_return()
    
    if success:
        print("🎉 ТЕСТ ПРОЙДЕН: Исправление работает!")
        exit(0)
    else:
        print("💥 ТЕСТ ПРОВАЛЕН: Требуется дополнительное исправление!")
        exit(1)