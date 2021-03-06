#!/usr/bin/python

import sys

from twisted.internet import reactor, protocol
from twisted.internet.protocol import Protocol, ServerFactory


class server(Protocol):

	def connectionMade(self):
	# Ajoutelenouveauclientdanslal i s t es e l f . factory . clients
		#ajoute le client à la liste
		self.factory.clients.append(self)
		#message (gentil) de connexion
		self.transport.write("Tu es connecté ma couille\r\n")


	def connectionLost(self,reason):
	# Retirelenouveauclientdelalistese l f . factory . clients
		#supprime le client de la liste
		self.factory.clients.remove(self)

	def dataReceived(self,data):
	# Transfertladatasurchaqueclients
	# On peutcontacterunclientautraversdesasockets e l f . transport
		#on récupère la ligne et on l'affiche sur le serveur.
		line = data.rstrip("\r\n")
		print line
		#On parcourt tous les clients de la liste
		for c in self.factory.clients:
			#Si le client n'est pas lui même alors on affiche le message (évite l'echo)
			if not self == c:
				c.messsage(line)
			#Quand un client écrit QUIT alors la connexion est perdue
			elif line == "QUIT":
				self.transport.loseConnection()

	#création d'une fonction qui écrit chez le client
	def messsage(self, line):
		self.transport.write(line+'\n')





def main():
	if not len(sys.argv) == 2:
		print('Usage: ' + sys.argv[0] + ' <tcp server port>')
		sys.exit(1)
	try:
		tcpPort = int(sys.argv[1])
	except ValueError:
		print(str(sys.argv[1]) + ' must be an integer.')
		sys.exit(1)
	
	#création serveur vide
	factory = protocol.ServerFactory()
	#création tableau client
	factory.clients = []
	#utilisation de notre serveur
	factory.protocol=server

	#spécification du port d'écoute et du serveur + lancer le moteur
	reactor.listenTCP(tcpPort,factory)
	reactor.run()


if __name__ == '__main__':
	main()

#! /usr/bin/python

# Written by Vincent Autefage

import os, os.path, sys, time, signal, hashlib, threading, code

sys.path.append('/net/ens/vince/dht')

from twisted.internet import reactor, protocol, defer
from twisted.internet.protocol import Protocol, ServerFactory, ClientCreator
from entangled.node import EntangledNode as KademliaNode

share = None

class FileServer(Protocol):
	'''File server class'''
	def dataReceived(self, data): # Called when a data (required file) is received from a client
		request = data.strip()
		for entry in os.listdir(self.factory.sharePath):
			 if entry == request:
				fullPath = os.path.join(self.factory.sharePath, request)
				f = open(fullPath, 'r')
				buf = f.read()
				self.transport.write(buf)
				f.close()
				break
		self.transport.loseConnection()


class FileGetter(Protocol):
	'''File client class'''
	def connectionMade(self): # Called when a client enables a connection
		self.buffer = ''
		self.filename = ''
		self.dest = ''
		
	def requestFile(self, filename, dest): # Sets the download parameters (desired file and destination)
		self.filename = filename
		self.transport.write(filename + '\r\n')
		self.dest = dest

	def dataReceived(self, data): # Called when a data is received from the server
		self.buffer += data
	
	def connectionLost(self, reason): # Called when the connection with the server is done
		if len(self.buffer) == 0:
			 gprint("An error occurred: file could not be retrieved.")
			 return
		f = open(self.dest, 'w')
		f.write(self.buffer)
		f.close()
		gprint('Done.')


