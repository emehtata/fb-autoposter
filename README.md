# Scheduled posting for Facebook pages

HOX! HUOM! OBS!

!!!! Strongly under development !!!!

## Pre-requisites

### secrets.json file

Create a file `secrets.json` in this directory with contents:

```json
{
    "client_id": "YOUR_APP_CLIENT_ID",
    "client_secret": "YOUR_APP_CLIENT_SECRET",
    "page_id": "YOUR_PAGE_ID",
    "fb_exchange_token": "YOUR_USER_ACCESS_TOKEN",
    "page_name_1": {
        "page_id": "YOUR_PAGE_ID_1"
    },
    "page_name_2": {
        "page_id": "YOUR_PAGE_ID_2"
    }
}
```

You can get your fb_exchange_token after login from https://developers.facebook.com/tools/explorer/. Select your app in Meta App and then select User Token -> Generate Access Token.

fb_exchange_token is used only once and long_access_token will replace it at the first run.
If you already have a long_access_token, add "long_access_token" key-value pair to secrets.json.
If your long_access_token has expired, just remove it from json and update fb_exchange_token.

### outbox files (timetables)

To create a scheduled posts timetable, create any file or modify the existing ones in `outbox` folder:

```
page_name|YYYY-MM-DD|hh:mm:ss|Text description|Link
```
where "page_name" refers to entry in your secrets file.

## Usage

With parameters:

python3 autoposter.py "Description" "http://www.example.com/link"

Without parameters tries to read outbox/* timetable files and schedule posts.