from OttServerWorker import OttServerWorker
import sys

class OttServer:
	
	def main(self):
		worker = OttServerWorker(sys.argv[1], sys.argv[2], sys.argv[3])
		worker.run()


if __name__ == "__main__":
	(OttServer()).main()