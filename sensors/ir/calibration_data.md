# Calibration Data and Analysis #

A dataset of 2100 data points was collected from robot #4 on 2014-03-06.

In the following `R` code, we find a third-order polynomial linear least squares regression. The use of the third-order polynomial is in no way a principled choice, but rather a practical assumption/simplification.


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
calib <- read.csv("calibration_data.csv", header = TRUE)
m <- lm(Distances ~ poly(Readings, 3, raw = TRUE), data = calib)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
> summary(m)

Call:
lm(formula = Distances ~ poly(Readings, 3, raw = TRUE), data = calib)

Residuals:
    Min      1Q  Median      3Q     Max 
-3.0520 -1.1882 -0.4838 -0.0494 13.7585 

Coefficients:
                                 Estimate Std. Error t value Pr(>|t|)    
(Intercept)                     1.005e+02  1.015e+00   98.98   <2e-16 ***
poly(Readings, 3, raw = TRUE)1 -2.811e-01  6.027e-03  -46.63   <2e-16 ***
poly(Readings, 3, raw = TRUE)2  3.148e-04  1.089e-05   28.90   <2e-16 ***
poly(Readings, 3, raw = TRUE)3 -1.254e-07  6.054e-09  -20.72   <2e-16 ***
---
Signif. codes:  0 ‘***’ 0.001 ‘**’ 0.01 ‘*’ 0.05 ‘.’ 0.1 ‘ ’ 1

Residual standard error: 2.293 on 2096 degrees of freedom
Multiple R-squared:  0.9643,	Adjusted R-squared:  0.9642 
F-statistic: 1.886e+04 on 3 and 2096 DF,  p-value: < 2.2e-16
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
> summary(calib$Readings)

   Min. 1st Qu.  Median    Mean 3rd Qu.    Max. 
  241.0   311.0   402.0   468.4   571.5  1023.0 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
xs <- seq(min(calib$Readings), max(calib$Readings))
ys <- predict(m, newdata = data.frame(Readings = xs))

plot(xs, ys, type = "l", xlab = "Readings", ylab = "Distances (cm)", lwd = 4, col = "blue")
points(calib$Readings, calib$Distances, lw = 0.3)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

![](img/calibration.svg)

Thus, for readings generated on Robot #4 in this range of values, i.e. the interval $[241, 1023]$, we can use the following third-order polynomial as an approximation for a mapping between readings and distances:

$$ c(d) = (-1.254 \cdot 10^{-7}) d^3 + (3.148 \cdot 10^{-4}) d^2 - (0.2811) d + 100.5 $$


In R, this can be implemented in either of the following ways, though the latter will introduce less error from floating-point operations.

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
conv <- function(d) {
    return (100.5 + (-0.2811) * d  + 3.148e-4 * d^2 + (-1.254e-7) * d^3)
}

conv <- function(d) {
    return (100.5 + d * (-0.2811 + d * (3.148e-4 + d * (-1.254e-7))))
}
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
