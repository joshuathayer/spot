# spot

Simple actor model implementation for PyQt, inspired by [thespian](https://thespianpy.com/doc/), but much simpler.

Actors:

- have local state
- receive messages
- are able to create new actors
- are able to send messages to other actors

Any class with an `act` method as shown below can be an actor. Here's a simple actor which keeps track of how many times it's been sent a message, and tells the `sum` actor its count.

    class Counter:

        def __init__(self):
            self.count = 0

        def act(self, msg, tell, create):

            self.count += 1
            tell('sum', self.count)


See `example.py` for a working example.
