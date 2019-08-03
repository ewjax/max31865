# max31865
Python module to convert RTD PT100 resistance readings to temperature using the MAX31865 chip.

Usage is simple (shown assuming chip is wired to CE0 of SPI0, on Raspberry Pi):

    csPin   = 8
    misoPin = 9
    mosiPin = 10
    clkPin  = 11
    max     = max31865.max31865(csPin, misoPin, mosiPin, clkPin)
    
    tempC   = max.temperature()
Adapted from 'max31865' class as published by Stephen P. Smith on github in 2015.  This work is very much derivative from that starting point.

***Discussion***

Significant changes primarily revolve around the method to convert the resistance values as read from the RTD to a temperature value.  The Callendar-Van Dusen (hereafter, C-VD) equation is fundamentally a curve fit of resistance as a function of temperature, i.e.

​		***R = f(T)***

The curve fit equations are either a 2nd or 3rd order polynomial, depending on the Temperature.

However, if we are in the business of using an RTD to measure resistance, then what we really need is the ability to go the other way, i.e. we know R and we want T.  What is needed is temperature as a function of resistance, i.e.

​		***T = f(R)***

We're in luck if we happen to be in the temperature range where the C-VD equation is a 2nd order polynomial, because it is possible to use the quadratic equation to analytically solve the C-VD equation for T, given R.  This is the approach taken by most implementations found on the internet.  The difficulty of course is if the temperature happens to be in the range where the C-VD equation becomes a 3rd order polynomial, at which point there is no way to analytically solve for T given R, so most implementations just bail out and use a very rough linear fit to get vaguely in the ballpark, or else they import a math module and use it to solve for the roots of the 3rd order polynomial.

However, it is possible, and even straightforward, to simply use the C-VD equations to prepare a table of resistances and temperatures in a spreadsheet, then to simply perform a curve fit in the opposite direction, of what I call the inverse C-VD equation, i.e. create a fit of T as a function of R, rather than the C-VD fit of R as a function of T.  Turns out Excel will do a fit like this for you in a snap (it's a bit hidden, but it's there in the ***trend line*** functionality). The only question is, what order polynomial fit should be used?  Higher orders will of course give better fits across the entire range, but theoretically could take longer to solve the math, depending on the horsepower of whatever device is doing the math.  

So depending on performance needs, the spreadsheet creates three different fits.  A little time testing on the Raspberry Pi 3B and 3B+ models indicates there is essentially no performance loss when using the 5th order fit compared to the others, so the 5th order fit is the default in this implementation.  However, the 3rd and 4th order fits are left in there, in case they are needed for a less manly device.



***Fifth Order Fit:***

Curve fit

​		`temp_C = (c5 * res^5) + (c4 * res^4) + (c3 * res^3) + (c2 * res^2) + (c1 * res) + c0`

where

        c5  = -9.2833E-12
        c4  =  1.2506E-08
        c3  = -4.9960E-06
        c2  =  1.9435E-03
        c1  =  2.2729E+00
        c0  = -2.4297E+02
Fitting error over range [-200C to 850C]

​		0.01 degC average, 0.24 degC maximum

Usage (these are equivalent)

​        `tempC = max.temperature() `
​		`tempC = max.temperature_poly5()`



***Fourth Order Fit:***

Curve fit

​		`temp_C = (c4 * res^4) + (c3 * res^3) + (c2 * res^2) + (c1 * res) + c0`

where

```
    c4  =  2.9401E-09
    c3  = -1.4136E-06
    c2  =  1.3543E-03
    c1  =  2.3132E+00
    c0  = -2.4381E+02
```

Fitting error over range [-200C to 850C]

​		0.01 degC average, 0.51 degC maximum

Usage

​		`tempC = max.temperature_poly4()`



***Third Order Fit:***

Curve fit

​		`temp_C = (c3 * res^3) + (c2 * res^2) + (c1 * res) + c0`

where

        c3  =  1.0154E-06
        c2  =  6.8975E-04
        c1  =  2.3803E+00
        c0  = -2.4568E+02
   Fitting error over range [-200C to 850C]

​		0.01 degC average, 1.35 degC maximum

Usage

​		`tempC = max.temperature_poly3()`



Copyright (c) 2019 Elliott W. Jackson


