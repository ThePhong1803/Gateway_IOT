
import network, time, machine, socket
from machine import Timer
from machine import ADC


#global variable for sending data interval in milisecond
ph_interval = 10000
oxy_interval = 10000
temp_interval = 10000

#device id
devID = 1

#networking variable
sta_if = network.WLAN(network.STA_IF)
s = socket.socket()
HOST = "192.168.1.100"
PORT = 80
SSID = "The Phong"
PASS = "18032002"
send_flag = False
Private_Port = 81
retry_timeout = 9
listen_timeout = 10

def init():
    global sta_if, s
    sta_if = network.WLAN(network.STA_IF)
    s = socket.socket()
    time.sleep(1)

#networking interface
def do_connect():
    global sta_if
    if not sta_if.isconnected():
        print('connecting to network...', end = "")
        sta_if.active(True)
        sta_if.connect(SSID, PASS)
        while not sta_if.isconnected():
            print('.', end = '')
            time.sleep(1)
    print('connected to network')

def connectPort(PORT):
    global s, send_flag, HOST
    send_flag = False
    retry = 10
    print("connecting to private port.")
    while True:
        try:
            device_socket = socket.socket()
            addr_info = socket.getaddrinfo(HOST, PORT)
            address = addr_info[0][-1]
            device_socket.settimeout(10)
            device_socket.connect(address)
            msg = device_socket.recv(1024)
            device_socket.settimeout(None)
            if(msg.decode("utf-8") == "OK"):
                s.close()
                s = device_socket
                print("connected.")
                send_flag = True
                return
            else:
                continue
        except:
            try:
                s.settimeout(retry_timeout)
                msg = s.recv(1024)
                if(msg.decode("utf-8") == "WAIT"):
                    print("Waiting for closing previous port")
                    time.sleep(1)
                else:
                    raise Exception("Server down")
            except:
                if(retry > 0):
                    print("Retry connecting to private port")
                    device_socket.close()
                    retry = retry - 1
                else:
                    print("Timeout wait for reopen device port")
                    return

def setSocketPort():
    global s, Private_Port, send_flag
    send_flag = False
    print("set up port connecting. ", end = "")
    try:
        addr_info = socket.getaddrinfo(HOST, PORT)
        address = addr_info[0][-1]
        s.connect(address)
        s.send("!REQ_CON:" + str(devID) + ":" + str(Private_Port)+ "#")
        data = s.recv(1024)
        if(data.decode("utf-8") == "OK"):
            print("Request accepted")
            time.sleep(1)
            connectPort(Private_Port)
            return
    except:
        s.close()
        print("Request rejected")
        time.sleep(1)



#reading sensor 
def sending_temp():
    global s, send_flag
    if(send_flag):
        try:
            temp_adc = machine.ADC(machine.Pin(34))
            temp_adc.atten(machine.ADC.ATTN_11DB)
            raw_temp = temp_adc.read()
            #value range from 0 to 100 C
            ret_value = (raw_temp / 4095) * 50
            s.send("!" + str(devID) + ":TEMP:" + str(ret_value) + "#")
        except:
            send_flag = False
            print("Send error")

def sending_ph():
    global s, send_flag
    if(send_flag):
        try:
            temp_adc = machine.ADC(machine.Pin(35))
            temp_adc.atten(machine.ADC.ATTN_11DB)
            raw_temp = temp_adc.read()
            #value range from 0 to 14 C
            ret_value = (raw_temp / 4095) * 14
            s.send("!" + str(devID) + ":PH:" + str(ret_value) + "#")
        except:
            send_flag = False
            print("Send error")

def sending_oxy():
    global s, send_flag
    if(send_flag):
        try:
            temp_adc = machine.ADC(machine.Pin(32))
            temp_adc.atten(machine.ADC.ATTN_11DB)
            raw_temp = temp_adc.read()
            #value range from 0 to 100
            ret_value = (raw_temp / 4095) * 20
            s.send("!" + str(devID) + ":OXY:" + str(ret_value) + "#")
        except:
            send_flag = False
            print("Send error")

led1 = machine.Pin(5, machine.Pin.OUT)
led2 = machine.Pin(2, machine.Pin.OUT)

def turn_led_on():
    led1.on()

def turn_led_off():
    led1.off()

def turn_pump_on():
    led2.on()

def turn_pump_off():
    led2.off()

def process_data(data):
    global s
    if(data == "LED_ON"):
        turn_led_on()
    elif(data == "LED_OFF"):
        turn_led_off()
    elif(data == "PUMP_ON"):
        turn_pump_on()
    elif(data == "PUMP_OFF"):
        turn_pump_off()

#setup section
tim1 = Timer(-1)
tim2 = Timer(-2)
tim3 = Timer(-3)

tim1.init(period = temp_interval, mode = Timer.PERIODIC, callback = lambda t:sending_temp())
tim2.init(period = ph_interval, mode = Timer.PERIODIC, callback = lambda t:sending_ph())
tim3.init(period = oxy_interval, mode = Timer.PERIODIC, callback = lambda t:sending_oxy())

def main():
    global s, send_flag
    turn_led_off()
    turn_pump_off()
    setSocketPort()
    while True:
        try:
            if(send_flag):
                data = s.recv(1024)
                data = data.decode("UTF-8")
                process_data(data)
            else:
                raise Exception("Socket is not available")
        except:
            s.close()
            print("Reconnect")
            send_flag = False
            init() 
            do_connect()
            setSocketPort()
            time.sleep(5)