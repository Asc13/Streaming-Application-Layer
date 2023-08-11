import sys, time, threading, socket
from random import randint
import re


sys.path.insert(0, '../Shared')
from FloodPacket import FloodPacket
from RtspPacket import RtspPacket
from RoutingTable import RoutingTable
from OkPacket import OkPacket


class OttWorker:

	SETUP = 'SETUP'
	PLAY = 'PLAY'
	PAUSE = 'PAUSE'
	TEARDOWN = 'TEARDOWN'


	floodPort = 5005
	regPort = 5006
	okPort = 5007
	floodAckPort = 5008
	regAckPort = 5009
	okAckPort = 5010
	rtspPort = 5011
	rtspAckPort = 5012
	rtpPort = 16384


	def __init__(self, name, address, bootstrap):
		self.routingTable = RoutingTable()
		self.name = name
		self.address = address
		self.bootstrap = bootstrap



	def run(self):
		self.openRegSender()
		self.openRegAckReceiver()
	
		self.sendRegistries()

		self.openOkSender()
		self.openOkReceiver()
		self.openOkAckReceiver()
		self.openOkAckSender()

		self.openFloodSender()
		self.openFloodReceiver()
		self.openFloodAckReceiver()
		self.openFloodAckSender()

		self.openRtspSender()
		self.openRtspReceiver()
		self.openRtspAckReceiver()
		self.openRtspAckSender()

		self.openRtpSender()
		self.openRtpReceiver()

		self.receiveOk()
		self.sendOk()
		self.handleFlood()
		self.handleRtsp()
		threading.Thread(target = self.handleRtp).start()



	''' INITIALIZATION '''

	def openRegSender(self):
		self.regSender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


	def openRegAckReceiver(self):
		self.regAckReceiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   
		self.regAckReceiver.bind((self.address, self.regAckPort))


	def sendRegistries(self):
		acked = False
		
		while not acked:
			self.regSender.sendto((self.name + ' ' + self.address).encode('utf-8'), (self.bootstrap, self.regPort))
		
			try:
				neighboors, _ = self.regAckReceiver.recvfrom(1024)

				if neighboors:
					self.routingTable.appendNeighboors(re.split(r'\n', neighboors.decode('utf-8')))
					self.routingTable.createTable()

			except:
				pass

			else:
				if neighboors:
					acked = True

	
	def openOkReceiver(self):
		self.okReceiver = {}

		for binding in self.routingTable.getBindings():
			
			receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   
			receiver.bind((binding, self.okPort))
			receiver.settimeout(1)
			self.okReceiver[binding] = receiver

	
	def openOkSender(self):
		self.okSender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	
	def openOkAckReceiver(self):
		self.okAckReceiver = {}

		for binding in self.routingTable.getBindings():
			
			receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   
			receiver.bind((binding, self.okAckPort))
			receiver.settimeout(1)
			self.okAckReceiver[binding] = receiver

	
	def openOkAckSender(self):
		self.okAckSender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


	def sendOk(self):
		for neighboor in self.routingTable.getNeighboors():
			packet = OkPacket()
			packet.encode(int(re.sub(r'O', r'', self.name)),
						  self.routingTable.getBinding(neighboor).encode('utf-8'))

			threading.Thread(target = self.okSenderHandler, args = (packet.getPacket(), neighboor, )).start()


	def receiveOk(self):
		for binding in self.routingTable.getBindings():
			threading.Thread(target = self.okReceiverHandler, args = (binding, )).start()


	def okSenderHandler(self, packet, neighboor):
		while True:

			acked = False
			while not acked:
			
				self.okSender.sendto(packet, (neighboor, self.okPort))
				
				try:
					receiver = self.okAckReceiver.get(self.routingTable.getBinding(neighboor))
					
					data, _ = receiver.recvfrom(1024)
					
					if data:
						data = data.decode('utf-8')

				except socket.timeout:
					self.routingTable.updateNeighboor(neighboor, 'OFF')

					if self.routingTable.isOrigin(neighboor):
						self.routingTable.resetTable()

						if len(self.routingTable.getActivatedDestinies()) > 0:
							time.sleep(8)

							origin = self.routingTable.getOrigin()
							bytes = self.routingTable.getBinding(origin).encode('utf-8')

							newPacket = RtspPacket()
							newPacket.encode(int(re.sub(r'O', r'', self.name)),
											len(bytes),
											bytes,
											self.PLAY.encode('utf-8'))

							threading.Thread(target = self.rtspSenderHandler, args = (newPacket.getPacket(), origin, )).start()
							
							
					break

				else:
					ackName = data[4:]

					if ackName == self.name:
						acked = True
						self.routingTable.updateNeighboor(neighboor, 'ON')


			#self.routingTable.printNeighboors()
			#self.routingTable.printTable()
			time.sleep(8)


	def okReceiverHandler(self, binding):
		while True:
			try:
				receiver = self.okReceiver.get(binding)
				data, _ = receiver.recvfrom(1024)

				if data:
					packet = OkPacket()
					packet.decode(data)
					self.okAckSender.sendto(('ACK O' + str(packet.getName())).encode('utf-8'), (packet.getAddress(), self.okAckPort))

			except socket.timeout:
				continue



	''' FLOODING '''

	def openFloodReceiver(self):
		self.floodReceiver = {}

		for binding in self.routingTable.getBindings():
			
			receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   
			receiver.bind((binding, self.floodPort))
			receiver.settimeout(1)
			self.floodReceiver[binding] = receiver

	
	def openFloodSender(self):
		self.floodSender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	
	def openFloodAckReceiver(self):
		self.floodAckReceiver = {}

		for binding in self.routingTable.getBindings():
			
			receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   
			receiver.bind((binding, self.floodAckPort))
			receiver.settimeout(1)
			self.floodAckReceiver[binding] = receiver

	
	def openFloodAckSender(self):
		self.floodAckSender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


	def handleFlood(self):
		for binding in self.routingTable.getBindings():
			threading.Thread(target = self.floodReceiverHandler, args = (binding, )).start()


	def floodReceiverHandler(self, binding):
		while True:
			time.sleep(1)
			try:
				receiver = self.floodReceiver.get(binding)
				data, _ = receiver.recvfrom(1024)

				if data:
					packet = FloodPacket()
					packet.decode(data)

					if self.routingTable.updateTable(packet.getAddress(), packet.getCost()):
						
						for on in self.routingTable.getNeighboors():
							newPacket = FloodPacket()
							newPacket.encode(int(re.sub(r'O', r'', self.name)),
											 self.routingTable.getBinding(on).encode('utf-8'),
											 packet.getCost() + 1)

							threading.Thread(self.floodSenderHandler(on, newPacket.getPacket())).start()

						ackMsg = 'ACK'

					else:
						ackMsg = 'NON'

					self.floodAckSender.sendto((ackMsg + ' O' + str(packet.getName())).encode('utf-8'), (packet.getAddress(), self.floodAckPort))
					
			except socket.timeout:
				continue


	def floodSenderHandler(self, destiny, packet):
		acked = False
		while not acked:

			self.floodSender.sendto(packet, (destiny, self.floodPort))
			
			try:
				receiver = self.floodAckReceiver.get(self.routingTable.getBinding(destiny))
				
				data, _ = receiver.recvfrom(1024)
				
				if data:
					data = data.decode('utf-8')

			except socket.timeout:
				break

			else:
				ackMsg = data[0:3]
				ackName = data[4:]

				if ackName == self.name:
					if ackMsg == 'NON':
						self.routingTable.popDestiny(destiny)

					acked = True



	''' RTP PACKETS '''

	def openRtpReceiver(self):
		self.rtpReceiver = {}

		for binding in self.routingTable.getBindings():
			
			receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   
			receiver.bind((binding, self.rtpPort))
			receiver.settimeout(1)
			self.rtpReceiver[binding] = receiver


	def openRtpSender(self):
		self.rtpSender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


	def handleRtp(self):
		while True:
			try:
				origin = self.routingTable.getOrigin()
				receiver = self.rtpReceiver.get(self.routingTable.getBinding(origin))
				data, _ = receiver.recvfrom(20480)
				if data:
					for address in self.routingTable.getActivatedDestinies():
						self.rtpSender.sendto(data, (address, self.rtpPort))

			except:
				continue


	''' RTSP Treatment '''

	def openRtspReceiver(self):
		self.rtspReceiver = {}

		for binding in self.routingTable.getBindings():
			
			receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   
			receiver.bind((binding, self.rtspPort))
			receiver.settimeout(1)
			self.rtspReceiver[binding] = receiver

	
	def openRtspSender(self):
		self.rtspSender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	
	def openRtspAckReceiver(self):
		self.rtspAckReceiver = {}

		for binding in self.routingTable.getBindings():
			
			receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   
			receiver.bind((binding, self.rtspAckPort))
			receiver.settimeout(1)
			self.rtspAckReceiver[binding] = receiver

	
	def openRtspAckSender(self):
		self.rtspAckSender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


	def handleRtsp(self):
		for binding in self.routingTable.getBindings():
			threading.Thread(target = self.rtspReceiverHandler, args = (binding, )).start()


	def rtspReceiverHandler(self, binding):
		while True:
			try:
				receiver = self.rtspReceiver.get(binding)
				
				data, _ = receiver.recvfrom(1024)

				if data:
					packet = RtspPacket()
					packet.decode(data)
					self.rtspAckSender.sendto(('ACK O' + str(packet.getName())).encode('utf-8'), (packet.getAddress(), self.rtspAckPort))
		
					if self.processRtsp(packet.getAddress(), packet.getType()):
						
						origin = self.routingTable.getOrigin()
						bytes = self.routingTable.getBinding(origin).encode('utf-8')

						newPacket = RtspPacket()
						newPacket.encode(int(re.sub(r'O', r'', self.name)),
										len(bytes),
										bytes,
										packet.getType().encode('utf-8'))

						threading.Thread(target = self.rtspSenderHandler, args = (newPacket.getPacket(), origin, )).start()
						
			except socket.timeout:
				continue

	
	def rtspSenderHandler(self, packet, origin):
		acked = False
		while not acked:
			self.rtspSender.sendto(packet, (origin, self.rtspPort))
			
			try:
				receiver = self.rtspAckReceiver.get(self.routingTable.getBinding(origin))
				data, _ = receiver.recvfrom(1024)
				
				if data:
					data = data.decode('utf-8')

			except socket.timeout:
				break

			else:
				ackName = data[4:]
				
				if ackName == self.name:
					acked = True


	def processRtsp(self, destiny, requestType):
		# Process SETUP request
		if requestType == self.SETUP:
			flag = True
		
		# Process PLAY request 		
		elif requestType == self.PLAY:
			flag = self.routingTable.changeState(destiny, 'A')
		
		# Process PAUSE request
		elif requestType == self.PAUSE:
			flag = self.routingTable.changeState(destiny, 'D')

		# Process TEARDOWN request
		elif requestType == self.TEARDOWN:
			flag = self.routingTable.changeState(destiny, 'D')

		return flag