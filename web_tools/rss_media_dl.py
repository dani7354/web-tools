#!/usr/bin/env python3
import argparse
import os
import queue
import xml.etree.ElementTree as ET
from datetime import datetime
from threading import Thread
from typing import Sequence

import requests
from slugify import slugify

MAX_THREADS = 8


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download media files from RSS feed")
    parser.add_argument("-u", "--url", dest="url", type=str, required=True)
    parser.add_argument("-d", "--dir", dest="dir", type=str, required=True)
    parser.add_argument("-w", "--words", dest="words", nargs="+", type=str, required=False)

    return parser.parse_args()

def is_match(item: tuple[str, str], words: Sequence[str]) -> bool:
    url, title = item
    for word in words:
        if word in title or word in url:
            return True

    return False


def read_rss_feed(url: str, directory: str, words: Sequence[str]) -> list[tuple[str, str]]:
    response = requests.get(url)
    response.raise_for_status()

    feed_rss_path = os.path.join(directory, f"feed_{slugify(datetime.now().isoformat())}.rss")
    with open(feed_rss_path, "w") as feed_file:
        feed_file.write(response.text)

    rss_tree = ET.ElementTree(ET.fromstring(response.content))
    items = rss_tree.findall(".//item")
    item_tuples = filter(
        lambda x: is_match(x, words),
        [(x.find("enclosure").get("url"), x.findtext("title")) for x in items])

    return list(item_tuples)


def create_queue(items) -> queue.Queue:
    items_queue = queue.Queue()
    [items_queue.put(i) for i in items]

    return items_queue


def save_file(filename: str, directory: str, content: bytes):
    full_path = os.path.join(directory, filename)
    counter = 1
    while os.path.exists(full_path):
        full_path = os.path.join(directory, f"{filename}_{counter}.mp3")
        counter += 1

    print(f"Saving {filename} to {full_path}")
    with open(full_path, "wb") as file:
        file.write(content)


def download_next_file(items_queue: queue.Queue, directory: str) -> None:
    while not items_queue.empty():
        url, title = items_queue.get()
        print(f"Downloading {title}: {url}")
        response = requests.get(url)
        filename = f"{slugify(url.split("/")[-1].strip('.mp3'))}.mp3"
        save_file(filename, directory, response.content)


def main() -> None:
    args = parse_arguments()

    print(f"Reading RSS feed at {args.url}...")
    items = read_rss_feed(args.url, args.dir, args.words)
    if not items:
        print("No items found in RSS feed")
        return

    print(f"Downloaded {len(items)} items from RSS feed")
    items_queue = create_queue(items)

    print(f"Downloading media files to {args.dir}...")
    threads = []
    for t in range(MAX_THREADS):
        t = Thread(target=download_next_file, args=(items_queue, args.dir))
        t.start()
        threads.append(t)
    [t.join() for t in threads]
    print("Finished downloading media files")


if __name__ == "__main__":
    main()
