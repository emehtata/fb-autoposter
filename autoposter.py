#!/usr/bin/env python3

import json
import logging
import sys
import datetime
import time
import requests
from os import environ
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from os import listdir
from os.path import isfile, join

logging_level = logging.INFO
if 'DEBUG' in environ:
    import debugpy
    logging_level = logging.DEBUG

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging_level,
    datefmt='%Y-%m-%d %H:%M:%S')


class Status:
    def __init__(self):
        self._error_msgs = []
        self.reset_errors()
        self._last_timetable_read_success = True

    def add_error(self, msg):
        self._error_msgs.append(msg)

    def reset_errors(self):
        self._error_msgs.clear()

    @property
    def errors(self):
        return len(self._error_msgs)

    @property
    def error_msgs(self):
        return self._error_msgs

    @property
    def last_timetable_read_success(self):
        return self._last_timetable_read_success

    @last_timetable_read_success.setter
    def last_timetable_read_success(self, new_state):
        self._last_timetable_read_success = new_state


class Secrets:
    def __init__(self, secrets_file):
        with open(secrets_file) as fp:
            data = json.load(fp)
            logging.info("Secrets read")
            self._client_id = data['client_id']
            self._client_secret = data['client_secret']
            self._fb_exchange_token = data['fb_exchange_token']
            self._pages = data['pages']
            self._telegram = False
            if 'telegram' in data:
                self._telegram_chat_id = data['telegram']['chat_id']
                self._telegram_bot_token = data['telegram']['bot_token']
                self._telegram = True
            self.get_access_token()

    @property
    def telegram_chat_id(self):
        return self._telegram_chat_id
    
    @property
    def telegram_bot_token(self):
        return self._telegram_bot_token

    @property
    def telegram(self):
        return self._telegram

    def get_access_token(self):
        access_token_url = f"https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id={self._client_id}&client_secret={self._client_secret}&fb_exchange_token={secrets['fb_exchange_token']}"

        try:
            r = requests.get(access_token_url)
            data = json.loads(r.text)
            self._access_token = data['access_token']
            logging.debug(data)
        except Exception as e:
            my_error(f"{r.text}, {e}")
            raise e

    def get_page_access_token(self, page):
        if not 'page_access_token' in self._pages[page]:
            page_access_url = f"https://graph.facebook.com/{self._pages[page]['page_id']}?fields=access_token&access_token={self._fb_exchange_token}"
            try:
                r = requests.get(page_access_url)
                data = json.loads(r.text)
                self._pages[page]['page_access_token'] = data['access_token']
                logging.debug(data)
            except Exception as e:
                my_error(f"{r.text}, {e}")
                raise e

    def get_long_lived_token(self):
        try:
            convert_url = f"https://graph.facebook.com/v16.0/oauth/access_token?grant_type=fb_exchange_token&client_id={self._client_id}&client_secret={self._client_secret}&fb_exchange_token={self._fb_exchange_token}"

            if not 'long_access_token' in secrets:
                logging.debug("Converting to long lived token")
                r = requests.get(convert_url)
                if 'error' in json.loads(r.text):
                    logging.warning(f"Token already extended?")
                logging.debug(r.text)
                self._long_access_token = json.loads(r.text)['access_token']
        except Exception as e:
            my_error(r.text)
            raise e

def page_post(msg):
    page_id = msg['page_id']
    page_access_token = msg['page_access_token']

    post_url = f"https://graph.facebook.com/{page_id}/feed"
    payload = {
        'message': msg['msg'],
        'link': msg['link'],
        'access_token': page_access_token
    }
    try:
        logging.debug(payload)
        r = requests.post(post_url, data=payload)
        logging.info(r.text)
    except Exception as e:
        my_error(f"{r.text}, {e}")
        raise e


