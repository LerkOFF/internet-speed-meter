#!/usr/bin/env python3
"""Замер скорости интернета: 10 раз подряд скачивает файл по адресу
и печатает среднее время запроса, объём скачанного и скорость в МБ/с."""

import sys
import time
import urllib.request

REQUESTS = 10
MB = 1_000_000  # десятичный мегабайт, как в тарифах провайдеров
CHUNK_SIZE = 64 * 1024
USER_AGENT = "internet-speed-meter/1.0 (Python urllib)"


def download(url):
    """Скачивает url целиком. Возвращает (байт в теле ответа, секунд на весь запрос)."""
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept-Encoding": "identity",  # без сжатия: считаем байты самого файла
        "Cache-Control": "no-cache",    # просим промежуточные кэши не отдавать сохранённую копию
    })
    received = 0
    started = time.perf_counter()
    with urllib.request.urlopen(request) as response:
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            received += len(chunk)
    return received, time.perf_counter() - started


def main():
    if len(sys.argv) != 2:
        print("Использование: python3 speed_meter.py URL", file=sys.stderr)
        return 2
    url = sys.argv[1]

    total_bytes = 0
    total_seconds = 0.0
    for number in range(1, REQUESTS + 1):
        size, seconds = download(url)
        total_bytes += size
        total_seconds += seconds
        print(f"[{number}/{REQUESTS}] {size / MB:.2f} МБ за {seconds:.2f} с")

    speed = total_bytes / MB / total_seconds
    print()
    print(f"Среднее время запроса: {total_seconds / REQUESTS:.3f} с")
    print(f"Скачано всего:         {total_bytes / MB:.2f} МБ")
    print(f"Скорость:              {speed:.2f} МБ/с")
    return 0


if __name__ == "__main__":
    sys.exit(main())
