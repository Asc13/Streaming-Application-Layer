from OttWorker import OttWorker
import sys

class Ott:
	
	def main(self):
		worker = OttWorker(sys.argv[1], sys.argv[2], sys.argv[3])
		worker.run()

if __name__ == "__main__":
	(Ott()).main()