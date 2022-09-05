# web-tools
Tools for testing web applications. 

## dir_fuzzer.py
Scans target webserver for hidden directories and files. One or more wordlists can be provided

## intruder.py
Performs brute-force password guessing against a target login site. 
It supports basic auth (GET), simple login forms and login forms with CSRF token validation. 
It may be necessary to configure or change parts of the script for each target site.