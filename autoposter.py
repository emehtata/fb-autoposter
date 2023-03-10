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
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S')


def get_access_token(secrets):
    access_token_url = f"https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id={secrets['client_id']}&client_secret={secrets['client_secret']}&fb_exchange_token={secrets['fb_exchange_token']}"

    try:
        r = requests.get(access_token_url)
        data = json.loads(r.text)
        access_token = data['access_token']
        logging.debug(access_token)
    except Exception as e:
        logging.error(f"{r.text}, {e}")
        raise e

    return access_token


def get_page_access_token(secrets):
    page_access_url = f"https://graph.facebook.com/{secrets['page_id']}?fields=access_token&access_token={secrets['fb_exchange_token']}"
    try:
        r = requests.get(page_access_url)
        data = json.loads(r.text)
        access_token = data['access_token']
        logging.debug(access_token)
    except Exception as e:
        logging.error(f"{r.text}, {e}")
        raise e

    return access_token


def read_secrets():
    with open("secrets.json") as fp:
        secrets = json.load(fp)

    logging.debug(secrets)

    return secrets


def page_post(msg, secrets):
    page_id = secrets['page_id']
    page_access_token = secrets['page_access_token']

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


def read_timetables(folder):
    timetable = []
    files = [f for f in listdir(folder) if isfile(join(folder, f))]
    logging.debug(files)
    for f in files:
        logging.debug(f"Reading {folder}/{f}")
        with open(f"{folder}/{f}") as fp:
            lines = fp.readlines()

        for l in lines:
            post_date, post_time, post_msg, post_link = l.split('|')
            Y, M, D = post_date.split('-')
            h, m, s = post_time.split(':')
            date_time = datetime.datetime(
                int(Y), int(M), int(D), int(h), int(m), int(s))
            unixtime = time.mktime(date_time.timetuple())
            entry = {
                "time": unixtime,
                "msg": post_msg,
                "link": post_link
            }
            if unixtime > time.time():
                logging.debug(f"Adding: {date_time} {entry}")
                timetable.append(entry)
            else:
                logging.debug(f"Old post: {date_time} {entry}")

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


def convert_to_long_lived_token(secrets):
    '''
    curl -i -X GET "https://graph.facebook.com/{graph-api-version}/oauth/access_token?  
        grant_type=fb_exchange_token&          
        client_id={app-id}&
        client_secret={app-secret}&
        fb_exchange_token={your-access-token}"     
    '''
    convert_url = f"https://graph.facebook.com/16.0/oauth/access_token?grant_type=fb_exchange_token&client_id={secrets['client_id']}&client_secret={secrets['client_secret']}&fb_exchange_token={secrets['fb_exchange_token']}"
    try:
        logging.debug("Converting to long lived token")
        r = requests.get(convert_url)
        logging.debug(r.text)
    except Exception as e:
        logging.error(r.text)
        raise e

    if 'error' in json.loads(r.text):
        logging.warning(f"Token already extended?")

def main_loop(timetable, secrets):
    while len(timetable) > 0:
        logging.info(f"Posts remaining: {len(timetable)}")
        next_post = get_next_post(timetable)
        pause = next_post['time']-time.time()
        logging.debug(f"Sleeping {pause} seconds")
        time.sleep(pause)
        logging.debug(f"Now posting {next_post}")
        page_post(next_post, secrets)
        timetable = read_timetables('outbox')

    return


if __name__ == '__main__':
    args = sys.argv
    args.pop(0)
    logging.debug(f"{args}")

    secrets = read_secrets()
    secrets['fb_exchange_token'] = get_access_token(secrets)
    secrets['page_access_token'] = get_page_access_token(secrets)
    logging.info(secrets)
    convert_to_long_lived_token(secrets)
    if len(args) == 2:
        next_post = {
            'msg': args[0],
            'link': args[1]
        }
        page_post(next_post, secrets)
    else:
        timetable = read_timetables('outbox')
        main_loop(timetable, secrets)
