import sys
import os
from random import choice, randint, shuffle
from time import sleep
from InstagramAPI import InstagramAPI
import client as c
import methods as m

try:
    m.handleLog()

    api = InstagramAPI(c.USERNAME, c.PASSWORD)
    if api.login():
        m.addLog('OK   ', 'SUCCESSFUL CLIENT LOGIN')
        if not os.path.isfile('data/' + c.USERNAME + '.json'):
            data = {
                'prospects': {}
            }
            m.updateData(data)
        users = m.fetchProspects(api)

        shuffle(users)
        for user in users:
            m.addLog('OK   ', 'PROPSPECTING ON ' + user['username'])
            if m.action(api, user):
                wait = randint(c.SLEEP_MIN, c.SLEEP_MAX)
                m.addLog('OK   ', 'SLEEPING ' + repr(wait) + 's')
                sleep(wait)
    else:
        m.addLog('ERROR', 'COULDNT LOGIN')


except KeyboardInterrupt:
    m.addLog('OK   ', 'KEYBOARD INTERRUPT')
    sys.exit()