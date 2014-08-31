#!/usr/bin/env python
# coding: utf-8

import os
import requests
from twitter import *
from twitter.api import TwitterHTTPError

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_OAUTH_TOKEN = os.getenv("GITHUB_OAUTH_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")


def shorten_url(long_url):
    params = {"access_token": os.getenv("BITLY_ACCESS_TOKEN"), "longUrl": long_url}
    r = requests.get("https://api-ssl.bitly.com/v3/shorten", params=params)
    json = r.json()
    data = json['data']
    return data['url']

def create_tweet_text(text, url):
    TEXT_LIMIT = 116 # 23 chars are reserved for url
    LIMIT = 140

    def join_text_and_url(text, url):
        return text + " " + url

    # first, shorten url
    if len(join_text_and_url(text, url)) > LIMIT:
        url = shorten_url(url)

    # shorten text if still over limit
    if len(join_text_and_url(text, url)) > LIMIT:
        over = len(text) - TEXT_LIMIT
        text = text[0:-1 * over - 1] + "…"

    return join_text_and_url(text, url)

def get_events():
    headers = {"Authorization": "token " + GITHUB_OAUTH_TOKEN}
    r = requests.get("https://api.github.com/users/" + GITHUB_USERNAME + "/received_events", headers=headers)
    events = r.json()
    event_list = []
    for event in events:
        ident = event['id']
        actor = event['actor']['login']
        event_type = event['type'][:-5] # ltrim 'Event'
        repo = event['repo']['name']
        summary = "[" + repo + "][" + event_type + "] " + actor + " / "
        url = ''
        payload = event['payload']
        if event_type == 'IssueComment' or event_type == 'CommitComment':
            summary += payload['comment']['body']
            url = payload['comment']['html_url']
        elif event_type == 'Issues':
            summary += payload['action'] + ":" + payload['issue']['title']
            url = payload['issue']['html_url']
        elif event_type == 'Delete':
            summary += 'Deleted ' + payload['ref_type'] + ' ' + payload['ref']
            url = 'https://github.com/' + repo
        elif event_type == 'Push':
            summary += "Pushed " + str(payload['size']) + " commits"
            url = 'https://github.com/' + repo
        elif event_type == 'Create':
            ref_type = payload['ref_type']
            if ref_type == "repository":
                summary += "Created repository"
            elif ref_type == "branch":
                summary += "Created branch " + payload['ref']
            elif ref_type == "tag":
                summary += "Created tag " + payload['ref']
            url = 'https://github.com/' + repo
        elif event_type == 'PullRequest':
            summary += payload['pull_request']['title']
            url = payload['pull_request']['html_url']
        elif event_type == 'PullRequestReviewComment':
            summary += payload['comment']['body']
            url = payload['comment']['html_url']
        elif event_type == 'Fork':
            url = payload['forkee']['html_url']
        elif event_type == 'Release':
            summary += payload['release']['body']
            url = payload['release']['html_url']
        elif event_type == 'Watch':
            summary += 'Started watching'
            url = 'https://github.com/' + repo
        elif event_type == 'Gollum':
            pages = payload['pages']
            action = pages[0]['action'] # edited or created
            page_name = pages[0]['page_name']
            summary += action.capitalize() + ' ' + page_name
            url = pages[0]['html_url']
        else:
            pass
        text = create_tweet_text(summary, url)
        event_list.append((int(ident), text))
    return event_list

def tweet(text):
    access_token_key = os.getenv("TWITTER_ACCESS_TOKEN_KEY")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    consumer_key = os.getenv("TWITTER_CONSUMER_KEY")
    consumer_secret = os.getenv("TWITTER_CONSUMER_SECRET")
    t = Twitter(
        auth=OAuth(access_token_key, access_token_secret, consumer_key, consumer_secret))
    t.statuses.update(
        status=text)

def write_position_file(ident):
    f = open(position_file, 'w')
    f.write(str(ident))
    f.close()

if __name__ == "__main__":
    position_file = "position.txt"
    if not os.path.exists(position_file):
        position_id = 0
    else:
        position_id = int(open(position_file).read())
    events = get_events()
    events.reverse()
    for ident, text in events:
        if ident > position_id:
            print(text)
            try:
                tweet(text)
            except TwitterHTTPError as e:
                message = str(e)
                if "Status is a duplicate" in message:
                    print("Status is a duplicate: " + text)
        write_position_file(ident)
