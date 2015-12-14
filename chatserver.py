#!/usr/bin/python

import sys

from twisted.internet import reactor, protocol
from twisted.internet.protocol import Protocol, ServerFactory

# TODO (server class)
class Behaviour(Protocol):

	def connectionMade(self):
		print("Adding client")
		self.factory.clients.append(self)

	def connectionLost(self, reason):
		print("Removing client")
		self.factory.clients.remove(self)

	def dataReceived(self, data):
		print("Data Received")
		for c in self.factory.clients:
			if(self != c):
				c.contact(data)

	def contact(self, message):
		self.transport.write(message + '\n')

def main():
	if not len(sys.argv) == 2:
		print('Usage: ' + sys.argv[0] + ' <tcp server port>')
		sys.exit(1)
	try:
		tcpPort = int(sys.argv[1])
	except ValueError:
		print(str(sys.argv[1]) + ' must be an integer.')
		sys.exit(1)
	# TODO (server configuration)
	factory = protocol.ServerFactory();
	factory.clients = []
	factory.protocol = Behaviour
	reactor.listenTCP(tcpPort, factory)
	reactor.run()


if __name__ == '__main__':
	main()
