import sys
import re
from threading import RLock

sys.path.insert(0, '../Shared')


class RoutingTable:

    def __init__(self):
        self.neighboors = []
        self.lock = RLock()
        self.flood = None


    def appendNeighboors(self, neighboors):
        with self.lock:
            for neighboor in neighboors:
                split = re.split(r'\s:\s', neighboor)
                self.neighboors.append((split[1], (split[0], 'OFF')))
                

    def printNeighboors(self):
        with self.lock:
            for elem in self.neighboors:
                print(elem[0] + ' : ' + str(elem[1]))
                

    def getBindings(self):
        with self.lock:
            bindings = []
            for elem in self.neighboors:
                bindings.append(elem[1][0])

            return set(bindings)


    def getNeighboors(self):
        with self.lock:
            keys = []
            for elem in self.neighboors:
                keys.append(elem[0])

            return keys

    
    def getNeighboor(self, neighboor):
        with self.lock:
            for elem in self.neighboors:
                if elem[0] == neighboor:
                    self.neighboors.remove(elem)
                    return elem[1]

    
    def setNeighboor(self, neighboor, value):
        with self.lock:
            self.neighboors.append((neighboor, value))


    def updateNeighboor(self, neighboor, state):
        with self.lock:
            temp = self.getNeighboor(neighboor)
            self.setNeighboor(neighboor, (temp[0], state))


    def getBinding(self, neighboor):
        with self.lock:
            for elem in self.neighboors:
                if elem[0] == neighboor:
                    return elem[1][0]


    def createTable(self):
        with self.lock:
            self.cost = 9999
            self.origin = ''
            self.destinies = {}

            for destiny in self.getNeighboors():
                self.destinies[destiny] = 'D'


    def isOrigin(self, neighboor):
        with self.lock:
            return neighboor == self.origin


    def createServerTable(self):
        with self.lock:    
            self.cost = 0
            self.origin = ''
            self.destinies = {}
            
            for destiny in self.getNeighboors():
                self.destinies[destiny] = 'D'


    def updateTable(self, origin, cost):
        with self.lock:
            if cost < self.cost and self.origin != origin:
                self.cost = cost
                self.origin = origin
                
                try:
                    self.destinies.pop(origin)
                except KeyError:
                    pass

                return True

            elif cost == self.cost and self.origin == origin:
                return True

            else:
                return False

    
    def resetTable(self):
        with self.lock:
            self.cost = 9999
            self.origin = ''
            
            for destiny in self.getNeighboors():
                if destiny not in self.destinies:
                    self.destinies[destiny] = 'D'


    def popDestiny(self, address):
        with self.lock:
            try:
                self.destinies.pop(address)
            except KeyError:
                pass


    def getDestinies(self):
        with self.lock:
            return list(self.destinies)

    
    def getActivatedDestinies(self):
        with self.lock:
            actives = []
            for key, value in self.destinies.items():
                if value == 'A':
                    actives.append(key)
            
            return actives


    def getOrigin(self):
        with self.lock:
            return self.origin

    
    def changeState(self, destiny, state):
        with self.lock:
            if state == 'D' and len(self.getActivatedDestinies()) > 1:
                self.destinies[destiny] = state
                return False
            else:
                self.destinies[destiny] = state
                return True
    

    def printTable(self):
        print(self.origin, self.cost, end = ' [')
        
        for key, value in self.destinies.items():
            print(key + ' ' + value, end = ', ')

        print(']')