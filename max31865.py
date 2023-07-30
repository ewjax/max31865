#!/usr/bin/python

import logging
import time, math
import RPi.GPIO as GPIO
import threading


# version number
__VERSION__ = '1.0.0.2-dev.2'


#
# class max31865
#
# a class to handle the MAX 31865 amplifier for converting PT100 RTD readings from resistance to temperature
#
# adapted from 'max31865' class as published by Stephen P. Smith on github in 2015
#
#   - refactored slightly to break apart the functions of 
#           a) reading the RTD resistance, and
#           b) converting that resistance to a temperature
#           c) this was done to allow multiple methods of performing the conversion of Resistance to Temperature
#   - added several polynomial fits to provide the conversion from Resistance to Temperature
#           a) 3rd order (fitting error = 0.0 degC average, 0.98 degC maximum, over range [-200C to 660C]
#           b) 4th order (fitting error = 0.0 degC average, 0.39 degC maximum, over range [-200C to 660C]
#           c) 5th order (fitting error = 0.0 degC average, 0.13 degC maximum, over range [-200C to 660C]
#           d) the default = the 5th order fit, since the performance difference on my RPi 3B and 3B+ is absolutely negligible,
#              but the others can be called if you are using a slower device
#
# Copyright (c) 2019 Elliott W. Jackson
#
class max31865(object):

    # ctor
    # defaults are for Raspberry Pi BCM pin numbers for SPI0
    def __init__(self, csPin = 8, misoPin = 9, mosiPin = 10, clkPin = 11):
        self.csPin = csPin
        self.misoPin = misoPin
        self.mosiPin = mosiPin
        self.clkPin = clkPin
        self.setupGPIO()

        self.goodreads = 0
        self.badreads = 0

        # threading lock for critical regions
        self.lock = threading.RLock()
#        self.logger = logging.getLogger(self.__class__.__name__)


    def __del__(self):
        print('csPin = {}: goodreads = {}, badreads = {}'.format(self.csPin, self.goodreads, self.badreads))

    def setupGPIO(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.csPin, GPIO.OUT)
        GPIO.setup(self.misoPin, GPIO.IN)
        GPIO.setup(self.mosiPin, GPIO.OUT)
        GPIO.setup(self.clkPin, GPIO.OUT)

        GPIO.output(self.csPin, GPIO.HIGH)
        GPIO.output(self.clkPin, GPIO.LOW)
        GPIO.output(self.mosiPin, GPIO.LOW)



    def writeRegister(self, regNum, dataByte):
        GPIO.output(self.csPin, GPIO.LOW)
        
        # 0x8x to specify 'write register value'
        addressByte = 0x80 | regNum;
        
        # first byte is address byte
        self.sendByte(addressByte)
        # the rest are data bytes
        self.sendByte(dataByte)

        GPIO.output(self.csPin, GPIO.HIGH)
        

    def readRegisters(self, regNumStart, numRegisters):
        out = []
        GPIO.output(self.csPin, GPIO.LOW)
        
        # 0x to specify 'read register value'
        self.sendByte(regNumStart)
        
        for byte in range(numRegisters):    
            data = self.recvByte()
            out.append(data)

        GPIO.output(self.csPin, GPIO.HIGH)
        return out


    def sendByte(self, byte):
        for bit in range(8):
            GPIO.output(self.clkPin, GPIO.HIGH)
            if (byte & 0x80):
                GPIO.output(self.mosiPin, GPIO.HIGH)
            else:
                GPIO.output(self.mosiPin, GPIO.LOW)
            byte <<= 1
            GPIO.output(self.clkPin, GPIO.LOW)


    def recvByte(self):
        byte = 0x00
        for bit in range(8):
            GPIO.output(self.clkPin, GPIO.HIGH)
            byte <<= 1
            if GPIO.input(self.misoPin):
                byte |= 0x1
            GPIO.output(self.clkPin, GPIO.LOW)
        return byte    
    
    #
    # function to read the resistance value of the RTD
    #
    def readRTD(self):
        #
        # 10000000 = 0x80
        # 0x8x to specify 'write register value'
        # 0xx0 to specify 'configuration register'
        #
        # Config Register
        # ---------------
        # 1.......  1 = Vbias On
        # .0......  0 = Conversion Manual
        # ..1.....  1 = One shot mode (auto clear)
        # ...1....  1 = 3 wire RTD
        # ....00..  00 = fault detection cycle control
        # ......1.  1 = fault status auto clear
        # .......0  0 = 60 Hz
        # --------
        # 10110010  0xB2
        #
        # Auto conversion = 11010010 = 0xD2
        #

        # threading lock
        self.lock.acquire()

        #one shot
        self.writeRegister(0, 0xB2)

        # wait
#        time.sleep(0)
#        time.sleep(0.0005)
#        time.sleep(0.001)
        time.sleep(0.005)
#        time.sleep(0.010)
#        time.sleep(0.020)
#        time.sleep(0.1)
#        time.sleep(0.5)

        # read all registers
        out = self.readRegisters(0, 8)

        # release the thread lock
        self.lock.release()

        # config register
        conf_reg = out[0]
