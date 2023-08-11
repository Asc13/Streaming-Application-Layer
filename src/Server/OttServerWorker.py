import sys, socket, time, threading
import re

from VideoStream import VideoStream

sys.path.insert(0, '../Shared')
from RoutingTable import RoutingTable
from Config import Config
from RtpPacket import RtpPacket
from RtspPacket import RtspPacket
from FloodPacket import FloodPacket
from OkPacket import OkPacket


class OttServerWorker:

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
		self.openRegAckSender()
		self.openRegReceiver()

		self.parseConfig()
		self.routingTable.appendNeighboors(re.split(r'\n', self.config.neighboors(self.name)))
		self.routingTable.createServerTable()
		
		self.openOkSender()
		self.openOkReceiver()
		self.openOkAckReceiver()
		self.openOkAckSender()
		self.openFloodAckReceiver()
		self.openFloodSender()
		self.openRtspReceiver()
		self.openRtspAckSender()
		self.openRtpSender()

		threading.Thread(target = self.receiveRegistries).start()
		threading.Thread(target = self.receiveOk).start()
		self.sendOk()
		self.sendFlood()
		self.handleRtsp()
		threading.Thread(target = self.sendRtp()).start()


	''' REGISTRIES '''

	def parseConfig(self):
		self.config = Config()
		self.config.readConfig(self.bootstrap)


	def openRegReceiver(self):
		self.regReceiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   
		self.regReceiver.bind((self.address, self.regPort))


	def openRegAckSender(self):
		self.regAckSender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   
		self.regAckSender.bind((self.address, self.regAckPort))


	def receiveRegistries(self):

		while True:
			try:
				data, _ = self.regReceiver.recvfrom(1024)
				
				if data:
					data = data.decode('utf-8')
					split = re.split(r' ', data)

					neighboors = self.config.neighboors(split[0])
					self.regAckSender.sendto(neighboors.encode('utf-8'), (split[1], self.regAckPort))
					
			except Exception as e:
				print(e)


	def openOkReceiver(self):
		self.okReceiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   
		self.okReceiver.bind((self.address, self.okPort))
		self.okReceiver.settimeout(1)

	
	def openOkSender(self):
		self.okSender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	
	def openOkAckReceiver(self):
		self.okAckReceiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   
		self.okAckReceiver.bind((self.address, self.okAckPort))
		self.okAckReceiver.settimeout(1)

	
	def openOkAckSender(self):
		self.okAckSender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


	def sendOk(self):
		for neighboor in self.routingTable.getNeighboors():
			packet = OkPacket()
			packet.encode(int(re.sub(r'O', r'', self.name)),
						  self.routingTable.getBinding(neighboor).encode('utf-8'))

			threading.Thread(target = self.okSenderHandler, args = (packet.getPacket(), neighboor, )).start()


	def receiveOk(self):
		while True:
			try:
				data, _ = self.okReceiver.recvfrom(1024)

				if data:
					packet = OkPacket()
					packet.decode(data)
					self.okAckSender.sendto(('ACK O' + str(packet.getName())).encode('utf-8'), (packet.getAddress(), self.okAckPort))
					
			except socket.timeout:
				continue


	def okSenderHandler(self, packet, neighboor):
		
		while True:

			acked = False
			while not acked:

				self.okSender.sendto(packet, (neighboor, self.okPort))
				
				try:
					data, _ = self.okAckReceiver.recvfrom(1024)
					
					if data:
						data = data.decode('utf-8')

				except socket.timeout:
					self.routingTable.updateNeighboor(neighboor, 'OFF')	
					break

				else:
					ackName = data[4:]

					if ackName == self.name:
						acked = True
						self.routingTable.updateNeighboor(neighboor, 'ON')
			
			time.sleep(8)


	''' FLOODING '''

	def openFloodAckReceiver(self):
		self.floodAckReceiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   
		self.floodAckReceiver.bind((self.address, self.floodAckPort))
		self.floodAckReceiver.settimeout(1)

	
	def openFloodSender(self):
		self.floodSender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


	def sendFlood(self):
	
		for neighboor in self.routingTable.getNeighboors():
			packet = FloodPacket()
			packet.encode(int(re.sub(r'O', r'', self.name)),
						  self.routingTable.getBinding(neighboor).encode('utf-8'), 1)

			threading.Thread(target = self.floodSenderHandler, args = (neighboor, packet.getPacket())).start()



	def floodSenderHandler(self, neighboor, packet):
		while True:
		
			acked = False
			while not acked:

				self.floodSender.sendto(packet, (neighboor, self.floodPort))
				
				try:
					data, _ = self.floodAckReceiver.recvfrom(1024)
					
					if data:
						data = data.decode('utf-8')

				except socket.timeout:
					continue

				else:
					ackName = data[4:]

					if ackName == self.name:
						acked = True

			time.sleep(8)



	''' RTP PACKETS '''

	def openRtpSender(self):
		self.rtpSender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


	def sendRtp(self):

		frameNum = 0

		while True:

			self.videoStream = VideoStream('../Media/movie.Mjpeg')

			while not self.videoStream.getEnd():
				time.sleep(0.03)

				data = self.videoStream.nextFrame()
				
				if data: 
					frameNum += 1

					try:
						addresses = self.routingTable.getActivatedDestinies()
						
						for address in addresses:
							self.rtpSender.sendto(self.makeRtp(data, frameNum), (address, self.rtpPort))

					except:
						continue
				

	def makeRtp(self, payload, frameNbr):
		version = 2
		padding = 0
		extension = 0
		cc = 0
		marker = 0
		pt = 26 # MJPEG type
		seqnum = frameNbr
		ssrc = 0 
		
		rtpPacket = RtpPacket()
		
		rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)
		
		return rtpPacket.getPacket()

	

	''' RTSP TREATMENT '''	
	
	def openRtspReceiver(self):
		self.rtspReceiver = {}

		for binding in self.routingTable.getBindings():
			
			receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   
			receiver.bind((binding, self.rtspPort))
			receiver.settimeout(1)
			self.rtspReceiver[binding] = receiver

	
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
					
					_ = self.processRtsp(packet.getAddress(), packet.getType())
					
			except socket.timeout:
				continue


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