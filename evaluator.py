import os
import joblib
import librosa
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, classification_report

# Silence TensorFlow logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

from keras.models import load_model
from engine import MentalHealthEngine
from tqdm import tqdm

def generate_performance_report():
    print("🚀 Starting CNN Audio Model Evaluation...")
    engine = MentalHealthEngine()
    
    # 1. Paths from your engine.py
    model_path = engine.model_path 
    label_path = engine.label_encoder_path

    if not os.path.exists(model_path):
        print(f"❌ Error: {model_path} not found!")
        return
    
    # Load Model and Encoder
    model = load_model(model_path)
    label_encoder = joblib.load(label_path)
    print("🧠 CNN Model and Labels loaded successfully.")

    # 2. RAVDESS Mapping
    emotion_map = {"01": "neutral", "03": "happy", "04": "sad", "05": "angry", "06": "fear"}
    
    y_true = []
    y_pred = []
    
    # Scan RAVDESS directory
    audio_files = []
    for root, _, files in os.walk(engine.ravdess_path):
        for file in files:
            if file.endswith(".wav"):
                parts = file.split("-")
                if len(parts) > 2 and parts[2] in emotion_map:
                    audio_files.append((os.path.join(root, file), parts[2]))

    if not audio_files:
        print(f"⚠️ No files found in {engine.ravdess_path}")
        return

    print(f"📊 Analyzing {len(audio_files)} files...")

    # 3. Prediction Loop
    for file_path, emotion_code in tqdm(audio_files, desc="CNN Processing"):
        try:
            # Load audio
            y_audio, sr = librosa.load(file_path, duration=2.5, offset=0.5)
            
            # Use the new helper function we added to engine.py
            features = engine.extract_features_for_eval(y_audio, sr)
            
            # Reshape for your CNN: (1, 40, 1)
            features_reshaped = features.reshape(1, 40, 1)
            
            # Get Prediction
            predictions = model.predict(features_reshaped, verbose=0)
            predicted_index = np.argmax(predictions, axis=1)
            predicted_label = label_encoder.inverse_transform(predicted_index)[0]
            
            y_true.append(emotion_map[emotion_code])
            y_pred.append(predicted_label)
            
        except Exception as e:
            print(f"\n❌ Skipping {os.path.basename(file_path)} due to error: {e}")
            continue

    # 4. Generate Visuals
    if not y_true:
        print("❌ No data collected. Evaluation failed.")
        return

    labels = label_encoder.classes_ 
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=labels, yticklabels=labels)
    plt.title('CNN Clinical Emotion - Confusion Matrix')
    plt.xlabel('AI Predicted Emotion')
    plt.ylabel('Actual Label (RAVDESS)')
    
    plt.tight_layout()
    plt.savefig('cnn_confusion_matrix.png', dpi=300)
    print("\n✅ CNN Matrix saved as 'cnn_confusion_matrix.png'")
    
    # 5. Classification Report
    print("\n--- CNN Classification Report ---")
    print(classification_report(y_true, y_pred, target_names=labels))
    plt.show()

if __name__ == "__main__":
    generate_performance_report()