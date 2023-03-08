# Scheduled posting for Facebook pages

## Pre-requisites

### secrets.json file

Create a file `secrets.json` in this directory with contents:

```
{
    "client_id": "YOUR_APP_CLIENT_ID",
    "client_secret": "YOUR_APP_CLIENT_SECRET",
    "page_id": "YOUR_PAGE_ID",
    "fb_exchange_token": "YOUR_USER_ACCESS_TOKEN",
    "app_token": "YOUR_APP_TOKEN"
}
```

### outbox files (timetables)

To create a scheduled posts timetable, create any file or modify the existing ones in `outbox` folder:

```
YYYY-MM-DD|hh:mm:ss|Text description|Link
```