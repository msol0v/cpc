"""
Модуль для кэширования меток ARINC с восьмеричными ключами
"""

import time
from typing import Dict, Optional, List, Tuple
from threading import Timer
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CacheEntry:
    """Информация о записи в кэше"""
    value: int
    first_seen: float
    last_seen: float
    access_count: int = 0
    changes_count: int = 0


class LabelsCache:
    """
    Кэш для меток ARINC с ключами в виде восьмеричных строк

    Пример использования:
        cache = LabelsCache(stats_interval=120)  # статистика каждые 2 минуты

        # Добавление записи
        cache.put('352', 0x7F3A)

        # Получение записи
        value = cache.get('352')

        # Получение статистики
        top_labels = cache.get_top_labels(10)
        info = cache.get_label_info('352')
    """

    def __init__(self, stats_interval: float = 120.0):
        """
        Инициализация кэша

        Args:
            stats_interval: интервал вывода статистики в секундах
                           (по умолчанию 120 = 2 минуты)
        """
        # Кэш: ключ - строка в восьмеричной системе (например, '352'),
        # значение - CacheEntry
        self._cache: Dict[str, CacheEntry] = {}
        self._stats_interval = stats_interval
        self._start_time = time.time()
        self._last_stats_time = self._start_time
        self._timer: Optional[Timer] = None

        # Запускаем периодический таймер
        self._restart_timer()

    def _restart_timer(self) -> None:
        """Перезапускает таймер статистики"""
        if self._timer and self._timer.is_alive():
            self._timer.cancel()

        self._timer = Timer(self._stats_interval, self._print_stats)
        self._timer.daemon = True
        self._timer.start()

    def put(self, label_octal: str, word_int: int) -> None:
        """
        Добавляет или обновляет значение в кэше

        Args:
            label_octal: метка в восьмеричной системе (например, '352')
            word_int: значение слова ARINC
        """
        now = time.time()

        if label_octal in self._cache:
            entry = self._cache[label_octal]
            if entry.value != word_int:
                entry.changes_count += 1
            entry.value = word_int
            entry.last_seen = now
            entry.access_count += 1
        else:
            self._cache[label_octal] = CacheEntry(
                value=word_int,
                first_seen=now,
                last_seen=now,
                access_count=1,
                changes_count=0
            )

    def get(self, label_octal: str) -> Optional[int]:
        """
        Получает значение из кэша по метке

        Args:
            label_octal: метка в восьмеричной системе (например, '352')

        Returns:
            Optional[int]: значение слова или None если метка не найдена
        """
        entry = self._cache.get(label_octal)
        if entry:
            entry.access_count += 1
            entry.last_seen = time.time()
            return entry.value
        return None

    def _print_stats(self) -> None:
        """Выводит статистику использования кэша"""
        now = time.time()
        elapsed = now - self._start_time

        print("\n" + "=" * 80)
        print(f"📊 CACHE STATISTICS (Runtime: {elapsed / 60:.1f} minutes)")
        print("=" * 80)

        if not self._cache:
            print("No cache activity")
            print("=" * 80)
            self._last_stats_time = now
            self._restart_timer()
            return

        # Сортируем по количеству обращений
        sorted_items = sorted(
            self._cache.items(),
            key=lambda x: x[1].access_count,
            reverse=True
        )

        # Заголовок таблицы
        print(f"{'Label (octal)':<15} {'Accesses':<12} {'Changes':<10} "
              f"{'Value (hex)':<15} {'Last seen':<20}")
        print("-" * 80)

        for label_octal, entry in sorted_items[:15]:  # Показываем топ-15
            last_seen_str = datetime.fromtimestamp(entry.last_seen).strftime('%H:%M:%S')
            value_hex = f"0x{entry.value:X}" if entry.value is not None else "N/A"
            print(f"{label_octal:<15} {entry.access_count:<12} {entry.changes_count:<10} "
                  f"{value_hex:<15} {last_seen_str:<20}")

        if len(sorted_items) > 15:
            print(f"... and {len(sorted_items) - 15} more labels")

        # Общая статистика
        print("-" * 80)
        total_accesses = sum(e.access_count for e in self._cache.values())
        active_labels = sum(1 for e in self._cache.values()
                            if now - e.last_seen < 10.0)  # Активны в последние 10 сек

        print(f"Total unique labels: {len(self._cache)}")
        print(f"Total accesses: {total_accesses}")
        print(f"Active labels (last 10s): {active_labels}")
        print(f"Accesses per second: {total_accesses / elapsed:.2f}")
        print("=" * 80)

        self._last_stats_time = now
        self._restart_timer()

    def get_top_labels(self, n: int = 10) -> List[Tuple[str, int]]:
        """
        Возвращает топ N самых часто встречающихся меток

        Args:
            n: количество меток для возврата

        Returns:
            List[Tuple[str, int]]: список (label_octal, access_count)
        """
        return sorted(
            [(label, entry.access_count) for label, entry in self._cache.items()],
            key=lambda x: x[1],
            reverse=True
        )[:n]

    def get_label_info(self, label_octal: str) -> Optional[Dict]:
        """
        Возвращает детальную информацию по конкретной метке

        Args:
            label_octal: метка в восьмеричной системе

        Returns:
            Optional[Dict]: информация о метке или None если метка не найдена
        """
        entry = self._cache.get(label_octal)
        if entry:
            return {
                'value': entry.value,
                'value_hex': f"0x{entry.value:X}",
                'value_dec': entry.value,
                'access_count': entry.access_count,
                'changes_count': entry.changes_count,
                'first_seen': datetime.fromtimestamp(entry.first_seen).strftime('%H:%M:%S'),
                'last_seen': datetime.fromtimestamp(entry.last_seen).strftime('%H:%M:%S'),
                'frequency_hz': entry.access_count / (entry.last_seen - entry.first_seen)
                if entry.last_seen > entry.first_seen else 0
            }
        return None

    def get_all_labels(self) -> List[str]:
        """
        Возвращает список всех меток в кэше

        Returns:
            List[str]: список восьмеричных меток
        """
        return list(self._cache.keys())

    def clear(self) -> None:
        """Очищает кэш и сбрасывает статистику"""
        self._cache.clear()
        print("🧹 Cache cleared")

    def stop(self) -> None:
        """Останавливает таймер и выводит финальную статистику"""
        if self._timer and self._timer.is_alive():
            self._timer.cancel()

        if self._cache:
            print("\n" + "🎯 FINAL CACHE STATISTICS")
            self._print_stats()
        else:
            print("\n" + "🎯 No cache activity during runtime")

    def __del__(self):
        """Деструктор для очистки таймера"""
        if self._timer and self._timer.is_alive():
            self._timer.cancel()