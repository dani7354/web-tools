#!/usr/bin/env python3
from argparse import ArgumentParser, FileType
from datetime import datetime
from requests.exceptions import RequestException
from html.parser import HTMLParser
import requests
import threading
import re
import os
import queue

class TagStripper(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.text = []

    def handle_data(self, data) -> None:
        self.text.append(data)

    def handle_comment(self, data) -> None:
        self.text.append(data)

    def strip(self, html) -> str:
        self.feed(html)
        return " ".join(self.text)


VALID_WORD_PATTERN = "[a-zA-Z]\w{2,}"

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:19.0) Gecko/20100101 Firefox/19.0"
THREADS = 4


def get_args():
    parser = ArgumentParser(description="Scrapes webpages and creates a wordlist.")
    parser.add_argument("-u", "--url-list", dest="urls", type=FileType("r"), required=True,
                        help="Text file containing URLs to scrape for elements (one per line).")
    return parser.parse_args()

def get_html_string(url):
    headers = { "User-Agent": USER_AGENT }
    response = requests.get(url, headers=headers)

    return response.content.decode() if response.status_code in (200, 301, 302) else ""

def mangle_word(word) -> list: # TODO: finish suffixes
    current_year = datetime.now().year
    suffixes = [ "", "#", f"{current_year}!", current_year ]
    mangled = []

    for w in (word, word.capitalize()):
        for s in suffixes:
            mangled.append(f"{w}{s}")

    return mangled

def write_to_file(words, filename_base) -> str:
    filename_final = f"{filename_base}.txt"
    file_number = 0

    while os.path.isfile(filename_final):
        file_number += 1
        filename_final = f"{filename_base}_{str(file_number)}.txt"

    with open(filename_final, "w") as word_list:
        for word in words:
            word_list.write(f"{word}\n")
    return filename_final


def get_words(urls, found_words) -> None:
    words = []
    url = ""
    while not  urls.empty():
        try:
            url = urls.get()
            print(f"GET: {url}")
            content = get_html_string(url)
            tag_stripper = TagStripper()
            content_stripped = tag_stripper.strip(content)
            words_from_content = re.findall(VALID_WORD_PATTERN, content_stripped)
            [words.extend(mangle_word(w.lower())) for w in words_from_content]
        except RequestException as ex:
            print(f"Something went wrong while getting words from url {url}. Exception: {ex}")
            continue

    for word in words:
        found_words.put(word)



def read_urls(file) -> list:
    with file as url_list:
        return url_list.readlines()


def main():
    args = get_args()
    urls = read_urls(args.urls)
    urls_queue = queue.Queue()

    for url in urls:
        if url.strip() == "":
            print("Skipped empty line in URL file!")
            continue

        urls_queue.put(url.strip())

    threads = []
    found_words = queue.Queue()
    for _ in range(THREADS):
        t = threading.Thread(target=get_words, args=(urls_queue, found_words,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    print("Creating file...")
    words_set = set(found_words.queue)
    time_str = datetime.now().strftime("%d-%m-%y")
    filename = write_to_file(words_set, f"wordlist_{time_str}")
    print(f"{len(words_set)} words was written to {filename}")
    print("Script done!")

if __name__ == "__main__":
    main()