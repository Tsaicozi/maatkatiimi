"""
Deep Learning -mallit markkinoiden ennustamiseen
Enhanced Ideation Crew v2.0 - Osa 2
"""

import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
import joblib
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential, Model
    from tensorflow.keras.layers import LSTM, Dense, Dropout, Input, MultiHeadAttention, LayerNormalization
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("TensorFlow ei ole asennettu. Asenna: pip install tensorflow")

class DeepLearningPredictor:
    """Deep Learning -mallit markkinoiden ennustamiseen"""
    
    def __init__(self):
        self.scaler = MinMaxScaler()
        self.models = {}
        self.tensorflow_available = TENSORFLOW_AVAILABLE
    
    def prepare_data(self, data: pd.DataFrame, sequence_length: int = 60) -> Tuple[np.ndarray, np.ndarray]:
        """Valmistele data LSTM-mallille"""
        try:
            # Valitse ominaisuudet
            features = ['Open', 'High', 'Low', 'Close', 'Volume']
            if all(col in data.columns for col in features):
                df = data[features].copy()
            else:
                df = data[['Close']].copy()
            
            # Normalisoi data
            scaled_data = self.scaler.fit_transform(df)
            
            # Luo sekvenssit
            X, y = [], []
            for i in range(sequence_length, len(scaled_data)):
                X.append(scaled_data[i-sequence_length:i])
                y.append(scaled_data[i, 0])  # Ennusta Close-hinta
            
            return np.array(X), np.array(y)
            
        except Exception as e:
            print(f"Virhe datan valmistelussa: {e}")
            return np.array([]), np.array([])
    
    def create_lstm_model(self, input_shape: Tuple[int, int]) -> Sequential:
        """Luo LSTM-malli"""
        if not self.tensorflow_available:
            raise ImportError("TensorFlow ei ole saatavilla")
        
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(50, return_sequences=True),
            Dropout(0.2),
            LSTM(50),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])
        
        model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
        return model
    
    def create_transformer_model(self, input_shape: Tuple[int, int]) -> Model:
        """Luo Transformer-malli"""
        if not self.tensorflow_available:
            raise ImportError("TensorFlow ei ole saatavilla")
        
        # Input layer
        inputs = Input(shape=input_shape)
        
        # Multi-head attention
        attention = MultiHeadAttention(num_heads=8, key_dim=64)(inputs, inputs)
        attention = Dropout(0.1)(attention)
        
        # Add & Norm
        attention = LayerNormalization(epsilon=1e-6)(inputs + attention)
        
        # Feed forward
        ffn = Dense(128, activation='relu')(attention)
        ffn = Dense(input_shape[1])(ffn)
        ffn = Dropout(0.1)(ffn)
        
        # Add & Norm
        output = LayerNormalization(epsilon=1e-6)(attention + ffn)
        
        # Global average pooling ja output
        output = tf.keras.layers.GlobalAveragePooling1D()(output)
        output = Dense(64, activation='relu')(output)
        output = Dropout(0.2)(output)
        output = Dense(1)(output)
        
        model = Model(inputs=inputs, outputs=output)
        model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
        
        return model
    
    def train_lstm_model(self, symbol: str, period: str = "2y") -> Dict:
        """Kouluta LSTM-malli symbolille"""
        try:
            if not self.tensorflow_available:
                return {'error': 'TensorFlow ei ole saatavilla'}
            
            # Hae data
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            if len(data) < 100:
                return {'error': f'Liian vähän dataa symbolille {symbol}'}
            
            # Valmistele data
            X, y = self.prepare_data(data, sequence_length=60)
            
            if len(X) == 0:
                return {'error': 'Datan valmistelu epäonnistui'}
            
            # Jaa data
            split = int(0.8 * len(X))
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]
            
            # Luo ja kouluta malli
            model = self.create_lstm_model((X.shape[1], X.shape[2]))
            
            # Callbacks
            callbacks = [
                EarlyStopping(patience=10, restore_best_weights=True),
                ReduceLROnPlateau(factor=0.5, patience=5)
            ]
            
            # Kouluta
            history = model.fit(
                X_train, y_train,
                epochs=50,
                batch_size=32,
                validation_data=(X_test, y_test),
                callbacks=callbacks,
                verbose=0
            )
            
            # Ennusta
            predictions = model.predict(X_test, verbose=0)
            
            # Laske metriikat
            mse = mean_squared_error(y_test, predictions)
            mae = mean_absolute_error(y_test, predictions)
            
            # Tallenna malli
            self.models[f'{symbol}_lstm'] = model
            
            return {
                'symbol': symbol,
                'model_type': 'LSTM',
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'mse': float(mse),
                'mae': float(mae),
                'rmse': float(np.sqrt(mse)),
                'final_loss': float(history.history['loss'][-1]),
                'final_val_loss': float(history.history['val_loss'][-1])
            }
            
        except Exception as e:
            return {'error': f'Virhe LSTM-koulutuksessa: {str(e)}'}
    
    def train_transformer_model(self, symbol: str, period: str = "2y") -> Dict:
        """Kouluta Transformer-malli symbolille"""
        try:
            if not self.tensorflow_available:
                return {'error': 'TensorFlow ei ole saatavilla'}
            
            # Hae data
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            if len(data) < 100:
                return {'error': f'Liian vähän dataa symbolille {symbol}'}
            
            # Valmistele data
            X, y = self.prepare_data(data, sequence_length=60)
            
            if len(X) == 0:
                return {'error': 'Datan valmistelu epäonnistui'}
            
            # Jaa data
            split = int(0.8 * len(X))
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]
            
            # Luo ja kouluta malli
            model = self.create_transformer_model((X.shape[1], X.shape[2]))
            
            # Callbacks
            callbacks = [
                EarlyStopping(patience=10, restore_best_weights=True),
                ReduceLROnPlateau(factor=0.5, patience=5)
            ]
            
            # Kouluta
            history = model.fit(
                X_train, y_train,
                epochs=50,
                batch_size=32,
                validation_data=(X_test, y_test),
                callbacks=callbacks,
                verbose=0
            )
            
            # Ennusta
            predictions = model.predict(X_test, verbose=0)
            
            # Laske metriikat
            mse = mean_squared_error(y_test, predictions)
            mae = mean_absolute_error(y_test, predictions)
            
            # Tallenna malli
            self.models[f'{symbol}_transformer'] = model
            
            return {
                'symbol': symbol,
                'model_type': 'Transformer',
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'mse': float(mse),
                'mae': float(mae),
                'rmse': float(np.sqrt(mse)),
                'final_loss': float(history.history['loss'][-1]),
                'final_val_loss': float(history.history['val_loss'][-1])
            }
            
        except Exception as e:
            return {'error': f'Virhe Transformer-koulutuksessa: {str(e)}'}
    
    def predict_future_prices(self, symbol: str, days: int = 30, model_type: str = 'lstm') -> Dict:
        """Ennusta tulevia hintoja"""
        try:
            model_key = f'{symbol}_{model_type}'
            if model_key not in self.models:
                return {'error': f'Malli {model_key} ei ole koulutettu'}
            
            model = self.models[model_key]
            
            # Hae viimeisimmät data
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="3mo")
            
            if len(data) < 60:
                return {'error': 'Liian vähän dataa ennustamiseen'}
            
            # Valmistele data
            features = ['Open', 'High', 'Low', 'Close', 'Volume']
            if all(col in data.columns for col in features):
                df = data[features].copy()
            else:
                df = data[['Close']].copy()
            
            # Normalisoi
            scaled_data = self.scaler.fit_transform(df)
            
            # Ennusta
            predictions = []
            current_sequence = scaled_data[-60:].reshape(1, 60, -1)
            
            for _ in range(days):
                pred = model.predict(current_sequence, verbose=0)[0, 0]
                predictions.append(pred)
                
                # Päivitä sekvenssi
                new_row = np.zeros((1, 1, current_sequence.shape[2]))
                new_row[0, 0, 0] = pred  # Aseta ennuste Close-sarakkeeseen
                current_sequence = np.concatenate([current_sequence[:, 1:, :], new_row], axis=1)
            
            # Muunna takaisin alkuperäiseen skaalaan
            predictions = self.scaler.inverse_transform(
                np.array(predictions).reshape(-1, 1)
            ).flatten()
            
            current_price = data['Close'].iloc[-1]
            expected_return = (predictions[-1] - current_price) / current_price * 100
            
            return {
                'symbol': symbol,
                'model_type': model_type,
                'current_price': float(current_price),
                'predicted_prices': [float(p) for p in predictions],
                'final_predicted_price': float(predictions[-1]),
                'expected_return_percent': float(expected_return),
                'prediction_days': days,
                'confidence': self._calculate_confidence(predictions, current_price)
            }
            
        except Exception as e:
            return {'error': f'Virhe ennustamisessa: {str(e)}'}
    
    def _calculate_confidence(self, predictions: np.ndarray, current_price: float) -> str:
        """Laske luottamustaso ennusteelle"""
        volatility = np.std(predictions) / np.mean(predictions)
        
        if volatility < 0.05:
            return "Korkea"
        elif volatility < 0.1:
            return "Kohtalainen"
        else:
            return "Matala"
    
    def compare_models(self, symbol: str) -> Dict:
        """Vertaa LSTM ja Transformer -mallien suorituskykyä"""
        try:
            lstm_result = self.train_lstm_model(symbol)
            transformer_result = self.train_transformer_model(symbol)
            
            if 'error' in lstm_result or 'error' in transformer_result:
                return {
                    'error': 'Mallien vertailu epäonnistui',
                    'lstm_error': lstm_result.get('error'),
                    'transformer_error': transformer_result.get('error')
                }
            
            # Valitse parempi malli
            better_model = 'LSTM' if lstm_result['rmse'] < transformer_result['rmse'] else 'Transformer'
            
            return {
                'symbol': symbol,
                'lstm_performance': lstm_result,
                'transformer_performance': transformer_result,
                'better_model': better_model,
                'performance_difference': abs(lstm_result['rmse'] - transformer_result['rmse'])
            }
            
        except Exception as e:
            return {'error': f'Virhe mallien vertailussa: {str(e)}'}

# Testaa työkalu
if __name__ == "__main__":
    if TENSORFLOW_AVAILABLE:
        predictor = DeepLearningPredictor()
        
        print("=== LSTM-MALLI ===")
        lstm_result = predictor.train_lstm_model("AAPL", period="1y")
        print(f"LSTM-tulos: {lstm_result}")
        
        if 'error' not in lstm_result:
            print("\n=== LSTM-ENNUSTEET ===")
            prediction = predictor.predict_future_prices("AAPL", days=30, model_type='lstm')
            print(f"Ennuste: {prediction}")
        
        print("\n=== TRANSFORMER-MALLI ===")
        transformer_result = predictor.train_transformer_model("AAPL", period="1y")
        print(f"Transformer-tulos: {transformer_result}")
        
        if 'error' not in transformer_result:
            print("\n=== TRANSFORMER-ENNUSTEET ===")
            prediction = predictor.predict_future_prices("AAPL", days=30, model_type='transformer')
            print(f"Ennuste: {prediction}")
        
        print("\n=== MALLIEN VERTAILU ===")
        comparison = predictor.compare_models("AAPL")
        print(f"Vertailu: {comparison}")
    else:
        print("TensorFlow ei ole asennettu. Asenna: pip install tensorflow")