class FileShare():
	'''Main DHT control class'''
	def __init__(self, node, port): # Initialization
		print('Building DHT node...')
		self.node = node
		self.port = port
		self.files = []
		print('Launching file server...')
		self.factory = ServerFactory()
		self.factory.protocol = FileServer
		self.factory.sharePath = '.'
		reactor.listenTCP(self.port, self.factory)

	def join(self, boostrap): # Joins another DHT network node identified by the tuple <boostrap>
		print('Joining ' + str(boostrap) + '...')
		node.joinNetwork(boostrap)

	def start(self): # Starts the event-driven framework loop
		print('Running network daemon...')
		reactor.run()

	def stop(self): # Cleans DHT entries and stops the event-driven framework loop
		gprint('Stopping network daemon...')
		self.clean()
		reactor.stop()
		self.transport.loseConnection()

	def errcallback(orself, failure): # Genereic error callback handler
		gprint('An error occurred: ' + failure.getErrorMessage())

	def search(self, keyword): # Retreives DHT keys similar to <keyword>
		gprint('Searching for : ' + str(keyword))
		h = hashlib.sha1()
		h.update(keyword)
		key = h.digest()
		df = self.node.iterativeFindValue(key)
		df.addErrback(self.errcallback)
		def ok(result) :
			if isinstance(result,dict):
				gprint (keyword + " found . ")
			else :
				gprint ("Cannotfind" + keyword)
		df.addCallback(ok)



	
	def publish(self, path): # Publishes new DHT entries from the files located in the directory <path>
		files = list()
		#cmp = 1
		if not os.path.exists(path):
			gprint(str(path) + ' does not exist')
			return
		self.files = list()
		self.factory.sharePath = path
		gprint('Publishing the directory ' + str(path))
		for entry in os.listdir(path):
			if os.path.isfile(os.path.join(path, entry)):
				files.append(entry)
		files.sort()
		def publishNextFile(result=None):
			filename = files.pop()
			h = hashlib.sha1()
			h.update(filename)
			key = h.digest()
			df = self.node.iterativeStore(key,self.node.id)
			self.files.append(filename)
			if files:
				 #cmp = cmp+1
				df.addCallback(publishNextFile)
				df.addErrback(self.errcallback)
			else:
				gprint("number of file :")
				return
		publishNextFile()
	
	def clean(self): # Deletes own DHT entries
		#cmp = 1
		gprint('Cleaning DHT entries of ' + str(self.factory.sharePath))
		self.factory.sharePath = '.'
		def cleanNextFile(result=None):
			filename = self.files.pop()
			h = hashlib.sha1()
			h.update(filename)
			key = h.digest()
			df = self.node.iterativeDelete(key)
			if self.files:
				#cmp = cmp+1
				df.addCallback(cleanNextFile)
				df.addErrback(self.errcallback)
			else:
				gprint("number of file deleted :")
				return
		cleanNextFile()

	def download(self, filename): # Downloads a file from a node of the DHT
		gprint('Hashing ' + str(filename))
		h = hashlib.sha1()
		h.update(filename)
		key = h.digest()
		def getTargetNode(result):
			gprint('Looking for holder of ' + str(filename))
			targetNodeID = None
			df = None
			try:
				targetNodeID = result[key]
			except Exception:
				gprint('Cannot find ' + str(filename))
				pass
			if targetNodeID:
				df = self.node.findContact(targetNodeID)
			return df
		def getFile(protocol):
			gprint('Downloading ' + str(filename) + ' in ' + str(self.factory.sharePath))
			if protocol != None:
				protocol.requestFile(filename, os.path.join(self.factory.sharePath,filename))
		def connectToPeer(contact):
			if contact == None:
				gprint(filename + ' could not be retrieved. The host that published this file is no longer on-line.')
			else:
				gprint('Contacting holder of ' + str(filename))
				c = ClientCreator(reactor, FileGetter)
				df = c.connectTCP(contact.address, contact.port)
				return df
		df = self.node.iterativeFindValue(key)
		df.addCallback(getTargetNode)
		df.addCallback(connectToPeer)
		df.addCallback(getFile)
		df.addErrback(self.errcallback)

	def update(self): # Updates DHT entries from the own shared directory
		path = self.factory.sharePath
		self.publish(path)


def gprint(line): # Prints <line> on the Daemon and Client outputs
	print(str(line))
	if DHTCom.transport:
		DHTCom.transport.write(str(line) + "\n")



class DHTCom(Protocol):
	'''DHT Daemon remote controller'''
	transport = None
	def connectionMade(self): # Called when a client enables a connection
		print("New Connection.")
		if len(self.factory.clients) == 0:
			self.factory.clients.append(self)
			DHTCom.transport = self.transport
			gprint("Connection accepted.")
		else:
			gprint("Connection rejected.")
			self.transport.loseConnection()
		
	def dataReceived(self, data): # Called when a data (required command) is received from a client
		if not data.rstrip().rstrip("\n"):
			return
		gprint('Order : ' + data.rstrip().rstrip("\n\r"))
		commandParts = data.rstrip().rstrip("\n\r").split()
		command = commandParts[0].lower()
		args = commandParts[1:]
		if command == 'halt':
			share.stop()
		elif command == 'check':
			gprint(str(args))
		elif command == 'search' and args:
			share.search(args[0])
		elif command == 'update':
			share.update()
		elif command == 'download' and args:
			share.download(args[0])
		elif command == 'publish' and args:
			share.publish(args[0])
		elif command == 'clean':
			share.clean()
		elif command == 'help': # QUESTION 11 : creation de la commande help
			gprint("please enter commands halt,check,search,update,download,publish,clean\r\n") 
		else:
			gprint(str(command) + " is unknown")
		
	def connectionLost(self, reason): # Called when a connection with a client is done
		if not self in self.factory.clients:
			return
		self.factory.clients.remove(self)
		gprint("Connection done.")
		DHTCom.transport = None


if __name__ == '__main__':
	if len(sys.argv) < 3:
		print('Usage: ' + sys.argv[0] + ' <remote tcp server> <udp port> [<boostrap node ip><bootstrap node port>]')
		sys.exit(1)
	try:
		tcpPort = int(sys.argv[1])
		udpPort = int(sys.argv[2])
	except ValueError:
		print(str(sys.argv[1]) + ' must be an integer value.')
		print(str(sys.argv[2]) + ' must be an integer value.')
		sys.exit(1)
	
	boostrap = None
	if len(sys.argv) == 5:
		boostrap = [(sys.argv[3], int(sys.argv[4]))]

	node = KademliaNode(udpPort=udpPort, dataStore=None)
	share = FileShare(node, udpPort)
	share.join(boostrap)

	factory = protocol.ServerFactory()
	factory.protocol = DHTCom
	factory.clients = []
	reactor.listenTCP(tcpPort,factory)
	share.start()
	sys.exit(0)
	gprint('Halted.')
