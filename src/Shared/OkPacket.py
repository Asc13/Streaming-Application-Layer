HEADER_SIZE = 4

class OkPacket:

    header = bytearray(HEADER_SIZE)

    def __init__(self):
        pass
    
    
    # Encode the Flood packet with header fields and payload.
    def encode(self, name, address):
        
        header = bytearray(HEADER_SIZE)

        # Fill the header bytearray with Flood header fields        
        header[0] = (name & 0xFFFFFFFF)

        self.address = address
        self.header = header



    # Decode the Flood packet.
    def decode(self, byteStream):
        self.header = bytearray(byteStream[:HEADER_SIZE])
        self.address = byteStream[HEADER_SIZE:]


    def getName(self):
        return int(self.header[0])


    def getAddress(self):
        return self.address.decode('utf-8')


    # Return Flood packet.
    def getPacket(self):
        return self.header + self.address