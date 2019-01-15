from bs4 import BeautifulSoup
import requests
import datetime
import calendar
import json
import logging
import os
import sys
import urllib.parse as urlparse
import pytz
import hmac
import hashlib

URL_MENU = 'http://www.aramarkcafe.com/layouts/canary_2015/locationhome.aspx?locationid=4386&pageid=20&stationID=-1'
LOGGER = logging.getLogger()
if os.getenv('logging_level', 'info') == 'debug':
    LOGGER.setLevel(logging.DEBUG)
else:
    LOGGER.setLevel(logging.INFO)

SIGNING_SECRET = os.getenv('signing_secret', '')


def parse_station(raw_station):
    LOGGER.debug('Starting parse_station')
    details = raw_station.find_all('div', {'class': 'noNutritionalLink'})
    side = raw_station.find(
        'span', {'class': 'menuRightDiv_li_p'}).get_text().strip()
    if len(details) != 2:
        LOGGER.debug(
            'Invalid number of station details, expected 2 found {}'.format(len(details)))
        return None, None, None
    entree = details[0].get_text().strip()
    # calories = details[1].get_text().strip()
    return {'title': entree, 'text': side}


def parse_daily_menu(raw_column):
    stations = raw_column.find_all('ul')
    day = raw_column.find('h1')
    if 0 == len(stations) or None == day:
        return None, None
    return_items = []
    for raw_station in stations:
        items = raw_station.find_all('li')
        for raw_item in items:
            return_items.append(parse_station(raw_item))
    return day.get_text(), return_items


def parse_weekly_menu():
    try:
        response = requests.get(URL_MENU)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as ex:
        LOGGER.error('Failed to get website info. {}'.format(ex))
        return None
    raw_columns = soup.find_all('div', {'class': 'foodMenuDayColumn'})
    if 0 == len(raw_columns):
        LOGGER.debug('No columns found')
        return None
    weekly_menu = {}
    for column in raw_columns:
        day, menu = parse_daily_menu(column)
        if day and menu:
            weekly_menu[day] = menu
    return weekly_menu


def get_todays_menu(day_of_week):
    full_menu = parse_weekly_menu()
    if day_of_week in full_menu:
        return full_menu[day_of_week]
    else:
        return {'text': 'No menu items available today'}

def get_day_of_week():
    tz = pytz.timezone('US/Pacific')
    today = tz.localize(datetime.datetime.now())
    day_of_week = calendar.day_name[today.today(
    ).astimezone(pytz.timezone('US/Pacific')).weekday()]
    return day_of_week


def get_slack_command(event):
    search_query = None
    if 'body' in event and event['body']:
        commands = event['body'].split('&')
        for command in commands:
            if command.startswith('text='):
                search_query = command.split('=')[1].lower()
    return search_query.lower()


def check_validity(event):
    if not 'headers' in event or not 'body' in event:
        return False
    headers = event['headers']
    if not 'X-Slack-Request-Timestamp' in headers or not 'X-Slack-Signature' in headers:
        return False

    ts = headers['X-Slack-Request-Timestamp']
    sig = headers['X-Slack-Signature']
    base_string = bytes('{}:{}:{}'.format('v0', ts, event['body']), 'utf-8')
    secret = bytes(SIGNING_SECRET, 'utf-8')
    signed_string = 'v0={}'.format(hmac.new(secret, base_string,
                                            hashlib.sha256).hexdigest())
    return hmac.compare_digest(signed_string, sig)


def lambda_handler(event, context):
    LOGGER.debug(event)

    if not check_validity(event):
        return {
            'statusCode': 401,
            'body': json.dumps({'text': 'Unauthorized'})
        }

    office = get_slack_command(event)
    if None == office or not 'sc' == office:
        return {
            'statusCode': 200,
            'body': json.dumps({'text': 'Incorrect usage. Correct format is `/lunch [office]`\n*Note* Only the Santa Clara office is currently supported'})
        }

    menu = None
    LOGGER.debug('Getting todays schedule')
    day_of_week = get_day_of_week()
    if day_of_week == 'Sunday' or day_of_week == 'Saturday':
        return {
            'statusCode': 200,
            'body': json.dumps({'text': 'The cafeteria is closed on the weekends'})
        }

    LOGGER.debug('Today is {}'.format(day_of_week))
    menu = get_todays_menu(day_of_week)

    if None == menu:
        menu = [{
            'title': 'Failed to get menu options',
            'text': 'There was an error retrieving the menu options, please try again later',
            'color': 'danger'
        }]

    menu.append({'title': 'Click here for the full menu', 'title_link': URL_MENU})
    return {
        'statusCode': 200,
        'body': json.dumps({'text': 'Todays menu options',
                            'attachments': menu})
    }


