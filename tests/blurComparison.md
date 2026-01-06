# Blur Comparison

For our solution, we set up a testing program to compare several blurring methods. From this test code, we received the following results:

```yaml
Method       | Avg fg MOG2  | Avg fg KNN   | Contours M2  | Contours KNN
----------------------------------------------------------------------
original     | 5011.1       | 13847.7      | 285.2        | 1025.7      
gaussian     | 4867.7       | 12197.8      | 245.8        | 818.9       
median       | 4654.4       | 11180.7      | 240.7        | 572.9       
clahe        | 14703.5      | 72949.3      | 1441.4       | 13128.0     
hsv_v        | 5779.2       | 57761.4      | 604.7        | 7828.0       
```

---
## 1. Median has the lowest foreground pixels

Lower foreground pixels indicate less noise.

|Method|Avg FG (MOG2)|Conclusion|
|---|---|---|
|Median|4654|Best at noise removal|
|Gaussian|4867|Acceptable|
|Original|5011|Worse|
|CLAHE|14703|Very noisy|
|HSV|5779|High noise|

Median shows the best performance for noise reduction.

---

## 2. Median has the fewest contours

Lower contour counts indicate fewer false detections.

|Method|Contours (MOG2)|Conclusion|
|---|---|---|
|Median|240|Most stable, fewest false positives|
|Gaussian|245|Acceptable|
|Original|285|Worse|
|CLAHE|1441|Very noisy|
|HSV|604|High noise|

Median again performs best.

---

## 3. KNN results confirm the pattern

KNN is generally noisier, but relative differences highlight the best preprocessing method.

|Method|Contours (KNN)|Conclusion|
|---|---|---|
|Median|572|Best|
|Gaussian|818|Acceptable|
|Original|1025|Worse|
|CLAHE|13128|Extremely noisy|
|HSV|7828|Very noisy|

Median provides the most stable results across both MOG2 and KNN.

---

## Conclusion

Based on the metrics:

- Median Blur produces the lowest noise levels.
- Median Blur results in the fewest false contours.
- Median Blur is consistent across both MOG2 and KNN algorithms.
- Median Blur improves stability without losing significant details.


**Recommendation:** Use Median Blur as the pre-processing method for our traffic monitoring system.