#        self.logger.debug('config register byte: 0x{:X}'.format(conf_reg))

        # RTD data
        [rtd_msb, rtd_lsb] = [out[1], out[2]]
        rtd_ADC_Code = (( rtd_msb << 8 ) | rtd_lsb ) >> 1
#        self.logger.debug('RTD ADC Code: {:d}'.format(rtd_ADC_Code))

        # convert the RTD value to RTD resistance
        R_REF = 430.0                                   # Reference Resistor on PT100 31865 amplifier
        Res_RTD = (rtd_ADC_Code * R_REF) / 32768.0      # PT100 Resistance
#        self.logger.debug('RTD resistance: {:f} ohms'.format(Res_RTD))
            
        # high fault threshold
        [hft_msb, hft_lsb] = [out[3], out[4]]
        hft = (( hft_msb << 8 ) | hft_lsb ) >> 1
#        self.logger.debug('high fault threshold: {:d}'.format(hft))

        # low fault threshold
        [lft_msb, lft_lsb] = [out[5], out[6]]
        lft = (( lft_msb << 8 ) | lft_lsb ) >> 1
#        self.logger.debug('low fault threshold: {:d}'.format(lft))

        # fault status register
        status = out[7]
        #
        # 10 Mohm resistor is on breakout board to help
        # detect cable faults
        # bit 7: RTD High Threshold / cable fault open 
        # bit 6: RTD Low Threshold / cable fault short
        # bit 5: REFIN- > 0.85 x VBias -> must be requested
        # bit 4: REFIN- < 0.85 x VBias (FORCE- open) -> must be requested
        # bit 3: RTDIN- < 0.85 x VBias (FORCE- open) -> must be requested
        # bit 2: Overvoltage / undervoltage fault
        # bits 1,0 don't care    
#        self.logger.debug('Status {:d}'.format(status))

        if status == 0:
            self.goodreads += 1
        else:
            self.badreads += 1

        # return the RTD resistance
        rv = Res_RTD
        return (rv, status)
        


    #
    # convert RTD reading to Temperature, using quadratic solution to Callendar-Van Dusen equation, which defines Resistance as a function of Temperature
    #
    # returns temperature, in celcius
    #
    def temperature_CVD(self):

        # get RTD resistance
        (res, status) = self.readRTD()

        a       = .00390830
        b       = -.000000577500
        Res0    = 100.0; # Resistance at 0 degC for 430 ohm R_Ref

        # use quadratic equation to solve for temp given resistance
        temp_C = -(a*Res0) + math.sqrt(a*a*Res0*Res0 - 4*(b*Res0)*(Res0 - res))
        temp_C = temp_C / (2*(b*Res0))

#        self.logger.debug('Callendar-Van Dusen Temp (degC > 0): {:f} degC, {:f} degF'.format(temp_C, c2f(temp_C)))
        return (temp_C, status)



    #
    # convert RTD reading to Temperature, using 3rd order polynomial fit of Temperature as a function of Resistance
    #
    #   temp_C = (c3 * res^3) + (c2 * res^2) + (c1 * res) + c0
    #
    # rearrange a bit to make it friendlier (less expensive) to calculate
    #
    #   temp_C = res ( res ( res * c3 + c2) + c1) + c0
    #
    # returns temperature, in celcius
    #
    def temperature_poly3(self):

        # coeffs for 3rd order fit
        c3  =  7.00406E-07
        c2  =  8.47800E-04
        c1  =  2.35841E+00
        c0  = -2.44950E+02

        # get RTD resistance
        (res, status) = self.readRTD()

        # do the math
        #   temp_C = res ( res ( res ( res * c4 + c3) + c2) + c1) + c0
        temp_C = res * c3 + c2

        temp_C *= res
        temp_C += c1

        temp_C *= res
        temp_C += c0

#        self.logger.debug('3rd order poly fit Temp: {:f} degC, {:f} degF'.format(temp_C, c2f(temp_C)))
        return (temp_C, status)


    #
    # convert RTD reading to Temperature, using 4th order polynomial fit of Temperature as a function of Resistance
    #
    #   temp_C = (c4 * res^4) + (c3 * res^3) + (c2 * res^2) + (c1 * res) + c0
    #
    # rearrange a bit to make it friendlier (less expensive) to calculate
    #
    #   temp_C = res ( res ( res ( res * c4 + c3) + c2) + c1) + c0
    #
    # returns temperature, in celcius
    #
    def temperature_poly4(self):

        # coeffs for 4th order fit
        c4  =  4.11530E-09
        c3  = -2.21378E-06
        c2  =  1.53359E-03
        c1  =  2.29835E+00
        c0  = -2.43465E+02

        # get RTD resistance
        (res, status) = self.readRTD()

        # do the math
        #   temp_C = res ( res ( res ( res * c4 + c3) + c2) + c1) + c0
        temp_C = res * c4 + c3

        temp_C *= res
        temp_C += c2

        temp_C *= res
        temp_C += c1

        temp_C *= res
        temp_C += c0

