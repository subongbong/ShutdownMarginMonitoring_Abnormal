import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
import numpy as np


'''
Class name  : Data share
Ver         : Ver 0
Release     : 2018 - 07 -06
Developer   : Deail Lee
'''

import socket
import pickle
from struct import pack, unpack
from numpy import shape
from time import sleep
from parameter import para
import csv


class DataShare:
    def __init__(self, ip, port):

        # socket part
        self.ip, self.port = ip, port  # remote computer

        # cns-data memory
        self.mem = {}  # {'PID val': {'Sig': sig, 'Val': val, 'Num': idx }}
        self.list_mem = {}          ##
        self.list_mem_number = []   ##
        self.number = 0             ##

        self.result=[]

        self.data=[]
        self.shut = []

        # self.Detect_bin = []
        self.A = len(self.data)

        self.fig = plt.figure()
        self.ax1 = self.fig.add_subplot(2, 1, 1)
        self.ax2 = self.fig.add_subplot(2, 1, 2)

    # 1. memory reset and refresh UDP
    def reset(self):
        self.mem, self.list_mem = {}, {}
        self.initial_DB()
        for i in range(5):
            self.read_socketdata()
        print('Memory and UDP network reset ready...')

    # 2. update mem from read CNS
    def update_mem(self):
        data = self.read_socketdata()
        for i in range(0, 4000, 20):
            sig = unpack('h', data[24 + i: 26 + i])[0]
            para = '12sihh' if sig == 0 else '12sfhh'
            pid, val, sig, idx = unpack(para, data[8 + i:28 + i])
            pid = pid.decode().rstrip('\x00')  # remove '\x00'
            if pid != '':
                self.mem[pid]['Val'] = val
                self.list_mem[pid]['Val'].append(val)

    # 3. change value and send
    def sc_value(self, para, val, cns_ip, cns_port):
        self.change_value(para, val)
        self.send_data(para, cns_ip, cns_port)

    # 4. dump list_mem as pickle (binary file)
    def save_list_mem(self, file_name):
        with open(file_name, 'wb') as f:
            print('{}_list_mem save done'.format(file_name))
            pickle.dump(self.list_mem, f)

    # (sub) 1.
    def animate(self,i):
        # 1. 값을 로드.
        # 2. 로드한 값을 리스로 저장.
        self.update_mem()
        self.list_mem_number.append(self.number)

        self.ShutdownMarginCalculation()
        self.Detect()
        self.Diagnosis()
        self.Suggest()
        self.text()
        self.number += 1

        # 3. 이전의 그렸던 그래프를 지우는거야.
        self.ax1.clear()
        self.ax2.clear()

        # 4. 그래프 업데이트.
        self.ax1.plot(self.list_mem_number, self.result, label='Result', linewidth=1)
        self.ax1.legend(loc='upper right', ncol=5, fontsize=10)
        self.ax1.set_ylim(-0.9, 1.1)
        self.ax1.set_xlabel('Time')
        self.ax1.set_ylabel('Monitoring Result')

        self.ax2.plot(self.list_mem_number, self.shut, linewidth=1)
        self.ax2.legend(loc='upper right', ncol=5, fontsize=10)
        self.ax2.set_ylim(0, 6000)
        self.ax2.axhline(y=1770, ls='--',color='r',linewidth=1)
        self.ax2.set_xlabel('Time')
        self.ax2.set_ylabel('ShutdownMargin')

        self.fig.tight_layout()


    # (sub) 1.1make grape
    def make_gp(self):
        style.use('fivethirtyeight')  # 스타일 형식
        ani = animation.FuncAnimation(self.fig, self.animate, interval=1000)
        plt.show()

    # (sub) socket part function
    def read_socketdata(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # socket definition
        sock.bind((self.ip, self.port))
        data, addr = sock.recvfrom(4008)
        sock.close()
        return data

    # (sub) initial memory
    def initial_DB(self):
        idx = 0
        with open('./db.txt', 'r') as f:   # use unit-test
        #with open('./fold/db.txt', 'r') as f: # This line is to use the "import" other function
            while True:
                temp_ = f.readline().split('\t')
                if temp_[0] == '':  # if empty space -> break
                    break
                sig = 0 if temp_[1] == 'INTEGER' else 1
                self.mem[temp_[0]] = {'Sig': sig, 'Val': 0, 'Num': idx}
                self.list_mem[temp_[0]] = {'Sig': sig, 'Val': [], 'Num': idx}
                idx += 1

    def ShutdownMarginCalculation(self):
        subdata=[]

        # 1. time
        self.Time = self.number
        print(self.Time)
        subdata.append(self.Time)

        # 2. BOL, 현출력% -> 0% 하기위한 출력 결손량 계산
        self.ReactorPower = self.mem['QPROLD']['Val']*100
        self.PowerDefect_BOL = para.TotalPowerDefect_BOL * self.ReactorPower / para.HFP
        print(self.PowerDefect_BOL)
        subdata.append(self.PowerDefect_BOL)

        # 3. EOL, 현출력% -> 0% 하기위한 출력 결손량 계산
        self.PowerDefect_EOL = para.TotalPowerDefect_EOL * self.ReactorPower / para.HFP
        print(self.PowerDefect_EOL)
        subdata.append(self.PowerDefect_EOL)

        # 4. 현재 연소도, 현출력% -> 0% 하기위한 출력 결손량 계산
        A = para.Burnup_EOL - para.Burnup_BOL
        B = self.PowerDefect_EOL - self.PowerDefect_BOL
        C = para.Burnup - para.Burnup_BOL

        self.PowerDefect_Burnup = B * C / A + self.PowerDefect_BOL
        print(self.PowerDefect_Burnup)
        subdata.append(self.PowerDefect_Burnup)

        # 5. 반응도 결손량을 계산
        self.PowerDefect_Final = self.PowerDefect_Burnup + para.VoidCondtent
        print(self.PowerDefect_Final)
        subdata.append(self.PowerDefect_Final)

        # 6. 운전불가능 제어봉 제어능을 계산
        self.InoperableRodWorth = para.InoperableRodNumber * para.WorstStuckRodWorth
        print(self.InoperableRodWorth)
        subdata.append(self.InoperableRodWorth)

        # 7. 비정상 제어봉 제어능을 계산
        if para.AbnormalRodName == 'C':
            self.AbnormalRodWorth = para.BankWorth_C / 8 * para.AbnormalRodNumber
            print(self.AbnormalRodWorth)
            subdata.append(self.AbnormalRodWorth)
        elif para.AbnormalRodName == 'A':
            self.AbnormalRodWorth = para.BankWorth_A / 8 * para.AbnormalRodNumber
            print(self.AbnormalRodWorth)
            subdata.append(self.AbnormalRodWorth)
        elif para.AbnormalRodName == 'B':
            self.AbnormalRodWorth = para.BankWorth_B / 8 * para.AbnormalRodNumber
            print(self.AbnormalRodWorth)
            subdata.append(self.AbnormalRodWorth)
        elif para.AbnormalRodName == 'D':
            self.AbnormalRodWorth = para.BankWorth_D / 8 * para.AbnormalRodNumber
            print(self.AbnormalRodWorth)
            subdata.append(self.AbnormalRodWorth)

        # 8. 운전 불능, 비정상 제어봉 제어능의 합 계산
        self.InoperableAbnormal_RodWorth = self.InoperableRodWorth + self.AbnormalRodWorth
        print(self.InoperableAbnormal_RodWorth)
        subdata.append(self.InoperableAbnormal_RodWorth)

        # 9. 현 출력에서의 정지여유도 계산
        self.ShutdownMargin = para.TotalRodWorth - self.InoperableAbnormal_RodWorth - self.PowerDefect_Final
        print(self.ShutdownMargin)
        subdata.append(self.ShutdownMargin)
        self.shut.append(self.ShutdownMargin)

        # 10. 정지여유도 제한치를 만족하는지 비교
        if self.ShutdownMargin >= para.ShutdownMarginValue:
            self.label = "만족"
        else:
            self.label = "불만족"

        # with open('./data_save.txt', 'a') as f:
        #     f.write('{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n'.format(self.Time, self.PowerDefect_BOL,self.PowerDefect_EOL,self.PowerDefect_Burnup,
        #                                                               self.PowerDefect_Final, self.InoperableRodWorth, self.AbnormalRodWorth, self.InoperableAbnormal_RodWorth,
        #                                                               self.ShutdownMargin, self.label))


        if self.ShutdownMargin >= para.ShutdownMarginValue:
            self.result.append(1) #만족
            return print('만족'), subdata.append(1), subdata.append('ShutdownMargin'), self.data.append(subdata)
        else:
            self.result.append(0) #불만족
            return print('불만족'), subdata.append(0), subdata.append('ShutdownMargin'), self.data.append(subdata)


    def write(self):

        print(self.data)

    def Detect(self):

        # len(self.data)
        # print(len(self.data))
        # A=len(self.data)

        print(self.data[self.A-1][10])
        print(self.data[self.A-1][9])

        if self.data[self.A-1][10] == 'ShutdownMargin' and self.data[self.A-1][9] == 0 :
            self.Detect_bin = 'LCO 3.1.1'
            print('LCO 3.1.1')
        else:
            print('??')

    def Diagnosis(self):

        if self.Detect_bin == 'LCO 3.1.1':
            self.Diagnosis_bin=['LCO 3.1.1', 0]
            print(self.Diagnosis_bin)
        else :
            print('?')

    def Suggest(self):
        A = self.data[self.A - 1][8]
        B = 1770
        C = -5.9

        if self.Diagnosis_bin[0] == 'LCO 3.1.1' and self.Diagnosis_bin[1] == 0:
            boron=(A-B)/C
            self.boron_cons = 'KBCDO16'
            self.boron_cons_target = self.mem['KBCDO16']['Val']+boron
            self.boration = boron
            print('KBCDO16')
            print(self.mem['KBCDO16']['Val']+boron)
            print('boration: {}'.format(boron))

        else:
            print('??')

    def text(self):
        with open('./data_save.txt', 'a') as f:
            f.write('{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t\t{}\t{}\t\t{}\n'.format(self.Time, self.PowerDefect_BOL,self.PowerDefect_EOL,self.PowerDefect_Burnup,
                                                                      self.PowerDefect_Final, self.InoperableRodWorth, self.AbnormalRodWorth, self.InoperableAbnormal_RodWorth,
                                                                      self.ShutdownMargin, self.label, self.Detect_bin, self.boration, self.boron_cons, self.boron_cons_target))


if __name__ == '__main__':

    # unit test
    test = DataShare('192.168.0.192', 8001)  # current computer ip / port
    test.reset()
    test.make_gp()
    test.write()
    # test.Detect()
    # test.Diagnosis()
    # test.Suggest()
    # test.text()





