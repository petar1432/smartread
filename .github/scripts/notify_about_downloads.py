"""
Compares the download counts of all SmartRead releases with the counts from the last check,
and sends an e-mail when there are new downloads.

The counts from the last check are kept in the file given as the first argument.
The first check only remembers the counts and sends nothing.

Environment: GITHUB_TOKEN, GITHUB_REPOSITORY, GMAIL_ADDRESS, GMAIL_APP_PASSWORD, NOTIFY_EMAIL.
"""
import json
import os
import smtplib
import sys
import urllib.request
from email.message import EmailMessage
from pathlib import Path

READABLE_NAMES_OF_FILES = {
    'SmartRead-Windows.zip': 'Windows',
    'SmartRead-macOS-AppleSilicon.zip': 'Mac (Apple Silicon)',
    'SmartRead-macOS-Intel.zip': 'Mac (Intel)',
}


def main() -> None:
    path_of_last_counts = Path(sys.argv[1])
    current_counts = read_current_download_counts()
    last_counts = read_last_counts(path_of_last_counts)

    if last_counts is not None:
        new_downloads = find_new_downloads(current_counts, last_counts)
        if sum(new_downloads.values()) > 0:
            send_email_about(new_downloads, current_counts)

    path_of_last_counts.write_text(json.dumps(current_counts, indent=2, sort_keys=True) + '\n')


def read_current_download_counts() -> dict[str, int]:
    """Counts per release and file, for example {"v1.0.0/SmartRead-Windows.zip": 3}."""
    request = urllib.request.Request(
        f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/releases?per_page=100",
        headers={
            'Authorization': f"Bearer {os.environ['GITHUB_TOKEN']}",
            'Accept': 'application/vnd.github+json',
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        releases = json.load(response)
    return {
        f"{release['tag_name']}/{asset['name']}": asset['download_count']
        for release in releases
        for asset in release['assets']
    }


def read_last_counts(path_of_last_counts: Path) -> dict[str, int] | None:
    if not path_of_last_counts.exists():
        return None
    return json.loads(path_of_last_counts.read_text())


def find_new_downloads(current_counts: dict[str, int], last_counts: dict[str, int]) -> dict[str, int]:
    return {
        release_and_file: count - last_counts.get(release_and_file, 0)
        for release_and_file, count in current_counts.items()
        if count > last_counts.get(release_and_file, 0)
    }


def send_email_about(new_downloads: dict[str, int], current_counts: dict[str, int]) -> None:
    number_of_new_downloads = sum(new_downloads.values())
    message = EmailMessage()
    message['Subject'] = f'SmartRead: {number_of_new_downloads} {word_for_downloads(number_of_new_downloads)}'
    message['From'] = os.environ['GMAIL_ADDRESS']
    message['To'] = os.environ['NOTIFY_EMAIL']
    message.set_content(build_text_of_email(new_downloads, current_counts))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30) as mail_server:
        mail_server.login(os.environ['GMAIL_ADDRESS'], os.environ['GMAIL_APP_PASSWORD'])
        mail_server.send_message(message)


def build_text_of_email(new_downloads: dict[str, int], current_counts: dict[str, int]) -> str:
    lines = ['Nova preuzimanja od zadnje provjere:', '']
    for release_and_file, count in sorted(new_downloads.items()):
        lines.append(f'  {describe(release_and_file)}: +{count}')
    lines += ['', f'Ukupno preuzimanja svih verzija: {sum(current_counts.values())}', '']
    for release_and_file, count in sorted(current_counts.items()):
        lines.append(f'  {describe(release_and_file)}: {count}')
    lines += ['', 'https://github.com/petar1432/smartread/releases']
    return '\n'.join(lines)


def describe(release_and_file: str) -> str:
    release, file_name = release_and_file.split('/', 1)
    return f'{READABLE_NAMES_OF_FILES.get(file_name, file_name)} ({release})'


def word_for_downloads(number: int) -> str:
    """Croatian plural: 1 novo preuzimanje, 2-4 nova preuzimanja, 5+ novih preuzimanja."""
    if number % 10 == 1 and number % 100 != 11:
        return 'novo preuzimanje'
    if number % 10 in (2, 3, 4) and number % 100 not in (12, 13, 14):
        return 'nova preuzimanja'
    return 'novih preuzimanja'


if __name__ == '__main__':
    main()