#        self.logger.debug('4th order poly fit Temp: {:f} degC, {:f} degF'.format(temp_C, c2f(temp_C)))
        return (temp_C, status)


    #
    # convert RTD reading to Temperature, using 5th order polynomial fit of Temperature as a function of Resistance
    #
    #   temp_C = (c5 * res^5) + (c4 * res^4) + (c3 * res^3) + (c2 * res^2) + (c1 * res) + c0
    #
    # rearrange a bit to make it friendlier (less expensive) to calculate
    #
    #   temp_C = res ( res ( res ( res ( res * c5 + c4) + c3) + c2) + c1) + c0
    #
    # returns temperature, in celcius
    #
    def temperature_poly5(self):

        # coeffs for 5th order fit
        c5  = -2.10678E-11
        c4  =  2.27311E-08
        c3  = -8.20888E-06
        c2  =  2.38589E-03
        c1  =  2.24745E+00
        c0  = -2.42522E+02

        # get RTD resistance
        (res, status) = self.readRTD()

        # do the math
        #   temp_C = res ( res ( res ( res ( res * c5 + c4) + c3) + c2) + c1) + c0
        temp_C = res * c5 + c4

        temp_C *= res
        temp_C += c3

        temp_C *= res
        temp_C += c2

        temp_C *= res
        temp_C += c1

        temp_C *= res
        temp_C += c0

#        self.logger.debug('5th order poly fit Temp: {:f} degC, {:f} degF'.format(temp_C, c2f(temp_C)))
        return (temp_C, status)

    #
    # default = the 5th order polynomial fit of inverse CVD
    #
    # returns temperature, in celcius
    #
    def temperature(self):
        (temp_C, status) = self.temperature_poly5()
        return (temp_C, status)



#
# helper function just to convert celsius to Fahrenheit
#
def c2f(degC):
    degF = (9.0 / 5.0 * degC) + 32.0
    return degF


#
# 
#
def main():

    import max31865
    import timeit

#    logging.basicConfig(level=logging.DEBUG)


    # create instance of RTD reader class
#    csPin = 5
    csPin   = 8
    misoPin = 9
    mosiPin = 10
    clkPin  = 11
    max     = max31865.max31865(csPin, misoPin, mosiPin, clkPin)


    for cnt in range(0, 1000):
        (tempC, status) = max.temperature()


#
#    # do some timing.  
#    #
#    # Note that the time is completely dominated by the 10 millisecond sleep() call buried in the readRTD() function
#    # in other words, using the polynomial form to solve inverse Callander-Van Dusen adds negligible time to processing
#    def f1():
#        tempC = max.temperature_CVD()
#
#    def f2():
#        tempC = max.temperature_poly3()
#
#    def f3():
#        tempC = max.temperature_poly4()
#
#    def f4():
#        tempC = max.temperature_poly5()
#
#    def f5():
#        tempC = max.temperature()
#
#    nn = 10
#    duration = timeit.timeit(f1, number = nn)
#    print('{} calls to temperature_CVD duration = {:0.5}, Per-call = {:.5}'.format(nn, duration, duration/nn))
#    duration = timeit.timeit(f2, number = nn)
#    print('{} calls to temperature_poly3 duration = {:0.5}, Per-call = {:.5}'.format(nn, duration, duration/nn))
#    duration = timeit.timeit(f3, number = nn)
#    print('{} calls to temperature_poly4 duration = {:0.5}, Per-call = {:.5}'.format(nn, duration, duration/nn))
#    duration = timeit.timeit(f4, number = nn)
#    print('{} calls to temperature_poly5 duration = {:0.5}, Per-call = {:.5}'.format(nn, duration, duration/nn))
#    duration = timeit.timeit(f4, number = nn)
#    print('{} calls to temperature duration = {:0.5}, Per-call = {:.5}'.format(nn, duration, duration/nn))
#
#
#
#    # turn on debugging within the class member functions - comment out to remove these diagnostics
##    logging.basicConfig(level=logging.DEBUG)
#
#
#    tempC = max.temperature_CVD()
#    print('Callendar-Van Dusen Temp: {:.5} degC, {:.5} degF'.format(tempC, c2f(tempC)))
#
#    tempC = max.temperature_poly3()
#    print('3rd Order Poly Fit Temp: {:.5} degC, {:.5} degF'.format(tempC, c2f(tempC)))
#
#    tempC = max.temperature_poly4()
#    print('4th Order Poly Fit Temp: {:.5} degC, {:.5} degF'.format(tempC, c2f(tempC)))
#
#    tempC = max.temperature_poly5()
#    print('5th Order Poly Fit Temp: {:.5} degC, {:.5} degF'.format(tempC, c2f(tempC)))
#
#    tempC = max.temperature()
#    print('5th Order Poly Fit Temp: {:.5} degC, {:.5} degF'.format(tempC, c2f(tempC)))
#

    GPIO.cleanup()


if __name__ == '__main__':
    main()

