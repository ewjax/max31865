# max31865
Python module to convert RTD PT100 resistance readings to temperature using the MAX31865 chip.

Copyright (c) 2019 Elliott W. Jackson

Usage is simple (shown assuming chip is wired to CE0 of SPI0, on Raspberry Pi):

    csPin   = 8
    misoPin = 9
    mosiPin = 10
    clkPin  = 11
    max     = max31865.max31865(csPin, misoPin, mosiPin, clkPin)
    
    tempC   = max.temperature()



***Discussion***

This work is adapted from 'max31865' class as published by Stephen P. Smith, https://github.com/steve71/MAX31865.  Significant changes primarily revolve around the method to convert the resistance values as read from the RTD to a temperature value.  

The venerable Callendar-Van Dusen (hereafter, C-VD) equation is fundamentally a curve fit of resistance as a function of temperature, i.e.

​			***R = f(T)***

The curve fit equations are either a 2nd or 3rd order polynomial, depending on the Temperature.

However, if we are in the business of using an RTD to measure resistance, then what we really need is the ability to go the other way, i.e. we know R and we want T.  What is needed is temperature as a function of resistance, i.e.

​			***T = f(R)***

We're in luck if we happen to be in the temperature range where the C-VD equation is a 2nd order polynomial, because it is possible to use the quadratic equation to analytically solve the C-VD equation for T, given R.  This is the approach taken by many implementations found on the internet.  The difficulty of course is if the temperature happens to be in the range where the C-VD equation becomes a 3rd order polynomial, at which point there is no way to analytically solve for T given R, so most implementations just bail out and claim they just don't work for temperatures < 0C, or they use a very rough linear fit to get vaguely in the ballpark, or else they import a math module (like the Python numpy module) and use it to solve for the roots of the 3rd order polynomial, which can really be time consuming expensive, depending on the horsepower of whatever device is running the calculation.

However, rather than jumping through these hoops to solve the C-VD equations backward, perhaps a better approach might be to simply create a new curve fit that provides exactly what is needed, i.e. a curve fit that that provide T given R.  

To accomplish that, it is reasonably straightforward to create a table of raw temperature and RTD resistance data in a spreadsheet, and use that data to perform the desired curve fit, using a least-squares fitting tool of some kind, or even just Excel.  The raw data can be obtained from various DIN IEC 751 documents that can be found on the internet (see one in '*reference/Pt_RTD_LakeShore.pdf*').  Excel can easily generate the desired polynomial fits (it's a bit hidden, but it's there in the ***trendline*** functionality for scatter plots). The only question is, what order polynomial fit should be used?  Higher orders will of course give better fits across the entire range, but theoretically could take longer to solve the math.

So depending on performance needs, the spreadsheet creates three different fits.  A little time testing on the Raspberry Pi 3B and 3B+ models indicates there is essentially no performance loss when using the 5th order fit compared to the others, so the 5th order fit is the default in this implementation.  However, the 3rd and 4th order fits are left in there, in case they are needed for a less manly device.  The spreadsheet can be seen in '*reference/RTD Transfer Function.xlsx*'.

(*Note: there is a decent discussion of this entire approach buried in the 'reference/AN709_0.pdf' document, although that author elected to keep the quadratic solution of the C-VD fits for temperature ranges > 0C, and only created fits for the temperature/resistance data for ranges < 0C.  The implementation in this module dispenses entirely with C-VD, and simply creates fits across the entire range of temperature data, from [-200C, 660C].*)  



***Fifth Order Fit:***

Curve fit

​		`temp_C = (c5 * res^5) + (c4 * res^4) + (c3 * res^3) + (c2 * res^2) + (c1 * res) + c0`

where

            c5  = -2.10678E-11
            c4  =  2.27311E-08
            c3  = -8.20888E-06
            c2  =  2.38589E-03
            c1  =  2.24745E+00
            c0  = -2.42522E+02
Fitting error over range [-200C to 660C]

​		0.00 degC average, 0.13 degC maximum

Usage (these are equivalent)

```
       tempC = max.temperature()
       tempC = max.temperature_poly5()
```



***Fourth Order Fit:***

Curve fit

​		`temp_C = (c4 * res^4) + (c3 * res^3) + (c2 * res^2) + (c1 * res) + c0`

where

```
        c4  =  4.11530E-09
        c3  = -2.21378E-06
        c2  =  1.53359E-03
        c1  =  2.29835E+00
        c0  = -2.43465E+02
```

Fitting error over range [-200C to 660C]

​		0.00 degC average, 0.39 degC maximum

Usage

​		`tempC = max.temperature_poly4()`



***Third Order Fit:***

Curve fit

​		`temp_C = (c3 * res^3) + (c2 * res^2) + (c1 * res) + c0`

where

            c3  =  7.00406E-07
            c2  =  8.47800E-04
            c1  =  2.35841E+00
            c0  = -2.44950E+02

Fitting error over range [-200C to 660C]

​		0.00 degC average, 0.98 degC maximum

Usage

​		`tempC = max.temperature_poly3()`








