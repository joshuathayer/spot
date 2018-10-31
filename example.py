from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, \
    QVBoxLayout, QListWidget, QListWidgetItem

import spot.system
import logging
import time
import requests
import uuid
import random

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class Timer:
    def act(self, msg, tell, create):
        target = msg['target']
        target_msg = msg['target_msg']
        time.sleep(msg['sleep'])
        tell(target, target_msg)


class Counter:

    def __init__(self):
        self.count = 0

    def act(self, msg, tell, create):

        self.count += 1
        tell('fetcher', self.count)


class Fetcher:
    def act(self, msg, tell, create):
        req_id = str(uuid.uuid4())

        tell('receiver', {'req_id': req_id,
                          'action': 'newreq'})

        timed_actor = create(Timer())
        tell(timed_actor.name, {'sleep': 2,
                                'target': 'receiver',
                                'target_msg': {'req_id': req_id,
                                               'action': 'timeout'}})

        # simulate a slow connection
        time.sleep(random.randint(0, 3))

        response = requests.get("https://jsonplaceholder.typicode.com/todos/{}".format(msg))
        resp = response.json()

        tell('receiver', {'req_id': req_id,
                          'action': 'resp',
                          'resp': resp})


class Receiver:
    def __init__(self):
        self.current_reqs = {}

    def act(self, msg, tell, create):
        req_id = msg['req_id']
        action = msg['action']

        if action == 'newreq':
            self.current_reqs[req_id] = True

        elif action == 'timeout' and req_id in self.current_reqs:
            logger.info("Request timed out!")
            del self.current_reqs[req_id]

        elif action == 'resp' and req_id in self.current_reqs:
            del self.current_reqs[req_id]

            resp = msg['resp']

            tell('db', {'type': 'new-todo',
                        'body': resp})

            tell('item-list', {'type': 'new-todo',
                               'body': resp})
        else:
            logger.warn("Not sure what to do with {} {}".format(action, req_id))


# single point of DB mutation
class DB:
    def __init__(self):
        self.state = {}

    def act(self, msg, tell, create):
        msg_type = msg['type']
        if msg_type == 'new-todo':
            title = msg['body']['title']
            msg_id = msg['body']['id']

            self.state[msg_id] = title


class ItemList:
    def __init__(self, item_list):
        self.item_list = item_list

    def act(self, msg, tell, create):
        msg_type = msg['type']
        if msg_type == 'new-todo':
            title = msg['body']['title']

            QListWidgetItem(title, self.item_list)


app = QApplication([])

window = QWidget()
layout = QVBoxLayout()
get = QPushButton('Fetch Item')
item_list = QListWidget()

system = spot.system.ActorSystem(app)
system.create_actor(Counter(), 'counter')
system.create_actor(DB(), 'db')
system.create_actor(Fetcher(), 'fetcher')
system.create_actor(Receiver(), 'receiver')
system.create_actor(ItemList(item_list), 'item-list')

get.clicked.connect(lambda: system.tell('counter', "click!"))
layout.addWidget(get)
layout.addWidget(item_list)
window.setLayout(layout)
window.show()

app.exec_()
