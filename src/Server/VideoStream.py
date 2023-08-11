class VideoStream:
	
	def __init__(self, filename):
		self.filename = filename
		self.end = False
		try:
			self.file = open(filename, 'rb')
		except:
			raise IOError
		

	# Get next frame.
	def nextFrame(self):
		data = self.file.read(5) # Get the framelength from the first 5 bits
		if data:
			framelength = int(data)
							
			# Read the current frame
			data = self.file.read(framelength)
			
		else: 
			self.end = True

		return data

	# Get frame number.
	def getEnd(self):
		return self.end
	
	