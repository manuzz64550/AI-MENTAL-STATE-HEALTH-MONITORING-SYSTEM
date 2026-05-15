import os
import io
import librosa
import numpy as np
import pandas as pd
import joblib
import plotly.graph_objects as go

# Modern 2026 Imports (Keras 3)
import keras
from keras.models import Sequential, load_model
from keras.layers import Conv1D, MaxPooling1D, Flatten, Dense, Dropout

from sklearn.preprocessing import LabelEncoder
from sklearn.naive_bayes import MultinomialNB
from sklearn.feature_extraction.text import TfidfVectorizer
from deepface import DeepFace
from PIL import Image

class MentalHealthEngine:
    def __init__(self):
        # 1. Essential Paths
        self.model_path = "audio_cnn_model.h5" 
        self.label_encoder_path = "audio_labels.pkl"
        self.ravdess_path = "ravdess_data/"
        self.text_data_path = "Combined Data.csv"
        self.fusion_brain_path = "fusion_brain.pkl" # <--- Path for your new AI brain
        
        # 2. Initialize Linguistic Components
        self.vectorizer = TfidfVectorizer(max_features=2000)
        self.text_model = None
        
        # 3. Initialize Visual Detector 
        self.detector = "DeepFace" 
        
        # 4. Initialize Audio Classifier
        self.audio_classifier = self.load_audio_engine()
        
        if os.path.exists(self.label_encoder_path):
            self.label_encoder = joblib.load(self.label_encoder_path)
        else:
            self.label_encoder = None

        # 5. Initialize Fusion Brain (The New AI)
        if os.path.exists(self.fusion_brain_path):
            self.fusion_brain = joblib.load(self.fusion_brain_path)
            print("Fusion Brain: AI Meta-Model Loaded Successfully")
        else:
            self.fusion_brain = None
            print("Fusion Brain: Model not found, using fallback math.")
        
        # 6. Run Initial Training for Text
        self.train_text_model()

    # --- NEW: AI FUSION LOGIC ---
    def calculate_fused_risk(self, v_score, a_score, t_score):
        """Replaces manual math with the Neural Network Brain"""
        if self.fusion_brain:
            try:
                # Format features for the MLPRegressor
                features = np.array([[v_score, a_score, t_score]])
                prediction = self.fusion_brain.predict(features)
                return float(np.clip(prediction[0], 0, 100))
            except:
                return (t_score * 0.5) + (a_score * 0.3) + (v_score * 0.2)
        else:
            # Fallback if .pkl is missing
            return (t_score * 0.5) + (a_score * 0.3) + (v_score * 0.2)

    # --- ACOUSTIC ENGINE (1D-CNN) ---
    def build_cnn_model(self, input_shape, num_classes):
        model = Sequential([
            Conv1D(64, 5, padding='same', activation='relu', input_shape=input_shape),
            MaxPooling1D(pool_size=5, strides=2, padding='same'),
            Conv1D(128, 5, padding='same', activation='relu'),
            MaxPooling1D(pool_size=5, strides=2, padding='same'),
            Dropout(0.3),
            Flatten(),
            Dense(256, activation='relu'),
            Dense(num_classes, activation='softmax')
        ])
        model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
        return model
    def extract_features_for_eval(self, y_audio, sr):
        """Helper for evaluator.py to ensure identical feature extraction"""
        mfccs = np.mean(librosa.feature.mfcc(y=y_audio, sr=sr, n_mfcc=40).T, axis=0)
        return mfccs
    
    def train_audio_engine(self):
        X, y = [], []
        emotion_map = {"03": "happy", "04": "sad", "05": "angry", "06": "fear", "01": "neutral"}
        
        if not os.path.exists(self.ravdess_path):
            return False

        for root, _, files in os.walk(self.ravdess_path):
            for file in files:
                if file.endswith(".wav"):
                    parts = file.split("-")
                    if len(parts) > 2 and parts[2] in emotion_map:
                        try:
                            y_audio, sr = librosa.load(os.path.join(root, file), duration=2.5, offset=0.5)
                            mfccs = np.mean(librosa.feature.mfcc(y=y_audio, sr=sr, n_mfcc=40).T, axis=0)
                            X.append(mfccs)
                            y.append(emotion_map[parts[2]])
                        except: continue

        if X:
            X = np.expand_dims(np.array(X), axis=2)
            le = LabelEncoder()
            y_encoded = le.fit_transform(y)
            self.audio_classifier = self.build_cnn_model((40, 1), len(le.classes_))
            self.audio_classifier.fit(X, y_encoded, epochs=50, batch_size=32, verbose=0)
            
            self.audio_classifier.save(self.model_path)
            joblib.dump(le, self.label_encoder_path)
            self.label_encoder = le
            return True
        return False

    def predict_audio_sentiment(self, audio_file):
        try:
            if self.audio_classifier is None: return "Neutral", 30.0
            audio_file.seek(0)
            y_audio, sr = librosa.load(io.BytesIO(audio_file.read()), duration=3)
            
            # SILENCE CHECK
            rms = np.mean(librosa.feature.rms(y=y_audio))
            if rms < 0.005:
                return "Neutral (Silence)", 30.0

            mfccs = np.mean(librosa.feature.mfcc(y=y_audio, sr=sr, n_mfcc=40).T, axis=0)
            features = mfccs.reshape(1, 40, 1)
            
            pred_probs = self.audio_classifier.predict(features, verbose=0)
            pred_idx = np.argmax(pred_probs)
            prediction = self.label_encoder.inverse_transform([pred_idx])[0]
            
            risk_table = {"sad": 85.0, "fear": 90.0, "angry": 75.0, "happy": 15.0, "neutral": 30.0}
            return prediction.capitalize(), risk_table.get(prediction.lower(), 30.0)
            
        except Exception as e:
            print(f"Audio Prediction Error: {e}")
            return "Neutral", 30.0

    # --- VISUAL ENGINE (DeepFace) ---
    def detect_face_emotion(self, img_file):
        try:
            with open("temp_face.jpg", "wb") as f:
                f.write(img_file.getbuffer())
            
            results = DeepFace.analyze(
                img_path="temp_face.jpg", 
                actions=['emotion'], 
                enforce_detection=True, 
                detector_backend='opencv'
            )
            
            if results:
                res = results[0]
                top_emo = res['dominant_emotion']
                prob = res['emotion'][top_emo]
                return top_emo.capitalize(), f"Dominant: {top_emo} ({prob:.1f}%)", prob
                
        except ValueError:
            return "Neutral", "No face detected - Please look at the camera", 0.0
        except Exception as e:
            return "Neutral", f"Sensor Error: {str(e)}", 0.0
        
        return "Neutral", "No face detected", 0.0

    # --- LINGUISTIC ENGINE ---
    def train_text_model(self):
        try:
            if os.path.exists(self.text_data_path):
                df = pd.read_csv(self.text_data_path).dropna(subset=['statement'])
                X = self.vectorizer.fit_transform(df['statement'].astype(str))
                self.text_model = MultinomialNB()
                self.text_model.fit(X, df['status'])
        except Exception as e:
            print(f"Text Training Error: {e}")

    def predict_mood_text(self, text):
        if self.text_model is None: return "Neutral"
        try:
            vec_text = self.vectorizer.transform([text])
            return str(self.text_model.predict(vec_text)[0])
        except:
            return "Neutral"

    # --- VISUALIZATIONS ---
    def plot_risk_trend(self, df):
        if df is None or len(df) == 0: return go.Figure()
        try:
            trend_df = df.copy()
            trend_df['Timestamp'] = pd.to_datetime(trend_df['Timestamp'], errors='coerce')
            trend_df = trend_df.dropna(subset=['Timestamp']).sort_values('Timestamp')
            trend_df['Risk_Score'] = trend_df['Risk_Index'].apply(lambda x: float(str(x).replace('%', '')))
            fig = go.Figure(go.Scatter(x=trend_df['Timestamp'], y=trend_df['Risk_Score'], mode='lines+markers', line=dict(color='#00e676', width=3)))
            fig.update_layout(title="Patient Risk Volatility", template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            return fig
        except: return go.Figure()

    def plot_explainable_ai(self, v_risk, a_risk, t_risk):
        components = ['Visual Affect', 'Acoustic Tone', 'Linguistic Intent']
        # We visualize the raw risk scores from each sensor
        scores = [v_risk, a_risk, t_risk] 
        fig = go.Figure(go.Bar(x=scores, y=components, orientation='h', marker_color=['#3b82f6', '#10b981', '#f59e0b']))
        fig.update_layout(title="Sensor Risk Inputs (Pre-Fusion)", template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", height=300)
        return fig

    def plot_professional_fused_risk(self, risk_score, user_name):
        colors = ['#00e676', '#ffea00', '#ff9100', '#ff1744']
        active_color = colors[3] if risk_score >= 75 else colors[2] if risk_score >= 50 else colors[1] if risk_score >= 25 else colors[0]
        fig = go.Figure(data=[go.Pie(values=[risk_score, 100-risk_score], hole=.85, marker_colors=[active_color, '#333'], textinfo='none', sort=False)])
        fig.update_layout(title=f"Patient: {user_name}", paper_bgcolor='rgba(0,0,0,0)', showlegend=False,
                          annotations=[dict(text=f"{risk_score:.1f}%", x=0.5, y=0.5, font_size=40, showarrow=False)])
        return fig

    def get_pro_advice(self, mood, masking):
        if masking: return "High clinical priority: Detected emotional masking."
        advice = {"depression": "Immediate clinical review recommended.", "anxiety": "Recommended: Box breathing (4-4-4-4).", "suicidal": "CRITICAL: Trigger emergency protocol."}
        return advice.get(mood.lower(), "Continue regular monitoring.")

    def load_audio_engine(self):
        if os.path.exists(self.model_path):
            try:
                return load_model(self.model_path)
            except Exception as e:
                print(f"Model Load Error: {e}")
                return None
        return None