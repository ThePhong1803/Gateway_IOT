import sys
import time
import socket
import threading
from Adafruit_IO import MQTTClient

class thread(threading.Thread):
    def __init__(self, thread_name, thread_ID, thread_func, client, deviceID, timeout):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.thread_ID = thread_ID
        self.function = thread_func
        self.client = client
        self.deviceID = deviceID
        self.timeout = timeout

        # helper function to execute the threads
    def run(self):
        self.function(self.thread_ID, self.client, self.deviceID, self.timeout)


AIO_FEED_ID = ["bbc-led", "bbc-pump", "bbc-led-2", "bbc-pump-2", "oxy-auto-level", "oxy-auto-off-level"]
AIO_USERNAME = "phongtran1803";
AIO_KEY = "aio_QDBO27FJ8ewpZbR4eeiz4EjxrhPb";

HOST = ""
PORT = 80

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

node_list = []
data = []

#default sample rate
oxy_sample_rate = 10
temp_sample_rate = 10
ph_sample_rate = 10
oxy_low_ths = 5
oxy_high_ths = 7
timeout_connection = 60
thread_id = 0

def gethost():
    global HOST, data, oxy_low_ths, oxy_high_ths
    with open("config.txt", "r") as file:
        data = file.readlines()

    HOST = data[0]
    HOST = HOST.replace("\r", "")
    HOST = HOST.replace("\n", "")
    oxy_low_ths = float(data[1])
    oxy_high_ths = float(data[2])
    print("Host ip: " + HOST)
    print("Oxy low threshold: " + str(oxy_low_ths))
    print("Oxy high threshold: " + str(oxy_high_ths))

def assign_thread_id():
    global thread_id
    assign_id = thread_id
    thread_id = thread_id + 1
    return assign_id

def binding():
    global s, HOST, PORT
    not_bind = True
    while not_bind:
        try:
            s.bind((HOST, PORT))
            not_bind = False
        except:
            print("Failed to bind to " + str(PORT))
            print("Retry after 1 second")
            time.sleep(1)
    print("Binding success, server online")

def number_of_thread():
    global node_list
    print("Number of threads: " + str(len(node_list)))

def device_handler(thread_ID, client, devID, timeout):
    global node_list
    print("thread start device ID: " + devID)
    client.send("OK".encode())
    while True:
        try:
            client.settimeout(timeout)
            data = client.recv(1024)
            if(len(data) <= 0):
                raise Exception("No data")
            client.settimeout(None)
            readMessage(data)
        except:
            try:
                for i in range(0, len(node_list)):
                    if (node_list[i][1] == devID) and (node_list[i][3] == thread_ID):
                        node_list.remove(node_list[i])
                        print("Device " + devID + " exit")
                        return
            except:
                print("Error while remove thread from list or thread already removed")
            print("Device " + devID + " exit")
            return


def server():
    #main listen port,
    global s, server_client
    try:
        print("Server listening")
        s.listen(2)
        server_client, addr = s.accept()
        print('Server connected by', addr)
        data = server_client.recv(1024)
        server_client.send("OK".encode())
        readMessage(data)
        return

    except:
        pass # server session timeout, return
    return

def  connected(client):
    print("Connect suscessfully!...")
    for feed in AIO_FEED_ID:
        client.subscribe(feed)

def  subscribe(client , userdata , mid , granted_qos):
    print("Subcribe suscessfully!...")

def  disconnected(client):
    print("Disconnection...")
    sys.exit (1)

def  message(client , feed_id , payload):
    global node_list, oxy_low_ths, oxy_high_ths
    print("Receive data: " + payload + " Feed id: " + feed_id)
    if feed_id == "oxy-auto-level":
        oxy_low_ths = float(payload)
        with open("config.txt", 'w') as config:
            data[1] = str(oxy_low_ths) + "\n"
            config.writelines(data)
            config.close()

    if feed_id == "oxy-auto-off-level":
        oxy_high_ths = float(payload)
        with open("config.txt", 'w') as config:
            data[2] = str(oxy_high_ths) + "\n"
            config.writelines(data)
            config.close()

    msg = payload
    msg = msg.replace("!", "")
    msg = msg.replace("#", "")
    splitmsg = msg.split(":")
    for node in node_list:
        if(node[1] == splitmsg[0]):
            node_socket = node[2]
            try:
                node_socket.send(splitmsg[1].encode())
                return
            except:
                pass


client = MQTTClient(AIO_USERNAME , AIO_KEY)

def MQTT_init():
    global client
    while True:
        try:
            client.on_connect = connected
            client.on_disconnect = disconnected
            client.on_message = message
            client.on_subscribe = subscribe
            client.connect()
            client.loop_background()
            return
        except:
            print("Error occur while init MQTT client")
            print("Retry after 1 second")
            time.sleep(1)

