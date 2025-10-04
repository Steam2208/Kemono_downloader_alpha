#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 Тест прогресс-баров v2.8.3
=============================
Проверяем что прогресс-бары обновляются правильно
"""

import sys
import os
import threading
import time

# Добавляем путь к нашим модулям
sys.path.append('.')

from downloader_static import download_files_parallel

def test_progress_callbacks():
    """Тестируем callback-функции прогресса"""
    print("🧪 ТЕСТ ПРОГРЕСС-БАРОВ v2.8.3")
    print("=" * 40)
    
    # Тестовые URL - короткие файлы для быстрого тестирования
    test_links = [
        "https://n2.kemono.cr/data/patreon/804602/224552fc5517153761fdb3e036d8cb6a415b3730fbddbf2161eef579f71783b4.png"  # Реальный файл
    ]
    
    test_dir = "test_progress_bars"
    if os.path.exists(test_dir):
        import shutil
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)
    
    print(f"🎯 Тестируем {len(test_links)} файлов")
    print()
    
    # Переменные для отслеживания callback'ов
    thread_updates = []
    overall_updates = []
    
    def thread_callback(thread_id, filename, current, total):
        """Callback для прогресса потоков"""
        thread_updates.append((thread_id, filename, current, total))
        print(f"🔄 Поток-{thread_id}: {filename[:30]} -> {current}/{total}")
    
    def overall_callback(current, total):
        """Callback для общего прогресса"""
        overall_updates.append((current, total))
        print(f"📊 Общий прогресс: {current}/{total}")
    
    print("📥 Запускаем скачивание с callback'ами...")
    start_time = time.time()
    
    downloaded_count = download_files_parallel(
        test_links,
        test_dir,
        progress_data=None,
        max_workers=2,
        thread_callback=thread_callback,
        overall_callback=overall_callback,
        stop_check=None
    )
    
    end_time = time.time()
    
    print()
    print("📊 РЕЗУЛЬТАТЫ ТЕСТА:")
    print(f"   Время выполнения: {end_time - start_time:.1f}с")
    print(f"   Скачано файлов: {downloaded_count}")
    print(f"   Thread callback вызовов: {len(thread_updates)}")
    print(f"   Overall callback вызовов: {len(overall_updates)}")
    
    if thread_updates:
        print("\n🔄 Thread callback вызовы:")
        for i, (tid, fname, curr, tot) in enumerate(thread_updates[-5:], 1):  # Последние 5
            print(f"      {i}. Поток-{tid}: {curr}/{tot}")
    
    if overall_updates:
        print("\n📊 Overall callback вызовы:")
        for i, (curr, tot) in enumerate(overall_updates, 1):
            print(f"      {i}. {curr}/{tot}")
    
    # Проверяем результат
    success = (
        downloaded_count > 0 and 
        len(thread_updates) > 0 and 
        len(overall_updates) > 0
    )
    
    print()
    if success:
        print("🎉 ТЕСТ ПРОЙДЕН: Прогресс-бары должны обновляться!")
    else:
        print("💥 ТЕСТ ПРОВАЛЕН: Callback'и не вызываются!")
    
    print("=" * 40)
    return success

if __name__ == "__main__":
    success = test_progress_callbacks()
    exit(0 if success else 1)