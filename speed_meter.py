#!/usr/bin/env python3
"""Замер скорости интернета: N раз подряд скачивает файл по адресу
и печатает среднее время запроса, объём скачанного и скорость в МБ/с.

Пример:
    python3 speed_meter.py https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Pizigani_1367_Chart_10MB.jpg/3840px-Pizigani_1367_Chart_10MB.jpg
"""

import argparse
import http.client
import socket
import sys
import time
import urllib.error
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
        expected = response.headers.get("Content-Length", "")
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            received += len(chunk)
    elapsed = time.perf_counter() - started
    # http.client на оборванном ответе молча отдаёт b"", поэтому сверяем длину сами
    if expected.isdigit() and received != int(expected):
        raise ConnectionError(f"ответ оборван: получено {received} из {expected} байт")
    return received, elapsed


def describe(error):
    """Короткое описание упавшего запроса для консоли."""
    if isinstance(error, urllib.error.HTTPError):
        return f"HTTP {error.code} {error.reason}"
    reason = getattr(error, "reason", error)  # URLError прячет настоящую причину в .reason
    if isinstance(reason, socket.timeout):
        return "сервер не ответил за отведённое время"
    return str(reason) or type(reason).__name__


def main(argv=None):
    args = parse_args(argv)
    print(f"Адрес: {args.url}")
    print(f"Запросов: {args.count}, по очереди\n")

    results = []  # (байт, секунд) по каждому успешному запросу
    width = len(str(args.count))
    for number in range(1, args.count + 1):
        prefix = f"[{number:>{width}}/{args.count}]"
        try:
            size, seconds = download(args.url, args.timeout)
        except (OSError, http.client.HTTPException) as error:
            print(f"{prefix} ошибка: {describe(error)}")
            continue
        results.append((size, seconds))
        print(f"{prefix} {size / MB:8.2f} МБ за {seconds:6.2f} с, {size / MB / seconds:7.2f} МБ/с")

    if not results:
        sys.stdout.flush()  # иначе при выводе в файл stderr обгоняет буферизованный stdout
        print("Ни один запрос не удался, скорость считать не из чего.", file=sys.stderr)
        return 1

    total_bytes = sum(size for size, _ in results)
    total_seconds = sum(seconds for _, seconds in results)
    speed = total_bytes / MB / total_seconds
    print()
    print(f"Успешных запросов:     {len(results)} из {args.count}")
    print(f"Среднее время запроса: {total_seconds / len(results):.3f} с")
    print(f"Скачано всего:         {total_bytes / MB:.2f} МБ")
    print(f"Скорость:              {speed:.2f} МБ/с")
    return 0


if __name__ == "__main__":
    sys.exit(main())
