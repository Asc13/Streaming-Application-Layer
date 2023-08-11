import re

class Config:

         
    def __init__(self):
        self.lines = []
   

    ''' '''
    def readConfig(self, path):
        
        with open(path, 'r') as config:
            
            for line in config.readlines():
                split = re.split(r'\s-\s', re.sub(r'[\(\)\n]*', r'', line))
                
                self.lines.append((split[0], split[1]))

    
    def neighboors(self, name):
        temp = ''

        for elem in self.lines:
            split = re.split(r'\s:\s', elem[0])

            if split[0] == name:
                temp += split[1] + ' : ' + re.split(r'\s:\s', elem[1])[1] + '\n'

        return temp[:temp.rfind('\n')]