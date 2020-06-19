#!/usr/bin/env python3
import sys
from time import sleep
from SX127x.LoRa import *
from SX127x.LoRaArgumentParser import LoRaArgumentParser
from SX127x.board_config import BOARD
import LoRaWAN
from LoRaWAN.MHDR import MHDR
import json,datetime

BOARD.setup()
parser = LoRaArgumentParser("LoRaWAN sender")

class LoRaWANsend(LoRa):
    def __init__(self, devaddr = [], nwkey = [], appkey = [], verbose = False):
        super(LoRaWANsend, self).__init__(verbose)

    def on_tx_done(self): #2
        print("TxDone\n")
        self.set_mode(MODE.STDBY)
        self.clear_irq_flags(TxDone=1)
        self.set_mode(MODE.SLEEP)
        self.set_dio_mapping([0,0,0,0,0,0])
        self.set_invert_iq(1)
        self.reset_ptr_rx()
        sleep(1)
        self.set_mode(MODE.RXCONT)
        print("waiting for gw feedback")
        
    def on_rx_done(self): #3
        global RxDone
        RxDone = any([self.get_irq_flags()[s] for s in ['rx_done']])
        print("RxDone")
        self.clear_irq_flags(RxDone=1)
       
        payload = self.read_payload(nocheck=True)
        
        
        print("len(payload):",len(payload))
        
        lorawan = LoRaWAN.new(nwskey, appskey)
        lorawan.read(payload)
        
        k = lorawan.get_payload()[0] # 1 <= MOD <= 10
        print("k (ascii):", k)
        
        B = int(chr(k[i]))
        print("B:", B)
                
        # Preparing to send real data
        lora.set_mode(MODE.SLEEP)
        lora.set_dio_mapping([1,0,0,0,0,0])
            
    '''def on_connect(self, mqttc, obj, flags, rc) :
        print("on_conn")
        if rc==0:
            print('\nconnect to server')
            self.subscribe([('gateway/{}/tx'.format(self.eui),2)]) #, ('application/5/device/0000000000000007/rx',2)]
            self.connectSuccess=True
        else:
            print('bad connection:{}'.format(rc))'''
    
    def send(self):
        global fCnt
        lorawan = LoRaWAN.new(nwskey, appskey)
        message = "12,5"

        lorawan.create(MHDR.CONF_DATA_DOWN, {'devaddr': devaddr, 'fcnt': fCnt, 'data': list(map(ord, message)) })
        print("fCnt: ",fCnt)
        print("Send Message: ",message)
        fCnt = fCnt+1
        datalist = lorawan.to_raw()
        
        #shift data
        datalist = shift_data(datalist)
        print(datalist)
        
        self.write_payload(datalist)
        
        self.set_mode(MODE.TX)
    
    def time_checking(self):
        global RxDone

        TIMEOUT = any([self.get_irq_flags()[s] for s in ['rx_timeout']])
        if TIMEOUT:
            print("TIMEOUT!!")
            write_config()
            sys.exit(0)
        elif RxDone:
            print("SUCCESS!!")
            sys.exit(0)
    
    def start(self):
        self.send() #1
        #self.set_dio_mapping(DIO_RX)
        while True:
        #   self.time_checking() 
           sleep(1)

def binary_array_to_hex(array):
    return ''.join(format(x, '02x') for x in array)

def write_config():
    global devaddr,nwskey,appskey,fCnt
    config = {'devaddr':binary_array_to_hex(devaddr),'nwskey':binary_array_to_hex(nwskey),'appskey':binary_array_to_hex(appskey),'fCnt':fCnt}
    data = json.dumps(config, sort_keys = True, indent = 4, separators=(',', ': '))
    fp = open("config.json","w")
    fp.write(data)
    fp.close()

def read_config():
    global devaddr,nwskey,appskey,fCnt
    config_file = open('config.json')
    parsed_json = json.load(config_file)
    devaddr = list(bytearray.fromhex(parsed_json['devaddr']))
    nwskey = list(bytearray.fromhex(parsed_json['nwskey']))
    appskey = list(bytearray.fromhex(parsed_json['appskey']))
    fCnt = parsed_json['fCnt']
    print("devaddr: ",parsed_json['devaddr'])
    print("nwskey : ",parsed_json['nwskey'])
    print("appskey: ",parsed_json['appskey'],"\n")
def shift_data(thedatalist):
    for i in range(1,len(thedatalist)-4):
        thedatalist[i] += 5
    return thedatalist
    
# Init
RxDone = False
fCnt = 0
devaddr = []
nwskey = []
appskey = []
read_config()
lora = LoRaWANsend(False)


DIO_TX = [1,0,0,0,0,0]
DIO_RX = [0,0,0,0,0,0]

# Setup
lora.set_mode(MODE.SLEEP)
lora.set_dio_mapping([1,0,0,0,0,0])
lora.set_freq(924.1)
#lora.set_freq(AS923.FREQ7)
lora.set_spreading_factor(SF.SF9)
lora.set_bw(BW.BW125)
lora.set_pa_config(pa_select=1)
lora.set_pa_config(max_power=0x0F, output_power=0x0E)
lora.set_sync_word(0x34)
lora.set_rx_crc(True)

#print(lora)
assert(lora.get_agc_auto_on() == 1)

try:
    print("Sending LoRaWAN message")
    lora.start()
except KeyboardInterrupt:
    sys.stdout.flush()
    print("\nKeyboardInterrupt")
finally:
    sys.stdout.flush()
    lora.set_mode(MODE.SLEEP)
    BOARD.teardown()
    write_config()