#!/usr/bin/env python3
import os
import argparse
import queue
from threading import Thread

import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from slugify import slugify

MAX_THREADS = 8


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download media files from RSS feed")
    parser.add_argument("-u", "--url", dest="url", type=str, required=True)
    parser.add_argument("-d", "--dir", dest="dir", type=str, required=True)

    return parser.parse_args()


def read_rss_feed(url: str, directory: str) -> list[tuple[str, str]]:
    response = requests.get(url)
    response.raise_for_status()

    os.path.join(directory, f"feed_{datetime.now().isoformat()}.rss")
    with open("feed.rss", "w") as feed_file:
        feed_file.write(response.text)

    rss_tree = ET.ElementTree(ET.fromstring(response.content))
    items = rss_tree.findall(".//item")

    return [(x.find("enclosure").get("url"), x.findtext("title")) for x in items]


def create_queue(items) -> queue.Queue:
    items_queue = queue.Queue()
    [items_queue.put(i) for i in items]

    return items_queue


def download_next_file(items_queue: queue.Queue, directory: str) -> None:
    while not items_queue.empty():
        url, title = items_queue.get()
        print(f"Downloading {title}: {url}")
        response = requests.get(url)

        file_name = f"{slugify(title)}.mp3"
        full_path = os.path.join(directory, file_name)
        with open(full_path, "wb") as file:
            file.write(response.content)


def main():
    args = parse_arguments()
    print(f"Reading RSS feed at {args.url}...")
    items = read_rss_feed(args.url, args.dir)
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
