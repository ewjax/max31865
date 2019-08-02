# max31865
Perl module to convert RTD PT100 resistance readings to temperature using the MAX31865 chip



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
#           a) 3rd order (fitting error = .01 degC average, 1.35 degC maximum, over range [-200C to 850C]
#           b) 4th order (fitting error = .01 degC average, .51 degC maximum, over range [-200C to 850C]
#           c) 5th order (fitting error = .01 degC average, .24 degC maximum, over range [-200C to 850C]
#           d) the default = the 5th order fit, since the performance difference on my RPi 3B and 3B+ is absolutely negligible,
#              but the others can be called if you are using a slower device
#
# Copyright (c) 2019 Elliott W. Jackson
#

