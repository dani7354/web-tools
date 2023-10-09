#!/usr/bin/env python3
from requests.exceptions import HTTPError
import argparse
import requests
import time


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", dest="url", type=str, required=True)
    parser.add_argument("-c", "--count", dest="count", type=int, required=False, default=1)
    parser.add_argument("-p", "--pages", dest="pages", type=int, nargs="+", required=True)

    return parser.parse_args()


def time_requests(url: str, count: int, page_start: int, page_end: int) -> list[float]:
    """ Time requests to a URL
     :param url: URL as format string with one integer placeholder for page number
     :param count: number of rounds to request pages
     :param pages: list of page numbers to request
     :param page_start: first page number to request
     :param page_end: last page number to request"""

    response_times = []
    for i in range(count):
        for page in range(page_start, page_end + 1):
            try:
                page_url = url.format(page)
                print(f"GET {page_url}...")
                start_time = time.time()
                response = requests.get(page_url)
                response.raise_for_status()
                end_time = time.time()
                response_time = end_time - start_time
                response_times.append(response_time)
                print(f"Response time: {response_time}")
            except HTTPError as e:
                print(f"Error: {e}")

        return response_times


def main():
    args = parse_arguments()
    assert len(args.pages) == 2

    response_times = time_requests(args.url, args.count, args.pages[0], args.pages[1])
    print(f"Average response time: {sum(response_times) / len(response_times)}")


if __name__ == "__main__":
    main()
