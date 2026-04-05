
import argparse
from time import sleep

import serial


class PowerHandler():
    def __init__(self):
        super(PowerHandler, self).__init__()

        self.portName = 'COM14'
        self.baudrate = 9600
        self.connected = False

        self.port = serial.Serial(self.portName, self.baudrate)

    def checkConnection(self):
        self.port.write('*IDN?\n'.encode())
        idnStr = self.port.readline().decode()
        if not idnStr:
            exit("No response from pwr module")
        print(idnStr)
        self.connected = True

    def setI(self, iValue: float, chan:int=1):
        self.port.write(f'ISET{chan}:{iValue}\n'.encode())

    def setV(self, vValue: float, chan:int=1):
        self.port.write(f'VSET{chan}:{vValue}\n'.encode())

    def getI(self, chan: int =1)->float:
        self.port.write(f'ISET{chan}?\n'.encode())
        iValue = self.port.readline().decode()
        return float(iValue)

    def getV(self, chan: int =1)->float:
        self.port.write(f'VSET{chan}?\n'.encode())
        vValue = self.port.readline().decode()
        return float(vValue)

    def getI_out(self, chan: int =1)->str:
        self.port.write(f'IOUT{chan}?\n'.encode())
        return self.port.readline().decode()

    def getV_out(self, chan: int =1)->str:
        self.port.write(f'VOUT{chan}?\n'.encode())
        return self.port.readline().decode()

    def on(self):
        self.port.write(f'OUT1\n'.encode())

    def off(self):
        self.port.write(f'OUT0\n'.encode())

    def status(self):
        print(f'Now I set: {self.getI()}A')
        print(f'Now V set: {self.getV()}V')
        print(f'Now I out: {self.getI_out()[:-1]}')
        print(f'Now V out: {self.getV_out()[:-1]}')
        # self.port.write(f'STATUS?\n'.encode())
        # byteSta = int(self.port.read(1))
        # chan_1 = byteSta & 0x01
        # chan_2 = (byteSta >> 1) & 0x01



def main():
    parser = argparse.ArgumentParser(
        description="Power on/off",
        epilog="python power.py on/off")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-on", '--on', action="store_true",
                       help="Power on")
    group.add_argument("-off", '--off', action="store_true",
                       help="Power off")
    group.add_argument("-sta", '--status', action="store_true",
                       help="Status IV")
    args = parser.parse_args()

    pwr = PowerHandler()

    pwr.setV(vValue=28.0)
    pwr.setI(iValue=0.5)


    mode = [key for key, val in vars(args).items() if val][0]
    match mode:
        case 'on':
            pwr.on()
            #sleep(1)
            #pwr.status()
        case 'off':
            pwr.off()
            #sleep(1)
            #pwr.status()
        case 'status':
            pwr.status()

if __name__ == '__main__':
    main()
