from dataclasses import dataclass
import argparse
import imaplib, email, quopri, time, re
import json
import typing

from bs4 import BeautifulSoup

from secrets import username, bridge_password

@dataclass
class Transaction:
    date: str
    payee: str
    amount: int


def get_amount(soup) -> typing.Optional[int]:
    tag = soup.find("b", string=re.compile("Transaction Amount"))
    if tag:
        amount_str = tag.next_sibling.strip()
        amount = float(amount_str.split()[0]) * -100

        return int(amount)

    return None


def get_payee(soup) -> typing.Optional[str]:
    tag = soup.find("b", string=re.compile("Merchant"))
    if tag:
        return tag.next_sibling.strip()

    return None


def get_deposit_payee(soup) -> str:
    tag = soup.find("h4", string=re.compile("Payment From"))
    if tag:
        payee_str = tag.text.split(":")[1].strip()
        return payee_str
    return "Branch Deposit"

def get_deposit_amount(soup) -> typing.Optional[int]:
    tag = soup.find("h4", string=re.compile("Amount"))
    if tag:
        amount_str = tag.text.split("$")[1].strip()
        amount = float(amount_str) * 100

        return int(amount)

    return None


def convert_transaction(trans: Transaction) -> dict:
    return { "date": trans.date,
             "payee_name": trans.payee,
             "amount": trans.amount }


def parse_withdrawal(conn, idx) -> Transaction:
    # Fetch email internal date.
    resp, data = conn.fetch(idx, "(INTERNALDATE)")
    assert isinstance(data[0], bytes)

    date_struct = imaplib.Internaldate2tuple(data[0])
    date = time.strftime("%Y-%m-%d", date_struct)

    # Fetch email body as quoted-printable text.
    resp, data = conn.fetch(idx, "(BODY.PEEK[TEXT])")
    assert isinstance(data[0], tuple)

    msg = quopri.decodestring(data[0][1]).decode()
    soup = BeautifulSoup(msg, 'html.parser')

    # This is hardcoded to the emails PNC sends me.
    # I expect it to break in the future, but there's no document structure
    # to their emails so ¯\_(ツ)_/¯
    amount = get_amount(soup)
    payee = get_payee(soup)

    if not (amount and payee):
        raise ValueError

    return Transaction(date=date, amount=amount, payee=payee)


def parse_deposit(conn, idx) -> Transaction:
    # Fetch email internal date.
    resp, data = conn.fetch(idx, "(INTERNALDATE)")
    assert isinstance(data[0], bytes)

    date_struct = imaplib.Internaldate2tuple(data[0])
    date = time.strftime("%Y-%m-%d", date_struct)

    # Fetch email body as quoted-printable text.
    resp, data = conn.fetch(idx, "(BODY.PEEK[TEXT])")
    assert isinstance(data[0], tuple)

    msg = quopri.decodestring(data[0][1]).decode()
    soup = BeautifulSoup(msg, 'html.parser')

    # This is hardcoded to the emails PNC sends me.
    # I expect it to break in the future, but there's no document structure
    # to their emails so ¯\_(ツ)_/¯
    amount = get_deposit_amount(soup)
    payee = get_deposit_payee(soup)

    if not (amount and payee):
        raise ValueError

    return Transaction(date=date, amount=amount, payee=payee)

    

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("-o", "--out", help="JSON file to write transactions to. If not specified, use stdout.")
    args = parser.parse_args()

    json_transactions = []
    with imaplib.IMAP4(port=1143) as conn:
        conn.login(username, bridge_password)
        conn.select()
        resp, withdrawal_emails = conn.search(None, '(SUBJECT "PNC")')
        if resp == "OK":
            print(resp, withdrawal_emails)

            idxs = withdrawal_emails[0].split()
            for idx in idxs:
                transaction = parse_withdrawal(conn, idx)
                json_transactions.append(convert_transaction(transaction))
        
        resp, deposit_emails = conn.search(None, '(SUBJECT "Deposit")')
        if resp == "OK":
            print(resp, deposit_emails)

            idxs = deposit_emails[0].split()
            for idx in idxs:
                transaction = parse_deposit(conn, idx)
                json_transactions.append(convert_transaction(transaction))

    if args.out:
        with open(args.out, "w") as outfile:
            json.dump(json_transactions, outfile)
    else:
        print(json.dumps(json_transactions))


if __name__ == "__main__":
    main()
