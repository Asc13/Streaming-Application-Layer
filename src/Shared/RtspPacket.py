HEADER_SIZE = 8

class RtspPacket:

    header = bytearray(HEADER_SIZE)

    def __init__(self):
        pass
        
    
    def encode(self, name, addressSize, address, type):

        header = bytearray(HEADER_SIZE)
        	
        header[0] = (name & 0xFFFFFFFF)
        header[1] = (addressSize & 0xFFFFFFFF)

        self.address = address
        self.type = type
        self.header = header


    def getName(self):
        return int(self.header[0])


    def getAddress(self):
        return self.address.decode('utf-8')


    def getType(self):
        return self.type.decode('utf-8')


    def decode(self, byteStream):
        self.header = bytearray(byteStream[:HEADER_SIZE])
        rest = byteStream[HEADER_SIZE:]
        self.address = rest[:int(self.header[1])]
        self.type = rest[int(self.header[1]):]


    # Return RTP packet.
    def getPacket(self):
        return self.header + self.address + self.type