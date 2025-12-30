# Morphology Comparison

Morphological image processing is a group of operations that modify the shape of objects in a binary image using a small structuring element (kernel). Typical operations are erosion, dilation, opening and closing, which can merge nearby blobs, fill small gaps or remove tiny noise while preserving overall object structure. In this project morphology is applied to the foreground mask after background subtraction to better isolate vehicle blobs and suppress road lights and small reflections. 

In this test a fixed pre-processing pipeline (LAB + CLAHE + gain + median blur) and MOG2/KNN background subtraction are used to generate a base foreground mask. Different morphology pipelines are then applied to the same mask to measure their impact on foreground pixels and contour count over a sequence of highway frames.

---

## Tested morphology variants



The following pipelines were evaluated on the AND-combined foreground mask (MOG2 ∧ KNN).

- **no_morph**: raw foreground mask without any morphology.
- **Close_only**: one closing operation with a 9x9 elliptical kernel to merge split headlights and fill gaps inside vehicles.
- **Close-dilate**: closing followed by dilation with a 7X7 kernel to further connect fragmented parts of the same vehicle. 
- **Full_pipeline**: Closing-> Dilation-> opening(3X3 kernel, 3 iterations) -> erosion (1X1 kernel) to merge headlights, connect vehicle blobs, remove small road lights and clean residual edge noise.

The evolution of the metrics per frame is shown in the figures below. 

Foreground pixels vs frame

![](..\tests\morphology_output\fg_pixels.png)

- Contour count vs frame

  ![](..\tests\morphology_output\contours.png)

  ---

  ## Summary results

  The average values over all processed frames are summarised in the table.

  ```
  | Variant       | Avg fg px | Avg contours |
  |---------------|-----------|--------------|
  | no_morph      | 326.3     | 77.1         |
  | close_only    | 467.5     | 65.9         |
  | close_dilate  | 3148.6    | 49.9         |
  | full_pipeline | 2706.9    | 51.2         |
  
  ```

- **No_morph**: has the lowest foreground pixels but the highest contour count, meaning many small noisy blobs and fragmented vehicles.
- **Close_only**: slightly increases foreground pixels while reducing contour count, indicating better merging of split headlights but still leaving several small objects.
- **Close_dilate** and **Full_pipeline** produce far more foreground pixels but substantially fewer contours, showing that small fragments are merged into larger, more stable vehicle blobs.
- The **Full_pipeline**: slightly reduces foreground pixels compared to close_dilate while keeping a similar contour count, which indicates that opening and erosion remove some remaining noise without breaking vehicles apart.

---

The kernel sizes and iteration counts used in these morphology pipelines were not chosen arbitrarily but tuned experimentally on multiple highway sequences. Different kernel shapes and sizes were tested, and for the current camera viewpoint, resolution and lighting conditions, the selected values provide the best balance between merging headlights of the same vehicle and avoiding unwanted merging of adjacent vehicles or road structures.