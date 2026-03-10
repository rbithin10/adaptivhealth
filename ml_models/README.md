# ml_models/ — Machine Learning Model Files

Contains the trained cardiac risk prediction model, its training scripts, and supporting data files. The model predicts a patient's cardiac risk score based on their vitals, medical history, and lifestyle factors.

## Training Scripts

| File | What It Does |
|------|-------------|
| `train_tflite_model.py` | Trains the risk prediction model and exports it for on-device use (TFLite format) |
| `convert_to_tflite.py` | Converts an existing model to TensorFlow Lite format for mobile deployment |

## Model & Data Files

| File | What It Contains |
|------|-----------------|
| `risk_model.pkl` | The trained scikit-learn risk prediction model (pickle format) |
| `scaler.pkl` | Feature scaler — normalises input values so the model gets consistent data |
| `scaler_params.json` | Human-readable version of the scaler parameters (means, standard deviations) |
| `feature_columns.json` | List of input features the model expects (e.g. age, heart_rate, blood_pressure) |
| `model_metadata.json` | Model version, training date, accuracy metrics, and configuration |
| `tree_ensemble.json` | Internal tree structure of the ensemble model (for explainability) |
