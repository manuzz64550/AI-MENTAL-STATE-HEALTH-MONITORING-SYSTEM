import pandas as pd
import numpy as np
from sklearn.neural_network import MLPRegressor
import joblib

# 1. Data
X = np.random.uniform(0, 100, (1000, 3))
y = (X[:, 2] * 0.5 + X[:, 1] * 0.3 + X[:, 0] * 0.2)

# 2. Train a simple Neural Network (MLP)
# This does exactly what the Keras model does but without TensorFlow errors
model = MLPRegressor(hidden_layer_sizes=(16, 8), max_iter=500)
model.fit(X, y)

# 3. Save as a .pkl file (similar to your audio labels)
joblib.dump(model, 'fusion_brain.pkl')
print("Fusion Brain saved as fusion_brain.pkl using Scikit-Learn!")