def read_timetables(folder, secrets):
    timetable = []
    files = [f for f in listdir(folder) if isfile(join(folder, f))]
    logging.debug(files)
    status.reset_errors()
    for f in files:
        logging.debug(f"Reading {folder}/{f}")
        with open(f"{folder}/{f}") as fp:
            lines = fp.readlines()

        if len(lines) == 0:
            logging.warning(f"No lines found in {folder}/{f}")
            continue

        lnr = 0
        for l in lines:
            lnr += 1
            l = l.strip()
            try:
                page, post_date, post_time, post_msg, post_link = l.split('|')
                Y, M, D = post_date.split('-')
                h, m, s = post_time.split(':')
                date_time = datetime.datetime(
                    int(Y), int(M), int(D), int(h), int(m), int(s))
                unixtime = time.mktime(date_time.timetuple())
                if unixtime > time.time():
                    entry = {
                        "page_id": secrets.pages[page]['page_id'],
                        "page_access_token": secrets.page_access_token(page),
                        "time": unixtime,
                        "msg": post_msg,
                        "link": post_link
                    }
                    logging.debug(f"Adding: {date_time} {entry}")
                    timetable.append(entry)
                else:
                    logging.debug(f"Old post for {page}: {date_time}")
            except Exception as e:
                logging.error(
                    f"Failed to parse timetable line {lnr}: {l} - {e}")
                status.add_error(f"ERROR parsing {f}:{lnr}: {l}")

    if status.errors > 0 and status.last_timetable_read_success == True:
        send_telegram_msg(
            f"Failed to parse timetables!\n{status.error_msgs}", secrets)
        status.last_timetable_read_success = False
    elif status.errors == 0 and status.last_timetable_read_success == False:
        send_telegram_msg(
            f"Timetables OK!", secrets)
        status.last_timetable_read_success = True

    timetable = sorted(timetable, key=lambda d: d['time'])

    logging.debug(timetable)

    return timetable


def get_next_post(timetable):
    next_post = None
    timenow = time.time()
    mintime = 999999999
    for t in timetable:
        if t['time']-timenow < mintime:
            mintime = t['time']-timenow
            next_post = t

    logging.debug(
        f"Next post at {datetime.datetime.fromtimestamp(next_post['time'])}: {next_post}")
    return next_post


def my_error(msg):
    logging.error(msg)
    send_telegram_msg(
        f"ERROR {msg}", secrets)




def main_loop(folder, secrets):
    timetable = read_timetables(folder, secrets)
    while len(timetable) > 0:
        logging.info(f"Posts remaining: {len(timetable)}")
        next_post = get_next_post(timetable)
        pause = next_post['time']-time.time()
        if pause < 60:
            logging.debug(f"Sleeping {pause} seconds")
            time.sleep(pause)
            logging.debug(f"Now posting {next_post}")
            page_post(next_post)
        else:
            logging.info(f"Next post in {pause} seconds")
            time.sleep(60)

        logging.debug(f"Now reading timetables from {folder}")
        timetable = read_timetables(folder, secrets)

    return


def usage():
    help_text = '''
       With parameters you can do instant post:
       python3 autoposter.py pagename "Description" "http://www.example.com/link"
       Without parameters tries to read outbox/* timetable files and schedule posts.
       Check README.md for more information.
    '''

    print(help_text)


def send_telegram_msg(msg, secrets):
    if secrets.telegram:
        chatID = secrets.telegram_chat_id
        apiToken = secrets.telegram_bot_token
        apiURL = f'https://api.telegram.org/bot{apiToken}/sendMessage'
        try:
            response = requests.post(
                apiURL, json={'chat_id': chatID, 'text': msg})
            logging.info(response.text)
        except Exception as e:
            logging.error(e)
    else:
        logging.debug("No Telegram bot defined in secrets.")


if __name__ == '__main__':
    if 'DEBUG' in environ:
        debugpy.listen(5678)
        debugpy.wait_for_client()
    args = sys.argv
    args.pop(0)
    status = Status()
    logging.debug(f"{args}")
    if len(args) > 0 and (args[0] == '--help' or args[0] == '-h'):
        usage()
        sys.exit(0)
    folder = 'outbox'
    secrets = read_secrets()
    # Get your fb_exchange_token (User Token)
    # from https://developers.facebook.com/tools/explorer/
    secrets['fb_exchange_token'] = get_access_token(secrets)

    logging.debug(secrets)
    secrets = get_long_lived_token(secrets)
    secrets['fb_exchange_token'] = secrets['long_access_token']
    with open("secrets.json", "w") as fp:
        fp.write(json.dumps(secrets, indent=4))

    if len(args) == 3:
        page = args[0]
        secrets = get_page_access_token_to_secrets(secrets, page)
        next_post = {
            'page': page,
            'msg': args[1],
            'link': args[2],
            'page_id': secrets['pages'][page]['page_id'],
            'page_access_token': secrets['pages'][page]['page_access_token']
        }
        page_post(next_post)
    else:
        main_loop(folder, secrets)
