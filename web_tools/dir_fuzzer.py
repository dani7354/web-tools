#!/usr/bin/env python3
import argparse
import queue
import requests
import sys
import threading
import time
import urllib.parse

THREAD_COUNT = 50
THREAD_SLEEP_SECONDS = 0
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:19.0) Gecko/20100101 Firefox/19.0"
EXTENSIONS = ['.php', '.html', '.orig', '.bak']
CONNECTION_ERROR_MSG = "An error occurred while sending request!"

urls = []


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", dest="url", type=str, required=True)
    parser.add_argument("-w", "--word-lists", dest="word_lists", nargs="+", type=str, required=True)

    return parser.parse_args()


def add_words(wordlist, words_queue):
    def extend_words(word):
        if "." in word:
            words_queue.put(f'/{word}')
        else:
            words_queue.put(f'/{word}/')
        for extension in EXTENSIONS:
            words_queue.put(f'/{word}{extension}')

    with open(wordlist, "r") as wordlist_file:
        words_from_file = wordlist_file.readlines()
    [extend_words(word.strip()) for word in words_from_file]


def get_words_from_files(wordlists) -> queue.Queue:
    words = queue.Queue()
    for wordlist in wordlists:
        add_words(wordlist, words)

    return words


def try_urls(word_queue, target):
    global urls
    with requests.Session() as session:
        while not word_queue.empty():
            directory = word_queue.get()
            absolute_url = urllib.parse.urljoin(target, directory)
            try:
                headers = {"User-Agent": USER_AGENT}
                response = session.get(
                    absolute_url,
                    headers=headers)
                if response.status_code == 200:
                    print(f"{absolute_url} => 200")
                    urls.append(absolute_url)
                else:
                    print(f"{absolute_url} => {response.status_code}")
            except requests.exceptions.ConnectionError:
                sys.stderr.write(CONNECTION_ERROR_MSG)
                sys.stderr.flush()
                continue
            finally:
                time.sleep(THREAD_SLEEP_SECONDS)


def main():
    try:
        arguments = parse_arguments()

        print("Reading passwords from wordlists...")
        word_queue = get_words_from_files(arguments.word_lists)

        print(f"{word_queue.qsize()} words read from files. Press return to start...")
        sys.stdin.readline()

        threads = []
        for _ in range(THREAD_COUNT):
            t = threading.Thread(target=try_urls, args=(word_queue, arguments.url,))
            threads.append(t)
            t.start()

        [t.join() for t in threads]
        print("Script finished!")

        print("Found urls:")
        [print(url) for url in urls]

    except Exception as ex:
        print(ex)
        sys.exit(1)


if __name__ == "__main__":
    main()
