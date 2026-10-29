"""
E-mails the author how SmartRead was used today (sent at 23:00 Croatian time).
Reads the summary from the private usage server, with the secret key that only the author has.

Environment: STATS_URL, STATS_KEY, GMAIL_ADDRESS, GMAIL_APP_PASSWORD, NOTIFY_EMAIL.
"""
import json
import os
import smtplib
import urllib.request
from email.message import EmailMessage

NAMES_OF_PLATFORMS = {'win32': 'Windows', 'darwin': 'Mac', 'linux': 'Linux'}


def main() -> None:
    stats = read_stats()
    message = EmailMessage()
    message['Subject'] = (
        f"SmartRead danas: {stats['active_today']} aktivnih, "
        f"{stats['new_installations_today']} novih instalacija"
    )
    message['From'] = os.environ['GMAIL_ADDRESS']
    message['To'] = os.environ['NOTIFY_EMAIL']
    message.set_content(build_text_of_email(stats))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30) as mail_server:
        mail_server.login(os.environ['GMAIL_ADDRESS'], os.environ['GMAIL_APP_PASSWORD'])
        mail_server.send_message(message)


def read_stats() -> dict:
    request = urllib.request.Request(
        os.environ['STATS_URL'],
        headers={'x-stats-key': os.environ['STATS_KEY'], 'user-agent': 'smartread-usage-report'},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def build_text_of_email(stats: dict) -> str:
    return '\n'.join([
        f"Korištenje SmartReada za {stats['today']}:",
        '',
        f"  Aktivnih korisnika danas:     {stats['active_today']}  ({list_platforms(stats['active_today_by_platform'])})",
        f"  Novih instalacija danas:      {stats['new_installations_today']}",
        f"  Aktivnih jučer:               {stats['active_yesterday']}",
        f"  Aktivnih zadnjih 7 dana:      {stats['active_last_7_days']}",
        f"  Aktivnih zadnjih 30 dana:     {stats['active_last_30_days']}",
        f"  Instalacija ukupno:           {stats['installations_total']}",
        f"  Verzije (zadnjih 7 dana):     {list_groups(stats['active_last_7_days_by_version'])}",
        '',
        'Aktivan korisnik je instalacija koja je tog dana barem jednom pokrenuta.',
    ])


def list_platforms(groups: list[dict]) -> str:
    return ', '.join(f"{NAMES_OF_PLATFORMS.get(group['name'], group['name'])}: {group['number']}" for group in groups) or '-'


def list_groups(groups: list[dict]) -> str:
    return ', '.join(f"{group['name']}: {group['number']}" for group in groups) or '-'


if __name__ == '__main__':
    main()
