import time
from tkinter import *
from PIL import ImageTk, Image
import tkinter.messagebox as tkMessageBox
import socket, threading, sys, os
import re

sys.path.insert(0, '../Shared')
from RtpPacket import RtpPacket
from RtspPacket import RtspPacket
from FloodPacket import FloodPacket
from RoutingTable import RoutingTable
from OkPacket import OkPacket


CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class OttClient:

	SETUP_STR = 'SETUP'
	PLAY_STR = 'PLAY'
	PAUSE_STR = 'PAUSE'
	TEARDOWN_STR = 'TEARDOWN'

	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT
	
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3

	floodPort = 5005
	regPort = 5006
	okPort = 5007
	floodAckPort = 5008
	regAckPort = 5009
	okAckPort = 5010
	rtspPort = 5011
	rtspAckPort = 5012
	rtpPort = 16384

	RTSP_VER = "RTSP/1.0"
	TRANSPORT = "RTP/UDP"


	# Initiation.
	def __init__(self, name, address, bootstrap, master):
		self.name = name
		self.address = address
		self.bootstrap = bootstrap
		self.routingTable = RoutingTable()
		self.startClient(master)
		


	def startClient(self, master):
		self.openRegSender()
		self.openRegAckReceiver()
	
		self.sendRegistries()
		self.routingTable.createTable()
		
		self.openOkSender()
		self.openOkReceiver()
		self.openOkAckReceiver()
		self.openOkAckSender()
		self.openFloodReceiver()
		self.openFloodAckSender()
		self.openRtspSender()
		self.openRtspAckReceiver()

		self.receiveOk()
		self.sendOk()
		threading.Thread(target = self.receiveFlood).start()

		self.openRtpReceiver()

		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
		self.requestSent = -1
		self.teardownAcked = 0
		self.frameNbr = 0


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

					self.state = self.READY

					break

				else:
					ackName = data[4:]

					if ackName == self.name:
						acked = True
						self.routingTable.updateNeighboor(neighboor, 'ON')

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
		self.floodReceiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   
		self.floodReceiver.bind((self.address, self.floodPort))
		self.floodReceiver.settimeout(1)

	
	def openFloodAckSender(self):
		self.floodAckSender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


	def receiveFlood(self):
		while True:
			try:
				data, _ = self.floodReceiver.recvfrom(1024)

				if data:
					packet = FloodPacket()
					packet.decode(data)
					
					self.routingTable.updateTable(packet.getAddress(), packet.getCost())

					self.floodAckSender.sendto(('ACK O' + str(packet.getName())).encode('utf-8'), (packet.getAddress(), self.floodAckPort))
					
			except socket.timeout:
				continue



	''' RTSP TREATMENT '''

	def openRtspSender(self):
		self.rtspSender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


	def openRtspAckReceiver(self):
		self.rtspAckReceiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.rtspAckReceiver.bind((self.address, self.rtspAckPort))
		self.rtspAckReceiver.settimeout(1)


	# Send RTSP request to the server.
	def sendRtspRequest(self, requestCode):	
		
		# Setup request
		if requestCode == self.SETUP and self.state == self.INIT:
			
			origin = self.routingTable.getOrigin()
			bytes = self.address.encode('utf-8')

			packet = RtspPacket()
			packet.encode(int(re.sub(r'O', r'', self.name)),
						  len(bytes),
						  bytes,
						  self.SETUP_STR.encode('utf-8'))

			threading.Thread(target = self.sendRtsp, args = (origin, packet, self.SETUP, )).start()

		# Play request
		elif requestCode == self.PLAY and self.state == self.READY:

			origin = self.routingTable.getOrigin()
			bytes = self.address.encode('utf-8')

			packet = RtspPacket()
			packet.encode(int(re.sub(r'O', r'', self.name)), 
						  len(bytes),
						  bytes,
						  self.PLAY_STR.encode('utf-8'))

			threading.Thread(target = self.sendRtsp, args = (origin, packet, self.PLAY, )).start()
		
		# Pause request
		elif requestCode == self.PAUSE and self.state == self.PLAYING:

			origin = self.routingTable.getOrigin()
			bytes = self.address.encode('utf-8')

			packet = RtspPacket()
			packet.encode(int(re.sub(r'O', r'', self.name)),
						  len(bytes),
						  bytes,
						  self.PAUSE_STR.encode('utf-8'))

			threading.Thread(target = self.sendRtsp, args = (origin, packet, self.PAUSE)).start()
			
		# Teardown request
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:

			origin = self.routingTable.getOrigin()
			bytes = self.address.encode('utf-8')

			packet = RtspPacket()
			packet.encode(int(re.sub(r'O', r'', self.name)),
						  len(bytes),
						  bytes,
						  self.TEARDOWN_STR.encode('utf-8'))

			threading.Thread(target = self.sendRtsp, args = (origin, packet, self.TEARDOWN)).start()

		else:
			return

	

	def sendRtsp(self, origin, packet, requestSent):
		acked = False
		while not acked:
			self.rtspSender.sendto(packet.getPacket(), (origin, self.rtspPort))
			
			try:
				data, _ = self.rtspAckReceiver.recvfrom(1024)
				
				if data:
					data = data.decode('utf-8')
			
			except socket.timeout:
				continue

			else:
				ackName = data[4:]

				if ackName == self.name:
					
					if requestSent == self.SETUP:
						self.state = self.READY

					elif requestSent == self.PLAY:
						self.state = self.PLAYING

					elif requestSent == self.PAUSE:
						self.state = self.READY
						
						# The play thread exits. A new thread is created on resume.
						self.playEvent.set()

					elif requestSent == self.TEARDOWN:
						self.state = self.INIT
						self.teardownAcked = 1

					acked = True
	


	# Open RTP socket binded to a specified port.
	def openRtpReceiver(self):

		# Create a new datagram socket to receive RTP packets from the server
		self.rtpReceiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		
		try:
			# Bind the socket to the address using the RTP port given by the client user
			self.rtpReceiver.bind((self.address, self.rtpPort))
		
		except:
			tkMessageBox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' %self.rtpPort)


	# Handler on explicitly closing the GUI window.
	def handler(self):
		self.pauseMovie()
		if tkMessageBox.askokcancel("Quit?", "Are you sure you want to quit?"):
			self.exitClient()

		else: # When the user presses cancel, resume playing.
			self.playMovie()



	''' GUI and RTSP Treatment '''

	# Build GUI.		
	def createWidgets(self):

		# Create Setup button
		self.setup = Button(self.master, width=20, padx=3, pady=3)
		self.setup["text"] = "Setup"
		self.setup["command"] = self.setupMovie
		self.setup.grid(row=1, column=0, padx=2, pady=2)

		# Create Play button
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=1, column=1, padx=2, pady=2)

		# Create Pause button
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=1, column=2, padx=2, pady=2)

		# Create Teardown button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=1, column=3, padx=2, pady=2)

		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 
	

	# Setup button handler.
	def setupMovie(self):
		if self.state == self.INIT:
			self.sendRtspRequest(self.SETUP)
	

	# Teardown button handler.
	def exitClient(self):
		self.sendRtspRequest(self.TEARDOWN)
		self.master.destroy() # Close the gui window
		os.remove(CACHE_FILE_NAME + self.name + CACHE_FILE_EXT) # Delete the cache image from video


	# Pause button handler.
	def pauseMovie(self):
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)
	

	# Play button handler.
	def playMovie(self):
		if self.state == self.READY:

			# Create a new thread to listen for RTP packets
			threading.Thread(target = self.listenRtp).start()
			self.playEvent = threading.Event()
			self.playEvent.clear()
			self.sendRtspRequest(self.PLAY)
	

	# Listen for RTP packets.
	def listenRtp(self):		
		while True:
			try:
				data = self.rtpReceiver.recv(20480)
				if data:
					rtpPacket = RtpPacket()
					rtpPacket.decode(data)
					
					currFrameNbr = rtpPacket.seqNum()
										
					if currFrameNbr > self.frameNbr: # Discard the late packet
						self.frameNbr = currFrameNbr
						self.updateMovie(self.writeFrame(rtpPacket.getPayload()))

			except:
                # Stop listening upon requesting PAUSE or TEARDOWN
				if self.playEvent.isSet():
					break

				# Upon receiving ACK for TEARDOWN request,
				# close the RTP socket
				if self.teardownAcked == 1:
					self.rtpReceiver.shutdown(socket.SHUT_RDWR)
					self.rtpReceiver.close()
					break


	#Write the received frame to a temp image file. Return the image file.
	def writeFrame(self, data):
		cachename = CACHE_FILE_NAME + self.name + CACHE_FILE_EXT
		file = open(cachename, "wb")
		file.write(data)
		file.close()
		return cachename
	

	# Update the image file as video frame in the GUI.
	def updateMovie(self, imageFile):
		photo = ImageTk.PhotoImage(Image.open(imageFile))
		self.label.configure(image = photo, height=288)
		self.label.image = photo
		