if __name__ == '__main__':
    event = {'resource': '/lunch-bot', 'path': '/lunch-bot', 'httpMethod': 'POST', 'headers': {'Accept': 'application/json,*/*', 'Accept-Encoding': 'gzip,deflate', 'CloudFront-Forwarded-Proto': 'https', 'CloudFront-Is-Desktop-Viewer': 'true', 'CloudFront-Is-Mobile-Viewer': 'false', 'CloudFront-Is-SmartTV-Viewer': 'false', 'CloudFront-Is-Tablet-Viewer': 'false', 'CloudFront-Viewer-Country': 'US', 'Content-Type': 'application/x-www-form-urlencoded', 'Host': 'vfoqswde9f.execute-api.us-east-1.amazonaws.com', 'User-Agent': 'Slackbot 1.0 (+https://api.slack.com/robots)', 'Via': '1.1 9742923607374c982a5b7e9258144eab.cloudfront.net (CloudFront)', 'X-Amz-Cf-Id': 'K9l7Rsn_8CqTNchjulPrSoTSxK-ccZQfUi8ZEnRYFQGPodEU1gChpw==', 'X-Amzn-Trace-Id': 'Root=1-5c330b1c-a667f0dc4a3ac94ea43f64ff', 'X-Forwarded-For': '34.238.168.63, 70.132.60.89', 'X-Forwarded-Port': '443', 'X-Forwarded-Proto': 'https', 'X-Slack-Request-Timestamp': '1546849052', 'X-Slack-Signature': 'v0=e2f87134d24f6fc361926ce07575dda137ce73ff6f51c471cf72e07bccc18f47'}, 'multiValueHeaders': {'Accept': ['application/json,*/*'], 'Accept-Encoding': ['gzip,deflate'], 'CloudFront-Forwarded-Proto': ['https'], 'CloudFront-Is-Desktop-Viewer': ['true'], 'CloudFront-Is-Mobile-Viewer': ['false'], 'CloudFront-Is-SmartTV-Viewer': ['false'], 'CloudFront-Is-Tablet-Viewer': ['false'], 'CloudFront-Viewer-Country': ['US'], 'Content-Type': ['application/x-www-form-urlencoded'], 'Host': ['vfoqswde9f.execute-api.us-east-1.amazonaws.com'], 'User-Agent': ['Slackbot 1.0 (+https://api.slack.com/robots)'], 'Via': ['1.1 9742923607374c982a5b7e9258144eab.cloudfront.net (CloudFront)'], 'X-Amz-Cf-Id': ['K9l7Rsn_8CqTNchjulPrSoTSxK-ccZQfUi8ZEnRYFQGPodEU1gChpw=='], 'X-Amzn-Trace-Id': [
        'Root=1-5c330b1c-a667f0dc4a3ac94ea43f64ff'], 'X-Forwarded-For': ['34.238.168.63, 70.132.60.89'], 'X-Forwarded-Port': ['443'], 'X-Forwarded-Proto': ['https'], 'X-Slack-Request-Timestamp': ['1546849052'], 'X-Slack-Signature': ['v0=e2f87134d24f6fc361926ce07575dda137ce73ff6f51c471cf72e07bccc18f47']}, 'queryStringParameters': None, 'multiValueQueryStringParameters': None, 'pathParameters': None, 'stageVariables': None, 'requestContext': {'resourceId': '6rtbug', 'resourcePath': '/lunch-bot', 'httpMethod': 'POST', 'extendedRequestId': 'TH6scFTIoAMFxZw=', 'requestTime': '07/Jan/2019:08:17:32 +0000', 'path': '/prod/lunch-bot', 'accountId': '950747459100', 'protocol': 'HTTP/1.1', 'stage': 'prod', 'domainPrefix': 'vfoqswde9f', 'requestTimeEpoch': 1546849052458, 'requestId': 'ae6f195a-1254-11e9-a7bf-cd20761b0d9e', 'identity': {'cognitoIdentityPoolId': None, 'accountId': None, 'cognitoIdentityId': None, 'caller': None, 'sourceIp': '34.238.168.63', 'accessKey': None, 'cognitoAuthenticationType': None, 'cognitoAuthenticationProvider': None, 'userArn': None, 'userAgent': 'Slackbot 1.0 (+https://api.slack.com/robots)', 'user': None}, 'domainName': 'vfoqswde9f.execute-api.us-east-1.amazonaws.com', 'apiId': 'vfoqswde9f'}, 'body': 'token=3pswrMrRwi6sjJKLT0bm89ti&team_id=T9182B16E&team_domain=malwarebytes&channel_id=D99LHUB0C&channel_name=directmessage&user_id=U979JB7SM&user_name=dcollins&command=%2Flunch&text=sc&response_url=https%3A%2F%2Fhooks.slack.com%2Fcommands%2FT9182B16E%2F517761343123%2F8yhIuVyd2f9o0G5qjngI5nwZ&trigger_id=517761343155.307274375218.27d87d2e327cc17bae39cdca97f1c15b', 'isBase64Encoded': False}
    print(lambda_handler(event, None))
