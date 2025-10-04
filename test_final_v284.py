#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 Финальный тест KemonoDownloader v2.8.4
========================================
Проверяем все исправления:
1. Файлы находятся и возвращаются правильно
2. Прогресс-бары инициализируются и обновляются
3. Многопоточное скачивание работает
"""

import sys
import os
import shutil
import time

# Добавляем путь к модулям
sys.path.append('.')

from downloader_static import get_post_media, download_files_parallel

def main_test():
    """Основной тест всех компонентов"""
    print("🧪 ФИНАЛЬНЫЙ ТЕСТ KEMONODOWNLOADER v2.8.4")
    print("=" * 55)
    
    # Тестовые данные
    test_url = "https://kemono.cr/patreon/user/804602/post/91974242"
    test_dir = "test_final_v284"
    
    # Очистка тестовой папки
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)
    
    results = {}
    
    print("🔍 ТЕСТ 1: Получение файлов из поста")
    print("-" * 35)
    
    start_time = time.time()
    media_links = get_post_media(test_url, enhanced_search=True, save_dir=test_dir)
    get_time = time.time() - start_time
    
    if media_links and len(media_links) > 0:
        print(f"✅ Найдено файлов: {len(media_links)}")
        for i, link in enumerate(media_links, 1):
            filename = link.split('/')[-1].split('?')[0]
            print(f"   {i}. {filename[:50]}...")
        results['files_found'] = True
    else:
        print("❌ Файлы не найдены!")
        results['files_found'] = False
    
    print(f"⏱️ Время получения: {get_time:.1f}с")
    print()
    
    if not media_links:
        print("💥 ТЕСТ ПРОВАЛЕН: Нет файлов для скачивания")
        return False
    
    print("📥 ТЕСТ 2: Прогресс-бары и скачивание")
    print("-" * 35)
    
    # Счетчики для callback'ов
    thread_calls = []
    overall_calls = []
    
    def track_thread_progress(thread_id, filename, current, total):
        thread_calls.append((thread_id, filename[:20], current, total))
        print(f"🔄 Поток-{thread_id}: {current:3d}% - {filename[:25]}")
    
    def track_overall_progress(current, total):
        overall_calls.append((current, total))
        print(f"📊 Общий: {current}/{total} ({current/total*100:.0f}%)")
    
    print("🚀 Запускаем многопоточное скачивание...")
    start_time = time.time()
    
    downloaded = download_files_parallel(
        media_links,
        test_dir,
        progress_data=None,
        max_workers=3,
        thread_callback=track_thread_progress,
        overall_callback=track_overall_progress,
        stop_check=None
    )
    
    download_time = time.time() - start_time
    
    print()
    print("📊 РЕЗУЛЬТАТЫ ТЕСТОВ:")
    print("-" * 25)
    print(f"⏱️ Время скачивания: {download_time:.1f}с")
    print(f"📁 Скачано файлов: {downloaded}/{len(media_links)}")
    print(f"🔄 Thread callback вызовов: {len(thread_calls)}")
    print(f"📊 Overall callback вызовов: {len(overall_calls)}")
    
    # Проверяем реальные файлы
    real_files = []
    if os.path.exists(test_dir):
        for file in os.listdir(test_dir):
            filepath = os.path.join(test_dir, file)
            if os.path.isfile(filepath) and not file.startswith('.'):
                size = os.path.getsize(filepath)
                real_files.append((file, size))
    
    print(f"💾 Реальных файлов в папке: {len(real_files)}")
    for file, size in real_files:
        size_mb = size / (1024 * 1024)
        print(f"   • {file} ({size_mb:.1f} MB)")
    
    print()
    
    # Анализ результатов
    results.update({
        'files_downloaded': downloaded > 0,
        'real_files_exist': len(real_files) > 0,
        'thread_callbacks_work': len(thread_calls) > 0,
        'overall_callbacks_work': len(overall_calls) > 0,
        'progress_initialized': any(call[0] == 0 for call in overall_calls),
        'progress_completed': any(call[0] == call[1] for call in overall_calls)
    })
    
    print("🎯 АНАЛИЗ ИСПРАВЛЕНИЙ:")
    print("-" * 25)
    print(f"✅ Файлы находятся: {results['files_found']}")
    print(f"✅ Файлы скачиваются: {results['files_downloaded']}")
    print(f"✅ Реальные файлы создаются: {results['real_files_exist']}")
    print(f"✅ Thread прогресс работает: {results['thread_callbacks_work']}")
    print(f"✅ Overall прогресс работает: {results['overall_callbacks_work']}")
    print(f"✅ Прогресс инициализируется: {results['progress_initialized']}")
    print(f"✅ Прогресс завершается: {results['progress_completed']}")
    
    # Итоговая оценка
    all_good = all(results.values())
    
    print()
    print("=" * 55)
    if all_good:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! KemonoDownloader v2.8.4 работает!")
        print("   • Исправлено скачивание файлов")  
        print("   • Исправлены прогресс-бары")
        print("   • Многопоточность работает")
    else:
        print("⚠️ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        failed = [k for k, v in results.items() if not v]
        print(f"   Проблемы: {', '.join(failed)}")
    
    print("=" * 55)
    return all_good

if __name__ == "__main__":
    success = main_test()
    exit(0 if success else 1)