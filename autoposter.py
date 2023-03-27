#!/usr/bin/env python3

import json
import logging
import sys
import datetime
import time

from os import listdir
from os.path import isfile, join

import requests

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


def get_access_token(secrets):
    access_token_url = f"https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id={secrets['client_id']}&client_secret={secrets['client_secret']}&fb_exchange_token={secrets['fb_exchange_token']}"

    try:
        r = requests.get(access_token_url)
        data = json.loads(r.text)
        access_token = data['access_token']
        logging.debug(data)
    except Exception as e:
        logging.error(f"{r.text}, {e}")
        raise e

    return access_token


def get_page_access_token_to_secrets(secrets, page):
    page_access_url = f"https://graph.facebook.com/{secrets['pages'][page]['page_id']}?fields=access_token&access_token={secrets['fb_exchange_token']}"
    if not 'page_access_token' in secrets['pages'][page]:
        try:
            r = requests.get(page_access_url)
            data = json.loads(r.text)
            secrets['pages'][page]['page_access_token'] = data['access_token']
            logging.debug(data)
        except Exception as e:
            logging.error(f"{r.text}, {e}")
            raise e

    return secrets


def read_secrets():
    with open("secrets.json") as fp:
        secrets = json.load(fp)
        fp.close()

    logging.debug(secrets)

    return secrets


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
        logging.error(f"{r.text}, {e}")
        raise e


def read_timetables(folder, secrets):
    timetable = []
    files = [f for f in listdir(folder) if isfile(join(folder, f))]
    logging.debug(files)
    for f in files:
        logging.debug(f"Reading {folder}/{f}")
        with open(f"{folder}/{f}") as fp:
            lines = fp.readlines()

        for l in lines:
            page, post_date, post_time, post_msg, post_link = l.split('|')
            Y, M, D = post_date.split('-')
            h, m, s = post_time.split(':')
            date_time = datetime.datetime(
                int(Y), int(M), int(D), int(h), int(m), int(s))
            unixtime = time.mktime(date_time.timetuple())
            if unixtime > time.time():
                page_access_token = get_page_access_token_to_secrets(
                    secrets, page)['pages'][page]['page_access_token']
                entry = {
                    "page_id": secrets['pages'][page]['page_id'],
                    "page_access_token": page_access_token,
                    "time": unixtime,
                    "msg": post_msg,
                    "link": post_link
                }
                logging.debug(f"Adding: {date_time} {entry}")
                timetable.append(entry)
            else:
                logging.debug(f"Old post for {page}: {date_time}")

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


def get_long_lived_token(secrets):
    convert_url = f"https://graph.facebook.com/v16.0/oauth/access_token?grant_type=fb_exchange_token&client_id={secrets['client_id']}&client_secret={secrets['client_secret']}&fb_exchange_token={secrets['fb_exchange_token']}"
    try:
        if not 'long_access_token' in secrets:
            logging.debug("Converting to long lived token")
            r = requests.get(convert_url)
            if 'error' in json.loads(r.text):
                logging.warning(f"Token already extended?")
            logging.debug(r.text)
            secrets['long_access_token'] = json.loads(r.text)['access_token']
            return secrets
    except Exception as e:
        logging.error(r.text)
        raise e

    return secrets


def poll_for_changes(folder, secrets):
    while len(timetable) == 0:
        pause = 60
        timetable = read_timetables(folder, secrets)
        logging.debug(f"Waiting for changes. Sleeping {pause} seconds.")
        time.sleep(pause)

    return timetable


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
            logging.debug(f"Next post in {pause} seconds")
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

if __name__ == '__main__':
    args = sys.argv
    args.pop(0)
    logging.debug(f"{args}")
    if len(args) > 0 and ( args[0] == '--help' or args[0] == '-h' ):
        usage()
        sys.exit(0)
    folder = 'outbox'
    secrets = read_secrets()
    # Get your fb_exchange_token (User Token)
    # from https://developers.facebook.com/tools/explorer/
    secrets['fb_exchange_token'] = get_access_token(secrets)

    logging.info(secrets)
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
