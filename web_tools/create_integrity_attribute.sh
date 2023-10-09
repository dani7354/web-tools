#!/bin/bash

file=$1
[[ -e "$file" ]] || { echo "File not found" >&2 ; exit 1; }

sha256_hash=$(openssl sha256 -binary "$file" | base64)
sha384_hash=$(openssl sha384 -binary "$file" | base64)
sha512_hash=$(openssl sha512 -binary "$file" | base64)

echo "Integrity attrribute for <link> or <script> element:"
echo "integrity=\"sha256-${sha256_hash} sha384-${sha384_hash} sha512-${sha512_hash}\""
