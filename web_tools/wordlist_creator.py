#!/usr/bin/env python3

from argparse import ArgumentParser, FileType
from bs4 import BeautifulSoup
from datetime import datetime
from requests.exceptions import MissingSchema, ConnectionError, ConnectTimeout
import sys
import re
import os
import requests

# change the following, so it suits your needs..
VALID_WORD_PATTERN = "^[a-zA-Z0-9-]+$"
CHARS_TO_REMOVE = ("®", "/", "'", ".", "(", ")", "?", ":", "," "{", "{", "}", "}", "’", ",", "%", "&")
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:19.0) Gecko/20100101 Firefox/19.0"


def get_args():
    parser = ArgumentParser(description="Scrape webpages and create a wordlist")
    parser.add_argument("-u", "--url-list", dest="urls", type=FileType("r"), required=True,
                        help="Text file containing URLs to scrape for elements (one per line)")
    parser.add_argument("-e", "--exclude", dest="excluded", type=FileType("r"), nargs="*", required=False,
                        help="Text files containing words to be excluded from final wordlist (one per line)")
    parser.add_argument("-min", "--min-length", dest="min_len", type=int, required=False, help="Min word length")
    parser.add_argument("-max", "--max-length", dest="max_len", type=int, required=False, help="Max word length")
    arguments = vars(parser.parse_args())
    return arguments


def get_html_string(url):
    headers = { "User-Agent": USER_AGENT }
    response = requests.get(url, headers=headers)

    return  response.content.decode() if response.status_code == 200 else ""


def split_words(words):
    single_words = []
    for word_raw_str in words:
        for char in CHARS_TO_REMOVE:
            word_raw_str = word_raw_str.replace(char, "")
        w_no_newl = word_raw_str.replace("\n", " ").strip()
        words_split = w_no_newl.split(" ")
        for splitted_word in words_split:
            if splitted_word.strip() != "":  # remove empty strings
                single_words.append(splitted_word.strip())
    return single_words


def filter_words(words, **kwargs):
    words_filtered = []
    for word in words:
        if word.lower() in words_filtered or word.isdigit() or not re.match(VALID_WORD_PATTERN, word):  # already exist in the list OR is a number OR doesn't match the regex pattern
            continue  # skip to next
        if "min_len" in kwargs and kwargs["min_len"] is not None and len(word) < kwargs["min_len"]:  # word  minimum length
            continue
        if "max_len" in kwargs and kwargs["max_len"] is not None and len(word) > kwargs[
            "max_len"]:  # word maximum length
            continue
        if "excluded_words" in kwargs and kwargs["excluded_words"] is not None and word.lower() in kwargs[
            "excluded_words"]:  # list of words to exclude
            continue
        words_filtered.append(word.lower())
    words_filtered.sort()
    return words_filtered


def mangle_words():
    pass # TODO: implement this !


def write_to_file(words, filename_base):
    filename_final = f"{filename_base}.txt"
    file_number = 0

    while os.path.isfile(filename_final):
        file_number += 1
        filename_final = f"{filename_base}_{str(file_number)}.txt"

    with open(filename_final, "w") as word_list:
        for word in words:
            word_list.write(f"{word}\n")
    return filename_final


if __name__ == "__main__":
    try:
        args = get_args()
        with args["urls"] as url_list:
            urls = url_list.readlines()
        words = []

        for url in urls:  # Do for each URL: Get HTML data and parse selected elements
            try:
                if url.strip() == "":
                    print("Skipped empty line in URL file!")
                    continue

                print(f"GET: {url.strip()}")
                html = get_html_string(url.strip())

                if html == "":
                    print(f"Failed to get HTML elements from {url}")
                    continue

                print("Searching for HTML elements...")
                html_bs = BeautifulSoup(html, "html.parser")

                # included HTML elements
                html_elements = {"h1": html_bs.select("h1"), "h2": html_bs.select("h2"), "h3": html_bs.select("h3"),
                                 "h4": html_bs.select("h4"), "h5": html_bs.select("h5"), "li": html_bs.select("li")}

                for key, val in html_elements.items():
                    for element in val:
                        element_text = element.get_text().strip()
                        if element_text != "" or element_text != " ":
                            words.append(element.get_text().strip())
            except MissingSchema as exception:
                print(f"URL format incorrect - skipping to next! {exception}")
            except ConnectionError as exception:
                print(f"Failed to connect - skipping to next! {exception}")

        print("Splitting found text into single words...")
        s_words = split_words(words)

        # filter words
        # read excluded words from file(s)
        if "excluded" in args and args["excluded"] is not None:
            print("Collecting words to exclude...")
            args["excluded_words"] = []
            for file in args["excluded"]:
                with file as excluded_words_file:
                    words = []
                    for line in excluded_words_file.readlines():
                        words.append(line.replace("\n",
                                                  "").strip().lower())  # remove newline and spaces from lines + make lowercase
                    args["excluded_words"].extend(words)

            print(f"{len(args['excluded_words'])} words found on excluded list(s)...")

        # do the filtering...
        print("Filtering wordlist (please be patient!)...")
        filtered_words = filter_words(s_words, **args)

        # create filename with datetime and write list to file
        print("Creating file...")
        time_str = datetime.now().strftime("%d-%m-%y")
        filename = write_to_file(filtered_words, f"wordlist_{time_str}")
        print(f"{len(filtered_words)} words was written to {filename}")
        print("Script done!")

    except OSError as exception:
        print(
            f"An OSError occurred. Please check that you have sufficient permissions to the folder, in which the script is located, and to the URL and exclude files: {exception}")
        sys.exit(1)
    except Exception as exception:
        print(f"A general exception was caught. The script will terminate: {exception}")
        sys.exit(1)