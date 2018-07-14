import client as c
from datetime import datetime, timedelta
from time import sleep
from random import choice, randint, shuffle
import os
import sys
import json

def handleLog():
    if not os.path.isfile('logs/' + c.USERNAME + '.log'):
        file = open('logs/' + c.USERNAME + '.log', 'w')
        file.write('------- NEW GROW ------- \n\n')
        file.close()
    else:
        file = open('logs/' + c.USERNAME + '.log', 'a')
        file.write('\n ------- NEW SESSION ------- \n\n')
        file.close()

def addLog(status, message):
    now = datetime.now()
    log = '[  ' + status + '  ] ' + now.strftime("%d-%m %H:%M:%S") + ' ' + message
    print(log)
    file = open('logs/' + c.USERNAME + '.log', 'a')
    file.write(log + '\n')
    file.close()

def getData():
    with open('data/' + c.USERNAME + '.json') as data_file:    
        data = json.load(data_file)
    return data

def updateData(data):
    with open('data/' + c.USERNAME + '.json', 'w') as file:
        json.dump(data, file, indent=2, sort_keys=True)

def fetchProspects(api):
    users = []
    data = getData()
    response = 0
    fetch_error = 1

    ##### CHOSE ACCOUNT TO FETCH FROM
    while response != 200:
        account = choice(c.FETCH_FROM)
        response = api.searchUsername(account)
    account_id = api.LastJson['user']['pk']
    addLog('OK   ', 'CHOSE ' + account + ' FOLLOWERS')

    ##### FETCH SELF FOLLOWERS
    addLog('OK   ', 'FETCHING FOLLOWERS...')
    while fetch_error != 0:
        try:
            followers = api.getTotalFollowers(account_id)
            fetch_error = 0
        except:
            addLog('ERROR', 'API ERROR ON FOLLOWERS FETCH - RETRYING')
            sleep(10 * fetch_error)
            fetch_error += 1
            if fetch_error == 4:
                addLog('ERROR', 'TOO MANY RETRIES - SLEEP 20 HOURS')
                sleep(72000)
    
    ##### CHOSE PROSPECTS
    for user in followers:
        if not user['is_private']:
            if user['username'] not in data['prospects']:
                users.append({
                    "username": user['username'],
                    "id": user['pk']
                })
    addLog('OK   ', 'FOUND ' + repr(len(users)) + ' POTENTIAL PROSPECTS')

    return users

def action(api, user):
    data = getData()
    post_id = ''
    fetch_error = 1
    while fetch_error != 0:
        try:
            response = api.getUserFeed(str(user['id']))
            fetch_error = 0
        except:
            addLog('ERROR', 'API ERROR ON FEED FETCH - RETRYING')
            sleep(10 * fetch_error)
            fetch_error += 1
            if fetch_error == 4:
                addLog('ERROR', 'TOO MANY RETRIES - SLEEP 20 HOURS')
                sleep(72000)
    if response == 200:

        if 'items' in api.LastJson:
            photos = api.LastJson['items']
        else:
            photos = []
        if photos:

            data['prospects'][user['username']] = {}
            data['prospects'][user['username']]['time'] = (datetime.now() - timedelta(minutes=5)).strftime(c.DATE_FMT)
            data['prospects'][user['username']]['followed_back'] = False

            ##### COMMENT
            if c.ACTION == 'comment' or c.ACTION == 'both':
                response = 0
                index = 0
                comment = constructComment()
                response = api.comment(str(photos[index]['pk']), comment)
                if response == 200:
                    addLog('OK   ', 'COMMENTED ' + comment)
                    data['prospects'][user['username']]['comment'] = comment
                    data['prospects'][user['username']]['photo'] = 'instagram.com/p/' + photos[index]['code']
                    data['prospects'][user['username']]['confirmed'] = False
                    data['prospects'][user['username']]['photo_id'] = photos[index]['pk']
                    # wait = randint(c.SLEEP_MIN, c.SLEEP_MAX)
                    # addLog('OK   ', 'SLEEPING ' + repr(wait) + 's')
                    # sleep(wait)
                else:
                    addLog('ERROR', 'COULDNT COMMENT')
                    return False

            ##### LIKES
            if c.ACTION == 'like' or c.ACTION == 'both':
                liked = []
                err = 0
                if len(photos) < c.MAX_LIKE:
                    maxLike = len(photos)
                    minLike = 1
                else:
                    maxLike = c.MAX_LIKE
                    minLike = c.MIN_LIKE
                for i in range(randint(minLike, maxLike)):
                    post = photos[i]
                    post_id = post['pk']
                    response = api.like(str(post_id))
                    if response == 200:
                        addLog('OK   ', 'LIKED ' + repr(i + 1) + ' PHOTO')
                        liked.append(post_id)
                        sleep(randint(1,4))
                    else:
                        addLog('ERROR', 'COULDNT LIKE PHOTO - ERROR ' + repr(response))
                        err += 1
                data['prospects'][user['username']]['liked'] = i - err


            updateData(data)
            return True
        else:
            addLog('OK   ', 'USER HAS NO PHOTO')
            return False
    else:
        addLog('ERROR', 'COULDNT FETCH USER FEED')
        return False

def checkLastAction(apiCheck, user):
    data = getData()
    ##### RETRIEVE COMMENT ON POST
    has_more_comments = True
    max_id = ''
    comments = []
    utc_timedelta = datetime.utcnow() - datetime.now()
    while has_more_comments:
        _ = apiCheck.getMediaComments(data['prospects'][user['username']]['photo_id'], max_id=max_id)
        if 'comments' in apiCheck.LastJson:
            for cmt in reversed(apiCheck.LastJson['comments']):
                comments.append(cmt)
        else:
            addLog('ERR', 'COULDNT FETCH COMMENTS')
            print(apiCheck.LastJson)
        has_more_comments = apiCheck.LastJson.get('has_more_comments', False)
        older_comment = comments[-1]
        dt = datetime.utcfromtimestamp(older_comment.get('created_at_utc', 0))
        until_time = (datetime.strptime(data['prospects'][user['username']]['time'], c.DATE_FMT) + utc_timedelta)
        if dt <= until_time:
            comments = [
                cmt
                for cmt in comments
                if datetime.utcfromtimestamp(cmt.get('created_at_utc', 0)) > until_time
            ]
            has_more_comments = False
        if has_more_comments:
            max_id = apiCheck.LastJson.get('next_max_id', '')
            sleep(1)
    found = False
    for cmt in comments:
        if data['prospects'][user['username']]['comment'] == cmt['text']:
            found = True
            break
    if found:
        data['prospects'][user['username']]['confirmed'] = True
        updateData(data)
        return True
    else:
        return False


def constructComment():
    comment = ''
    for i in range(len(c.SYNTAX)):
        comment += choice(c.SYNTAX[i + 1])
    return comment