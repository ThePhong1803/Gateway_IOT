import socket
import threading
 
class thread(threading.Thread):
    def __init__(self, thread_name, thread_ID, thread_func):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.thread_ID = thread_ID
        self.function = thread_func
 
        # helper function to execute the threads
    def run(self):
        self.function()
 


HOST = "192.168.1.7"
PORT = 27015

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = (HOST, PORT)
print('connecting to %s port ' + str(server_address))
s.connect(server_address)


def listen():
    try:
        while True:
            msg = input('Client: ')
            s.sendall(bytes(msg, "utf8"))

            if msg == "quit":
                break
    finally:
        s.close()

def response():
    try: 
        while True:
            data = s.recv(1024)
            print(data.decode("UTF-8"))
    finally:
        s.close()

thread1 = thread("Listen", 1000, listen)
thread2 = thread("Answer", 2000, response)

thread1.start()
thread2.start()