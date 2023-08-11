from OttClient import OttClient
from tkinter import Tk

import sys


if __name__ == "__main__":
	try:
		name = sys.argv[1]
		address = sys.argv[2]
		bootstrap = sys.argv[3]

	except:
		pass
	
	root = Tk()
	
	# Create a new client
	app = OttClient(name, address, bootstrap, root)
	app.master.title("RTPClient " + name)
	root.mainloop()