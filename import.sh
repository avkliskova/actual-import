#!/bin/sh

filename="/root/transactions/$(date "+%s").json"

python3 mail.py -o $filename
node import-transactions.js $filename
