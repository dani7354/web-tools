#!/bin/bash

host=$1
cert_file="certificate.crt"

[[ -n $host ]] || { echo "Missing host!" >&2 ; exit 1; }

echo "Getting certificate from webserver ..."
true | openssl s_client -connect "$host:443" | sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > $cert_file

[[ -x /usr/bin/tlsa ]] || { echo "tlsa command missing! Installing hash-slinger package ..."; sudo apt install hash-slinger; }

echo "Creating TLSA record ..."
tlsa --create --selector 1 --certificate "$cert_file" "$host"

echo "Cleaning up ..."
rm $cert_file
