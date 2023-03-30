# Scheduled posting for Facebook pages

## Pre-requisites

### secrets.json file

Use FB's developer's graph explorer to get your User Token and Client ID/Secret.

Create a file `secrets.json` in this directory with contents:

```json
{
    "client_id": "YOUR_APP_CLIENT_ID",
    "client_secret": "YOUR_APP_CLIENT_SECRET",
    "fb_exchange_token": "YOUR_USER_ACCESS_TOKEN",
    "pages": {
        "page_name_1": {
            "page_id": "YOUR_PAGE_ID_1"
        },
        "page_name_2": {
            "page_id": "YOUR_PAGE_ID_2"
        }
    },
    "telegram": {
        "chat_id": "TELEGRAM_CHAT_ID_NR",
        "bot_token": "TELEGRAM_BOT_TOKEN"
    }
}
```

*"telegram" section is optional - just don't add it if you don't need it*

You can get your fb_exchange_token after login from https://developers.facebook.com/tools/explorer/. Select your app in Meta App and then select User Token -> Generate Access Token.

fb_exchange_token is used only once and long_access_token will replace it at the first run.
If you already have a long_access_token, add "long_access_token" key-value pair to secrets.json.
If your long_access_token has expired, just remove it from json and update fb_exchange_token.
TODO: fb_exchange_token is overwritten with long_access_token -> make them separate values

### outbox files (timetables)

To create a scheduled posts timetable, create any file or modify the existing ones in `outbox` folder:

```
page_name|YYYY-MM-DD|hh:mm:ss|Text description|Link
```
where "page_name" refers to entry in your secrets file.

## Usage

With parameters you can do instant post:

python3 autoposter.py pagename "Description" "http://www.example.com/link"

Without parameters tries to read outbox/* timetable files and schedule posts.

The main loop polls for changes in outbox/* files every 60 seconds. To keep the program running forever, add a scheduled post to somewhere far away in the future, like
```
page1|2033-01-01|12:00:00|the final post|http://www.example.com
```

TODO: Add watchdog to detect file changes.