# format is !ID:NAME:VALUE#

def processData(data):
    global HOST, node_list, server_client, client
    data = data.replace("!", "")
    data = data.replace("#", "")
    splitData = data.split(":")
    if(splitData[0] == "REQ_CON"):
        timeout = 2*max(temp_sample_rate, ph_sample_rate, oxy_sample_rate)
        deviceID = splitData[1]
        thread_name = "Node " + splitData[1]
        thread_ID = assign_thread_id()
        PORT = int(splitData[2])
        print("Request connect from device ID: " + deviceID + ", device port: " +str(PORT))
        #if existing socket, this mean device try to reconnect soon after disconnected
        for i in range(0, len(node_list)):
            try:
                if((node_list[i][1] == deviceID)):
                        node_list.remove(node_list[i])
            except:
                print("Error while removing thread or thread already removed")
        device_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        device_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        not_bind = True
        while not_bind:
            try:
                device_socket.bind((HOST, PORT)) # binding
                not_bind = False
                print("Bind Port " + str(PORT) + " success")
            except:
                print("Wait for port " + str(PORT) + " available")
                server_client.send("WAIT".encode())
                time.sleep(1)
        device_socket.settimeout(20)
        device_socket.listen(2)
        try:
            node_client, addr = device_socket.accept()
            device_socket.settimeout(0)
            node_thread = thread(thread_name, thread_ID, device_handler, node_client, deviceID, timeout)
            node_list.append([node_thread, deviceID, node_client, thread_ID])
            number_of_thread()
            node_thread.start()
        except:
            device_socket.close()
            print("Timeout listen for request private port")

    elif(splitData[0] == "1"):
        print("Receive " + splitData[1] + " from device ID: " + splitData[0] + ", value: " + splitData[2])
        if splitData[1] == "TEMP":
            client.publish("tcp-temp", splitData[2])
        elif splitData[1] == "OXY":
            client.publish("tcp-oxy", splitData[2])
            if float(splitData[2]) >= oxy_high_ths:
                print("Oxy is too high, auto turn off pump")
                for node in node_list:
                    if(node[1] == splitData[0]):
                        node_socket = node[2]
                        try:
                            node_socket.send("PUMP_OFF".encode())
                            client.publish("bbc-pump", "!1:PUMP_OFF#")
                            return
                        except:
                            pass
            if float(splitData[2]) <= oxy_low_ths:
                print("Oxy is too low, auto turn on pump")
                for node in node_list:
                    if(node[1] == splitData[0]):
                        node_socket = node[2]
                        try:
                            node_socket.send("PUMP_ON".encode())
                            client.publish("bbc-pump", "!1:PUMP_ON#")
                            return
                        except:
                            pass
        elif splitData[1] == "PH":
            client.publish("tcp-ph", splitData[2])
    elif(splitData[0] == "2"):
        print("Receive " + splitData[1] + " from device ID: " + splitData[0] + ", value: " + splitData[2])
        if splitData[1] == "TEMP":
            client.publish("tcp-temp", splitData[2])
        elif splitData[1] == "OXY":
            client.publish("tcp-oxy", splitData[2])
            if float(splitData[2]) >= oxy_high_ths:
                print("Oxy is too high, auto turn off pump")
                for node in node_list:
                    if(node[1] == splitData[0]):
                        node_socket = node[2]
                        try:
                            node_socket.send("PUMP_OFF".encode)
                            client.publish("bbc-pump-2", "!2:PUMP_OFF#")
                            return
                        except:
                            pass
            if float(splitData[2]) <= oxy_low_ths:
                print("Oxy is too low, auto turn on pump")
                for node in node_list:
                    if(node[1] == splitData[0]):
                        node_socket = node[2]
                        try:
                            node_socket.send("PUMP_ON".encode())
                            client.publish("bbc-pump-2", "!2:PUMP_ON#")
                            return
                        except:
                            pass
        elif splitData[1] == "PH":
            client.publish("tcp-ph", splitData[2])

mess = ""

def readMessage(message):
    if (len(message) > 0):
        global mess
        global server_client
        mess = message.decode("UTF-8")
        while ("#" in mess) and ("!" in mess):
            start = mess.find("!")
            end = mess.find("#")
            processData(mess[start:end + 1])
            if (end == len(mess)):
                mess = ""
            else:
                mess = mess[end+1:]

def main():
    time.sleep(5)
    gethost()
    MQTT_init()
    binding()
    time.sleep(1)
    while True:
        server()

main()
