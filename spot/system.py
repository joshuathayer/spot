import uuid
import logging
import random
import collections
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, \
    QEvent, QRunnable, QThreadPool, QMutex

logger = logging.getLogger(__name__)

class Actor(QRunnable):
    done = pyqtSignal()

    def __init__(self, runnable, tell, create, done, name=None):
        super().__init__()

        if name is None:
            name = str(uuid.uuid4())

        self.setAutoDelete(False)
        self.runnable = runnable
        self.tell = tell
        self.create = create
        self.name = name
        self.done = done
        self.inbox = collections.deque()

    @pyqtSlot()
    def run(self):

        # blocks...
        if len(list(self.inbox)) > 0:
            self.runnable.act(self.inbox.pop(), self.tell, self.create)
        else:
            logger.warning("Unexpectedly ran an actor ({}) with an empty inbox.".format(self.name))
        # unblocked...

        self.done(self.name)

class ActorSystem(QObject):

    actor_event = pyqtSignal(object)

    def __init__(self, app):
        super().__init__()

        self.app = app
        self.actors = {}

        self.threads = QThreadPool()
        self.tickmutex = QMutex()

        self.running = set()

        self.actor_event.connect(self.event)

    def event(self, e):
        self.tick()
        return False

    def create_actor(self, actor_class, actor_name=None):
        actor = Actor(actor_class,
                      lambda t, m: self.tell(t, m),
                      lambda a: self.create_actor(a),
                      self.actor_done,
                      actor_name)

        name = actor.name

        if name in self.actors:
            logger.info("Replacing existing actor at {}".format(name))

        self.actors[name] = actor
        self.actor_event.emit(None)
        return actor

    def tell(self, target, message):
        # this can run in an arbitrary thread

        # we'll assume `appendLeft` is thread safe
        if target in self.actors:
            self.actors[target].inbox.appendleft(message)
        else:
            logger.info("Was asked to add to an actor which does not exist")

        self.actor_event.emit(None)

    def actor_done(self, name):
        self.running.remove(name)
        self.actor_event.emit(None)

    def tick(self):
        if self.tickmutex.tryLock():
            readys = list(filter(lambda v: True
                                 if len(v.inbox) > 0
                                 and v.name not in self.running
                                 else False, self.actors.values()))

            random.shuffle(readys)

            for actor in readys:
                self.running.add(actor.name)
                self.threads.start(actor)

            self.tickmutex.unlock()
        else:
            logger.info("Failed to get tick mutex")
