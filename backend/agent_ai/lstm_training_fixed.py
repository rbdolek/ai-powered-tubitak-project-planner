# agent_ai/lstm_training_fixed.py

import os
import pandas as pd
import numpy as np
import json
import re
import logging
import pyodbc
import sys
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Embedding, LSTM, Dense, Dropout, Bidirectional, GlobalMaxPooling1D
from sklearn.model_selection import train_test_split
import pickle
from datetime import datetime

# Karakter kodlama sorununu çözmek için
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

# Log konfigürasyonu - UTF-8 encoding kullanarak
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("lstm_training.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LSTMTraining")

class LSTMDataProcessor:
    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.data_dir = "agent_ai/lstm_training_data"
        os.makedirs(self.data_dir, exist_ok=True)
        
        logger.info("LSTMDataProcessor initialized")
    
    def connect_to_db(self):
        """Veritabanına bağlanır ve bir bağlantı nesnesi döndürür"""
        try:
            conn = pyodbc.connect(self.connection_string)
            logger.info("Database connection successful")
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
    
    def fetch_all_training_data(self):
        """Tüm eğitim verilerini çeker"""
        logger.info("Fetching all training data...")
        
        query = """
        SELECT 
            cm.id AS message_id,
            cm.content AS message_content,
            cm.is_user,
            cm.timestamp AS message_timestamp,
            cs.id AS session_id,
            cs.ai_model,
            cs.title AS session_title,
            ap.plan_metni AS response_content,
            ap.ay_suresi,
            ap.meta_data,
            f.kod AS fon_kod,
            f.tur AS fon_tur
        FROM 
            dbo.chat_chatmessage cm
        JOIN 
            dbo.chat_chatsession cs ON cm.session_id = cs.id
        LEFT JOIN 
            dbo.chat_aiplan ap ON cm.related_plan_id = ap.id
        LEFT JOIN 
            dbo.chat_fon f ON f.id = ap.fon_id
        WHERE 
            cm.is_user = 1
        ORDER BY 
            cs.created_at DESC, cm.timestamp ASC
        """
        
        try:
            conn = self.connect_to_db()
            df = pd.read_sql(query, conn)
            conn.close()
            
            logger.info(f"Found {len(df)} training data records")
            
            # Veriyi CSV olarak kaydet
            csv_path = os.path.join(self.data_dir, "all_training_data.csv")
            df.to_csv(csv_path, index=False, encoding='utf-8')
            logger.info(f"Data saved as CSV: {csv_path}")
            
            return df
        except Exception as e:
            logger.error(f"Error fetching data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def fetch_messages_with_feedback(self):
        """Geri bildirim puanı olan mesajları çeker"""
        logger.info("Fetching messages with feedback...")
        
        query = """
        SELECT 
            cm.id AS message_id,
            cm.content AS message_content,
            cm.is_user,
            cm.timestamp AS message_timestamp,
            cs.id AS session_id,
            cs.ai_model,
            uf.puan AS feedback_score,
            uf.yorum AS feedback_comment,
            ap.plan_metni AS plan_text,
            ap.ay_suresi,
            ap.meta_data,
            f.kod AS fon_kod,
            f.tur AS fon_tur
        FROM 
            dbo.chat_chatmessage cm
        JOIN 
            dbo.chat_chatsession cs ON cm.session_id = cs.id
        LEFT JOIN 
            dbo.chat_aiplan ap ON cm.related_plan_id = ap.id
        LEFT JOIN 
            dbo.chat_userfeedback uf ON uf.plan_id = ap.id
        LEFT JOIN 
            dbo.chat_fon f ON f.id = ap.fon_id
        WHERE 
            cm.is_user = 1
            AND uf.puan IS NOT NULL
        ORDER BY 
            uf.puan DESC, cm.timestamp DESC
        """
        
        try:
            conn = self.connect_to_db()
            df = pd.read_sql(query, conn)
            conn.close()
            
            logger.info(f"Found {len(df)} messages with feedback")
            
            # Veriyi CSV olarak kaydet
            csv_path = os.path.join(self.data_dir, "messages_with_feedback.csv")
            df.to_csv(csv_path, index=False, encoding='utf-8')
            logger.info(f"Data saved as CSV: {csv_path}")
            
            return df
        except Exception as e:
            logger.error(f"Error fetching feedback data: {str(e)}")
            return pd.DataFrame()
    
    def clean_text(self, text):
        """Metin temizleme"""
        if not isinstance(text, str):
            return ""
            
        # Küçük harfe çevir
        text = text.lower()
        
        # Gereksiz boşlukları temizle
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Özel karakterleri temizle (noktalama işaretleri hariç)
        text = re.sub(r'[^a-zA-ZçğıöşüÇĞİÖŞÜ0-9\s\.,;:!?]', '', text)
        
        return text
    
    def extract_ay_suresi(self, text):
        """Metinden ay süresini çıkar"""
        if not isinstance(text, str):
            return 0
            
        # Ay süresi içeren ifadeleri ara
        patterns = [
            r'(\d+)\s*ayl[ıi]k',  # örn: "6 aylık", "12aylık"
            r'(\d+)\s*ay',        # örn: "6 ay", "12ay"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    # İlk eşleşmeyi kullan
                    return int(matches[0])
                except ValueError:
                    pass
        
        return 0
    
    def prepare_training_data(self, df=None):
        """Verileri eğitim için hazırla"""
        logger.info("Training data preparation started")
        
        # Eğer veri yoksa, veritabanından çek
        if df is None or df.empty:
            df = self.fetch_all_training_data()
        
        if df.empty:
            logger.warning("No data available for preparation!")
            return None
        
        # Veriyi hazırla
        df['cleaned_message'] = df['message_content'].apply(self.clean_text)
        df['extracted_ay_suresi'] = df['message_content'].apply(self.extract_ay_suresi)
        
        # Ay süresini belirle - önce veritabanındaki değeri kullan, yoksa çıkarılanı
        df['ay_suresi'] = df.apply(
            lambda row: row['extracted_ay_suresi'] if pd.isna(row.get('ay_suresi')) or row.get('ay_suresi', 0) == 0 
                      else row.get('ay_suresi'), 
            axis=1
        )
        
        # Sınıf sayısını sınırla - en fazla 3 sınıf kullanalım (0, 1, 2)
        def simplified_class(ay_suresi):
            if pd.isna(ay_suresi) or ay_suresi == 0:
                return 0  # Bilinmeyen
            elif ay_suresi <= 6:
                return 1  # Kısa/orta (1-6 ay)
            else:
                return 2  # Uzun (6+ ay)
        
        df['class'] = df['ay_suresi'].apply(simplified_class)
        
        # Son sınıfları analiz edelim
        unique_classes = df['class'].unique()
        logger.info(f"Unique classes after simplification: {unique_classes}")
        
        # Verileri çoğalt - basit tekrarlama
        X = []
        y = []
        
        for _, row in df.iterrows():
            X.append(row['cleaned_message'])
            y.append(row['class'])
            
            # Her veriyi 2 kez tekrarlayalım (küçük veri seti için)
            X.append(row['cleaned_message'])
            y.append(row['class'])
        
        # Veri setini oluştur
        X = np.array(X)
        y = np.array(y)
        
        # Verileri karıştır
        indices = np.arange(len(X))
        np.random.shuffle(indices)
        X = X[indices]
        y = y[indices]
        
        # Eğitim ve test setlerine ayır
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Tokenizer oluştur ve eğit
        max_words = 5000  # Daha küçük bir kelime dağarcığı
        tokenizer = Tokenizer(num_words=max_words, oov_token='<OOV>')
        tokenizer.fit_on_texts(X_train)
        
        # Sekansları oluştur
        max_length = 50  # Daha kısa bir maksimum uzunluk
        X_train_seq = tokenizer.texts_to_sequences(X_train)
        X_test_seq = tokenizer.texts_to_sequences(X_test)
        
        # Padding uygula
        X_train_pad = pad_sequences(X_train_seq, maxlen=max_length, padding='post')
        X_test_pad = pad_sequences(X_test_seq, maxlen=max_length, padding='post')
        
        # Sınıf sayısını hesapla
        num_classes = len(np.unique(y))
        logger.info(f"Number of classes: {num_classes}")
        
        # Tokenizer'ı kaydet
        tokenizer_path = os.path.join(self.data_dir, "tokenizer.pickle")
        with open(tokenizer_path, 'wb') as handle:
            pickle.dump(tokenizer, handle, protocol=pickle.HIGHEST_PROTOCOL)
        
        # Eğitim verilerini kaydet
        np.save(os.path.join(self.data_dir, "X_train.npy"), X_train_pad)
        np.save(os.path.join(self.data_dir, "X_test.npy"), X_test_pad)
        np.save(os.path.join(self.data_dir, "y_train.npy"), y_train)
        np.save(os.path.join(self.data_dir, "y_test.npy"), y_test)
        
        # Özet bilgileri yaz
        class_meanings = {
            "0": "Bilinmeyen/Belirsiz",
            "1": "Kisa/Orta vadeli (1-6 ay)",
            "2": "Uzun vadeli (6+ ay)"
        }
        
        summary = {
            'vocab_size': len(tokenizer.word_index) + 1,
            'max_length': max_length,
            'max_words': max_words,
            'class_meanings': class_meanings,
            'num_classes': int(num_classes),
            'class_distribution': {
                'train': {str(i): int((y_train == i).sum()) for i in np.unique(y_train)},
                'test': {str(i): int((y_test == i).sum()) for i in np.unique(y_test)}
            },
            'num_samples': {
                'train': len(X_train),
                'test': len(X_test),
                'total': len(X)
            }
        }
        
        with open(os.path.join(self.data_dir, "data_summary.json"), 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Training data prepared: {summary['num_samples']}")
        
        return {
            'X_train': X_train_pad,
            'X_test': X_test_pad,
            'y_train': y_train,
            'y_test': y_test,
            'tokenizer': tokenizer,
            'summary': summary
        }
    
    def train_lstm_model(self, training_data=None):
        """LSTM modelini eğit"""
        logger.info("LSTM model training starting")
        
        # Eğitim verilerini yükle
        if training_data is None:
            try:
                X_train = np.load(os.path.join(self.data_dir, "X_train.npy"))
                X_test = np.load(os.path.join(self.data_dir, "X_test.npy"))
                y_train = np.load(os.path.join(self.data_dir, "y_train.npy"))
                y_test = np.load(os.path.join(self.data_dir, "y_test.npy"))
                
                with open(os.path.join(self.data_dir, "data_summary.json"), 'r', encoding='utf-8') as f:
                    summary = json.load(f)
                
                with open(os.path.join(self.data_dir, "tokenizer.pickle"), 'rb') as handle:
                    tokenizer = pickle.load(handle)
                
                logger.info("Saved training data loaded")
            except Exception as e:
                logger.error(f"Error loading training data: {str(e)}")
                return None, None
        else:
            X_train = training_data['X_train']
            X_test = training_data['X_test']
            y_train = training_data['y_train']
            y_test = training_data['y_test']
            tokenizer = training_data['tokenizer']
            summary = training_data['summary']
        
        # Sınıf sayısını kontrol et
        num_classes = summary.get('num_classes', 3)  # Varsayılan olarak 3 sınıf
        logger.info(f"Building model with {num_classes} output classes")
        
        # Model parametreleri
        vocab_size = summary['vocab_size']
        embedding_dim = 64  # Daha küçük embedding boyutu
        max_length = summary['max_length']
        
        # Daha basit bir model oluştur
        model = Sequential([
            Embedding(vocab_size, embedding_dim, input_length=max_length),
            Bidirectional(LSTM(32, return_sequences=True)),  # Daha küçük LSTM katmanı
            GlobalMaxPooling1D(),
            Dense(32, activation='relu'),
            Dropout(0.5),
            Dense(num_classes, activation='softmax')  # Sınıf sayısı kadar çıkış
        ])
        
        # Model derleme
        model.compile(
            loss='sparse_categorical_crossentropy',
            optimizer='adam',
            metrics=['accuracy']
        )
        
        # Model özeti
        model.summary()
        
        # Modeli kaydet (boş hali)
        model_dir = os.path.join(self.data_dir, "model")
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, "lstm_model_initial.h5")
        model.save(model_path)
        
        logger.info(f"Initial model saved: {model_path}")
        
        # Modeli eğit - daha az epoch
        epochs = 10
        batch_size = 2  # Çok küçük batch size
        
        logger.info(f"Training starting: {epochs} epochs, {batch_size} batch size")
        
        try:
            history = model.fit(
                X_train, y_train,
                epochs=epochs,
                batch_size=batch_size,
                validation_data=(X_test, y_test),
                verbose=1
            )
            
            # Eğitilmiş modeli kaydet
            trained_model_path = os.path.join(model_dir, "lstm_model.h5")
            model.save(trained_model_path)
            
            # Agent AI klasörüne kopyala
            agent_models_dir = "agent_ai/models"
            os.makedirs(agent_models_dir, exist_ok=True)
            model.save(os.path.join(agent_models_dir, "lstm_model.h5"))
            
            # Tokenizer'ı kopyala
            with open(os.path.join(agent_models_dir, "tokenizer.pickle"), 'wb') as handle:
                pickle.dump(tokenizer, handle, protocol=pickle.HIGHEST_PROTOCOL)
            
            # Eğitim geçmişini kaydet
            history_dict = {key: [float(x) for x in history.history[key]] for key in history.history.keys()}
            with open(os.path.join(model_dir, "training_history.json"), 'w', encoding='utf-8') as f:
                json.dump(history_dict, f, indent=2)
            
            # Model değerlendirmesi
            test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
            logger.info(f"Test accuracy: {test_acc:.4f}, Test loss: {test_loss:.4f}")
            
            return model, history
            
        except Exception as e:
            logger.error(f"Error during model training: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None, None

# Ana işlev
def main():
    # MS SQL bağlantı bilgileri
    connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=tubitak_db;Trusted_Connection=yes;'
    
    # Veri işleme sınıfını başlat
    data_processor = LSTMDataProcessor(connection_string)
    
    try:
        # Veri çekme ve hazırlama
        logger.info("Starting data extraction process")
        training_df = data_processor.fetch_all_training_data()
        
        # Eğitim verileri hazırla
        training_data = data_processor.prepare_training_data(training_df)
        
        # En azından birkaç örnek oluşturalım (veri yoksa)
        if training_data is None or training_data['X_train'].shape[0] < 4:
            logger.warning("Not enough training data, creating synthetic examples")
            
            # Örnek veriler
            examples = [
                {"text": "2247-B kapsamında 6 aylık bir araştırma planı hazırlar mısın?", "class": 1},
                {"text": "1 yıllık proje için TÜBİTAK planı oluştur", "class": 2},
                {"text": "3 aylık kısa bir akademik araştırma için plan yapar mısın?", "class": 1},
                {"text": "Proje önerisi hazırlamak istiyorum", "class": 0},
                {"text": "4 aylık araştırma planı", "class": 1},
                {"text": "TÜBİTAK 1001 projesi için 24 aylık iş paketi planlaması", "class": 2}
            ]
            
            # Manuel veri oluştur
            X = [ex["text"] for ex in examples]
            y = [ex["class"] for ex in examples]
            
            # Tokenizer
            tokenizer = Tokenizer(num_words=5000, oov_token='<OOV>')
            tokenizer.fit_on_texts(X)
            
            # Sekanslar
            X_seq = tokenizer.texts_to_sequences(X)
            max_length = 50
            X_pad = pad_sequences(X_seq, maxlen=max_length, padding='post')
            
            # Eğitim/test ayırma
            X_train, X_test, y_train, y_test = train_test_split(
                X_pad, y, test_size=0.2, random_state=42
            )
            
            # Summary
            summary = {
                'vocab_size': len(tokenizer.word_index) + 1,
                'max_length': max_length,
                'max_words': 5000,
                'num_classes': 3,
                'class_meanings': {
                    "0": "Bilinmeyen/Belirsiz",
                    "1": "Kisa/Orta vadeli (1-6 ay)",
                    "2": "Uzun vadeli (6+ ay)"
                }
            }
            
            # Training data
            training_data = {
                'X_train': X_train,
                'X_test': X_test,
                'y_train': np.array(y_train),
                'y_test': np.array(y_test),
                'tokenizer': tokenizer,
                'summary': summary
            }
        
        # Modeli eğit
        if training_data:
            model, history = data_processor.train_lstm_model(training_data)
            
            if model:
                logger.info("LSTM model successfully trained")
                
                # Test et
                test_texts = [
                    "2247-B kapsamında 6 aylık bir araştırma planı hazırlar mısın?",
                    "1 yıllık proje için TÜBİTAK planı oluştur",
                    "3 aylık kısa bir akademik araştırma için plan yapar mısın?"
                ]
                
                tokenizer = training_data['tokenizer']
                max_length = training_data['summary']['max_length']
                
                logger.info("Testing model with sample text")
                sequences = tokenizer.texts_to_sequences(test_texts)
                padded = pad_sequences(sequences, maxlen=max_length, padding='post')
                predictions = model.predict(padded)
                
                for i, text in enumerate(test_texts):
                    pred_class = np.argmax(predictions[i])
                    confidence = predictions[i][pred_class]
                    class_meaning = training_data['summary']['class_meanings'].get(str(pred_class), "Unknown")
                    
                    logger.info(f"Text: {text}")
                    logger.info(f"  Prediction: Class {pred_class} ({class_meaning}) - Confidence: {confidence:.4f}")
            else:
                logger.error("LSTM model training failed")
        else:
            logger.error("Failed to prepare training data")
            
    except Exception as e:
        logger.error(f"Unexpected error during process: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()