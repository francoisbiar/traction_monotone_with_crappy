import numpy as np
import matplotlib.pyplot as plt
import cv2

mat = plt.imread('image_0.tif')

print mat.shape

mat_cp = np.zeros(mat.shape)
mat_cp[mat > 60] = 1

plt.imshow(mat_cp, cmap='Greys')
plt.colorbar()
plt.show()
