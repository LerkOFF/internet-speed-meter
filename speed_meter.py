#!/usr/bin/env python3
"""Замер скорости интернета: N раз подряд скачивает файл по адресу
и печатает среднее время запроса, объём скачанного и скорость в МБ/с.

Пример:
    python3 speed_meter.py https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Pizigani_1367_Chart_10MB.jpg/3840px-Pizigani_1367_Chart_10MB.jpg
"""

import argparse
import sys
import time
import urllib.parse
import urllib.request

MB = 1_000_000  # десятичный мегабайт, как в тарифах провайдеров
CHUNK_SIZE = 64 * 1024
USER_AGENT = "internet-speed-meter/1.0 (Python urllib)"


def http_url(value):
    """Тип для argparse: адрес http(s); без схемы подставляет https://."""
    if "://" not in value:
        value = "https://" + value
    parts = urllib.parse.urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise argparse.ArgumentTypeError(f"нужен адрес вида https://host/file.jpg, а не {value!r}")
    return value


def positive(cast):
    """Тип для argparse: число больше нуля."""
    def convert(value):
        try:
            number = cast(value)
            if number > 0:
                return number
        except ValueError:
            pass
        raise argparse.ArgumentTypeError(f"нужно число больше нуля, а не {value!r}")
    return convert


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Замер скорости интернета: N раз подряд скачивает файл по адресу "
                    "и печатает среднее время запроса, объём и скорость в МБ/с.")
    parser.add_argument("url", type=http_url,
                        help="адрес тяжёлого файла, например большой картинки")
    parser.add_argument("-n", "--count", type=positive(int), default=10,
                        help="сколько запросов сделать (по умолчанию 10)")
    parser.add_argument("-t", "--timeout", type=positive(float), default=30.0,
                        help="сколько секунд ждать ответа сервера (по умолчанию 30)")
    return parser.parse_args(argv)


def download(url, timeout):
    """Скачивает url целиком. Возвращает (байт в теле ответа, секунд на весь запрос)."""
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept-Encoding": "identity",  # без сжатия: считаем байты самого файла
        "Cache-Control": "no-cache",    # просим промежуточные кэши не отдавать сохранённую копию
    })
    received = 0
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            received += len(chunk)
    return received, time.perf_counter() - started


def main(argv=None):
    args = parse_args(argv)
    print(f"Адрес: {args.url}")
    print(f"Запросов: {args.count}, по очереди\n")

    total_bytes = 0
    total_seconds = 0.0
    width = len(str(args.count))
    for number in range(1, args.count + 1):
        size, seconds = download(args.url, args.timeout)
        total_bytes += size
        total_seconds += seconds
        print(f"[{number:>{width}}/{args.count}] {size / MB:8.2f} МБ за {seconds:6.2f} с, {size / MB / seconds:7.2f} МБ/с")

    speed = total_bytes / MB / total_seconds
    print()
    print(f"Среднее время запроса: {total_seconds / args.count:.3f} с")
    print(f"Скачано всего:         {total_bytes / MB:.2f} МБ")
    print(f"Скорость:              {speed:.2f} МБ/с")
    return 0


if __name__ == "__main__":
    sys.exit(main())
