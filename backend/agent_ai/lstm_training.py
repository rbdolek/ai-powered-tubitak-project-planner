# agent_ai/lstm_db_train.py
import os
import sys
import io
import re
import numpy as np
import pandas as pd
import tensorflow as tf
import pyodbc
import json
import pickle
import logging
import traceback
from datetime import datetime
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, LSTM, Dense, Dropout, Bidirectional, GlobalMaxPooling1D
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau

# UTF-8 karakter desteğini sağla
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Günlük ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_ai/lstm_training.log", encoding='utf-8'),
        logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8'))
    ]
)

logger = logging.getLogger("LSTMTraining")

class LSTMDataProcessor:
    """LSTM eğitimi için veri işleme sınıfı"""
    
    def __init__(self, connection_string=None):
        """Veri işleyiciyi başlat"""
        self.connection_string = connection_string or 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=tubitak_db;Trusted_Connection=yes;'
        self.training_dir = 'agent_ai/lstm_training_data'
        self.model_dir = 'agent_ai/models'
        
        # Dizinleri oluştur
        os.makedirs(self.training_dir, exist_ok=True)
        os.makedirs(os.path.join(self.training_dir, 'model'), exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)
        
        logger.info("LSTMDataProcessor başlatıldı")
    
    def connect_to_db(self):
        """Veritabanına bağlan"""
        try:
            conn = pyodbc.connect(self.connection_string)
            logger.info("Veritabanı bağlantısı başarılı")
            return conn
        except Exception as e:
            logger.error(f"Veritabanı bağlantı hatası: {str(e)}")
            raise
    
    def fetch_plans_with_feedback(self):
        """Geri bildirim puanı olan planları çek"""
        logger.info("Geri bildirim puanı olan planları çekiyorum...")
        
        # Düzeltilmiş sorgu - feedback tablosundan planları çek
        query = """
        SELECT 
            f.id AS feedback_id,
            f.puan AS feedback_score,
            f.yorum AS feedback_comment,
            f.olusturma_tarihi AS feedback_date,
            p.id AS plan_id,
            p.plan_metni AS plan_text,
            p.ay_suresi AS duration_months,
            p.meta_data,
            s.id AS session_id,
            s.title AS session_title,
            s.ai_model,
            fon.kod AS fon_code,
            fon.tur AS fon_type
        FROM 
            dbo.chat_userfeedback f
        JOIN 
            dbo.chat_aiplan p ON f.plan_id = p.id
        LEFT JOIN 
            dbo.chat_chatsession s ON s.plan_id = p.id
        LEFT JOIN 
            dbo.chat_fon fon ON p.fon_id = fon.id
        WHERE 
            f.puan IS NOT NULL
        ORDER BY 
            f.puan DESC, f.olusturma_tarihi DESC
        """
        
        try:
            conn = self.connect_to_db()
            df = pd.read_sql(query, conn)
            conn.close()
            
            logger.info(f"{len(df)} adet geri bildirimli plan bulundu")
            
            # CSV olarak kaydet
            csv_path = os.path.join(self.training_dir, 'plans_with_feedback.csv')
            df.to_csv(csv_path, index=False, encoding='utf-8')
            logger.info(f"Veriler CSV olarak kaydedildi: {csv_path}")
            
            return df
        except Exception as e:
            logger.error(f"Geri bildirimli planlar çekilirken hata: {str(e)}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def fetch_all_plans(self):
        """Tüm proje planlarını çek"""
        logger.info("Tüm plan verilerini çekiyorum...")
        
        # Düzeltilmiş sorgu - tüm planları çek
        query = """
        SELECT 
            p.id AS plan_id,
            p.plan_metni AS plan_text,
            p.ay_suresi AS duration_months,
            p.olusturma_tarihi AS created_at,
            p.meta_data,
            p.feedback_score,
            s.id AS session_id,
            s.title AS session_title,
            s.ai_model,
            fon.kod AS fon_code,
            fon.tur AS fon_type
        FROM 
            dbo.chat_aiplan p
        LEFT JOIN 
            dbo.chat_chatsession s ON s.plan_id = p.id
        LEFT JOIN 
            dbo.chat_fon fon ON p.fon_id = fon.id
        ORDER BY 
            p.olusturma_tarihi DESC
        """
        
        try:
            conn = self.connect_to_db()
            df = pd.read_sql(query, conn)
            conn.close()
            
            logger.info(f"{len(df)} adet plan verisi bulundu")
            
            # CSV olarak kaydet
            csv_path = os.path.join(self.training_dir, 'all_plans.csv')
            df.to_csv(csv_path, index=False, encoding='utf-8')
            logger.info(f"Veriler CSV olarak kaydedildi: {csv_path}")
            
            return df
        except Exception as e:
            logger.error(f"Plan verileri çekilirken hata: {str(e)}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def extract_query_from_title(self, title):
        """Oturum başlığından sorguyu çıkar"""
        # Fon kodunu kaldır (örn: "2209-A - Proje Başlığı" -> "Proje Başlığı")
        if title and re.match(r'\d{4}(-[A-Z])?\s*-\s*', title):
            return re.sub(r'^\d{4}(-[A-Z])?\s*-\s*', '', title)
        return title
    
    def extract_fon_info(self, text):
        """Metinden fon bilgisini çıkar"""
        # Fon kodu çıkarma (örn: 2209-A, 1001, vb.)
        fon_pattern = r'\b(\d{4}(?:-[A-Z])?)\b'
        fon_match = re.search(fon_pattern, text)
        fon_code = fon_match.group(1) if fon_match else ""
        
        # Ay süresi çıkarma
        month_pattern = r'(\d+)\s*ayl[ıi]k'
        month_match = re.search(month_pattern, text, re.IGNORECASE)
        months = int(month_match.group(1)) if month_match else 0
        
        return fon_code, months
    
    def determine_plan_class(self, months):
        """Ay süresine göre plan sınıfını belirle"""
        if months <= 0:
            return 0  # Belirsiz
        elif months <= 3:
            return 1  # Kısa vadeli
        elif months <= 6:
            return 2  # Orta vadeli
        else:
            return 3  # Uzun vadeli
    
    def prepare_training_data(self):
        """Eğitim verilerini hazırla"""
        logger.info("Eğitim verileri hazırlanıyor...")
        
        # Planları çek
        df = self.fetch_all_plans()
        
        if len(df) == 0:
            logger.warning("Veritabanında plan verisi bulunamadı!")
            # Manuel veri seti oluştur
            return self.create_manual_training_data()
        
        # Veri ön işleme
        # Boş değerleri doldur
        df['feedback_score'] = df['feedback_score'].fillna(0)
        df['duration_months'] = df['duration_months'].fillna(0)
        
        # Fon bilgilerini eksik olanlar için çıkar
        for idx, row in df.iterrows():
            if pd.isna(row['fon_code']) or not row['fon_code']:
                # Session title'dan veya meta_data'dan çıkarmaya çalış
                title = row['session_title'] if pd.notna(row['session_title']) else ""
                fon_code, months = self.extract_fon_info(title)
                
                if fon_code:
                    df.at[idx, 'fon_code'] = fon_code
                
                if row['duration_months'] <= 0 and months > 0:
                    df.at[idx, 'duration_months'] = months
        
        # Plan sınıflarını belirle
        df['plan_class'] = df['duration_months'].apply(self.determine_plan_class)
        
        # Sorgu oluştur (session_title'dan)
        df['query'] = df['session_title'].apply(lambda x: self.extract_query_from_title(x) if pd.notna(x) else "")
        
        # Geçersiz verileri filtrele
        df = df[df['plan_text'].notna() & (df['plan_text'] != "")]
        
        # Eğitim verileri için liste oluştur
        texts = []
        labels = []
        
        for _, row in df.iterrows():
            # Sorgu + fon kodu + ay süresi ifadesi oluştur
            query_text = row['query']
            fon_code = row['fon_code'] if pd.notna(row['fon_code']) else ""
            months = row['duration_months'] if pd.notna(row['duration_months']) else 0
            
            # Girdi metni oluştur
            if fon_code and months > 0:
                input_text = f"{query_text} için TÜBİTAK {fon_code} {months} aylık plan"
            elif fon_code:
                input_text = f"{query_text} için TÜBİTAK {fon_code} projesi"
            elif months > 0:
                input_text = f"{query_text} için {months} aylık plan"
            else:
                input_text = query_text
            
            texts.append(input_text)
            labels.append(row['plan_class'])
        
        # Veri seti çok küçükse manuel veri ile destekle
        if len(texts) < 20:
            logger.warning(f"Yetersiz veri: Sadece {len(texts)} örnek bulundu. Manuel veri eklenecek.")
            manual_texts, manual_labels = self.create_manual_training_data_only()
            texts.extend(manual_texts)
            labels.extend(manual_labels)
        
        # Eğitim ve test verilerini böl
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.2, random_state=42, stratify=labels if len(set(labels)) > 1 else None
        )
        
        # Veri kümelerini kaydet
        data = {
            'train': {
                'texts': X_train,
                'labels': y_train
            },
            'test': {
                'texts': X_test,
                'labels': y_test
            },
            'all': {
                'texts': texts,
                'labels': labels
            }
        }
        
        # JSON olarak kaydet
        json_path = os.path.join(self.training_dir, 'training_data.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Özet bilgileri
        summary = {
            'num_samples': {
                'train': len(X_train),
                'test': len(X_test),
                'total': len(texts)
            },
            'class_distribution': {
                'train': {str(c): y_train.count(c) for c in set(y_train)},
                'test': {str(c): y_test.count(c) for c in set(y_test)},
                'all': {str(c): labels.count(c) for c in set(labels)}
            }
        }
        
        logger.info(f"Eğitim verileri hazırlandı: {summary['num_samples']}")
        return data
    
    def create_manual_training_data_only(self):
        """Sadece manuel eğitim veri seti oluştur"""
        # Kategoriler ve örnek ifadeleri
        categories = {
            0: ["genel bilgi", "tavsiye", "proje fikri", "araştırma önerisi"],
            1: ["kısa vadeli plan", "3 aylık proje", "küçük ölçekli çalışma", "1 aylık", "2 aylık", "3 aylık"],
            2: ["orta vadeli plan", "6 aylık proje", "orta ölçekli çalışma", "4 aylık", "5 aylık", "6 aylık"],
            3: ["uzun vadeli plan", "12 aylık proje", "büyük ölçekli çalışma", "yıllık plan", "18 aylık", "24 aylık"]
        }
        
        # TÜBİTAK Fon Kodları
        fon_codes = ["1001", "1002", "1005", "2209-A", "2209-B", "3501", "4004", "4005", "1007"]
        
        # Araştırma Alanları
        research_areas = [
            "yapay zeka", "makine öğrenmesi", "veri bilimi", "robotik", "otomasyon",
            "yenilenebilir enerji", "sürdürülebilirlik", "iklim değişikliği", "çevre yönetimi",
            "sağlık teknolojileri", "biyomedikal", "teşhis sistemleri", "uzaktan sağlık",
            "akıllı şehirler", "nesnelerin interneti", "sensör ağları", "akıllı ulaşım",
            "tarım teknolojileri", "akıllı tarım", "gıda güvenliği", "hassas tarım",
            "malzeme bilimi", "nanoteknoloji", "kompozit malzemeler", "yenilikçi malzemeler"
        ]
        
        # Soru Formatları
        question_formats = [
            "{} için {} planı oluşturabilir misin?",
            "{} projesi için {} plan yapar mısın?",
            "{} üzerine {} proje planı istiyorum",
            "{} konusunda {} bir TÜBİTAK projesi nasıl yapılır?",
            "TÜBİTAK {} fonu için {} planlama",
            "{} odaklı {} proje önerin"
        ]
        
        # Verileri topla
        all_texts = []
        all_labels = []
        
        # 1. Fon + Süre kombinasyonları
        for label, duration_terms in categories.items():
            for fon in fon_codes:
                for duration in duration_terms:
                    for format in question_formats[:3]:  # Fon + süre için uygun formatlar
                        text = format.format(f"TÜBİTAK {fon}", duration)
                        all_texts.append(text)
                        all_labels.append(label)
        
        # 2. Araştırma Alanı + Süre kombinasyonları
        for label, duration_terms in categories.items():
            for area in research_areas:
                for duration in duration_terms[:2]:  # Her kategori için ilk 2 süre terimi
                    for format in question_formats[2:]:  # Araştırma + süre için uygun formatlar
                        text = format.format(area, duration)
                        all_texts.append(text)
                        all_labels.append(label)
        
        # 3. Karmaşık sorgular
        complex_queries = [
            # Genel (Kategori 0)
            "TÜBİTAK projeleri için önerileriniz nelerdir?",
            "Yapay zeka projesinde nelere dikkat etmeliyim?",
            "Bir araştırma projesi nasıl yazılır?",
            "TÜBİTAK 1001 için önemli hususlar nelerdir?",
            "Proje yazarken dikkat edilmesi gerekenler",
            "TÜBİTAK değerlendirme kriterleri nelerdir?",
            
            # Kısa Vadeli (Kategori 1)
            "3 aylık hızlı bir araştırma projesi yapmak istiyorum",
            "TÜBİTAK 1002 için 3 aylık plan oluşturur musun?",
            "Kısa vadeli bir 2209-A projesi planlıyorum",
            "Kısa süreli akıllı şehirler projesi için öneri",
            "Hızlı bir prototip için 2 aylık plan",
            "Üç aylık dönemde tamamlanacak nanoteknoloji projesi",
            
            # Orta Vadeli (Kategori 2)
            "6 aylık bir makine öğrenmesi projesi planlamak istiyorum",
            "TÜBİTAK 2209-A için 5 aylık plan yapar mısın?",
            "Yarım yıllık sürdürülebilirlik araştırması nasıl yapılır?",
            "Robotik projesi için 6 aylık bir iş planı",
            "Orta vadeli biyomedikal sensör projesi",
            "5 aylık sürede tamamlanacak nesnelerin interneti uygulaması",
            
            # Uzun Vadeli (Kategori 3)
            "12 aylık kapsamlı bir yapay zeka projesi planı istiyorum",
            "TÜBİTAK 1001 için yıllık proje planı oluştur",
            "18 aylık sürdürülebilir enerji projesi nasıl yapılandırılır?",
            "Uzun vadeli iklim değişikliği izleme projesi",
            "24 aylık bir sağlık teknolojileri araştırması",
            "Bir yıllık akıllı tarım sistemleri geliştirme planı"
        ]
        
        for i, query in enumerate(complex_queries):
            category = i // 6  # Her kategori için 6 sorgu var
            all_texts.append(query)
            all_labels.append(category)
        
        logger.info(f"Manuel veri seti oluşturuldu: {len(all_texts)} örnek")
        return all_texts, all_labels
    
    def create_manual_training_data(self):
        """Tam manuel eğitim veri seti oluştur ve eğitim/test olarak böl"""
        all_texts, all_labels = self.create_manual_training_data_only()
        
        # Veri setini karıştır ve böl
        indices = np.arange(len(all_texts))
        np.random.shuffle(indices)
        
        shuffled_texts = [all_texts[i] for i in indices]
        shuffled_labels = [all_labels[i] for i in indices]
        
        # Eğitim/test olarak böl
        train_size = int(0.8 * len(shuffled_texts))
        
        train_texts = shuffled_texts[:train_size]
        train_labels = shuffled_labels[:train_size]
        test_texts = shuffled_texts[train_size:]
        test_labels = shuffled_labels[train_size:]
        
        # Veri kümelerini oluştur
        data = {
            'train': {
                'texts': train_texts,
                'labels': train_labels
            },
            'test': {
                'texts': test_texts,
                'labels': test_labels
            },
            'all': {
                'texts': shuffled_texts,
                'labels': shuffled_labels
            }
        }
        
        # JSON olarak kaydet
        json_path = os.path.join(self.training_dir, 'training_data.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Özet bilgileri
        summary = {
            'num_samples': {
                'train': len(train_texts),
                'test': len(test_texts),
                'total': len(shuffled_texts)
            },
            'class_distribution': {
                'train': {str(c): train_labels.count(c) for c in set(train_labels)},
                'test': {str(c): test_labels.count(c) for c in set(test_labels)},
                'all': {str(c): shuffled_labels.count(c) for c in set(shuffled_labels)}
            }
        }
        
        logger.info(f"Manuel eğitim verileri hazırlandı: {summary['num_samples']}")
        return data
    
    def train_lstm_model(self, training_data):
        """LSTM modeli eğit"""
        logger.info("LSTM model eğitimi başlıyor...")
        
        # Eğitim parametreleri
        max_words = 10000
        max_length = 100
        embedding_dim = 128
        lstm_units = 64
        dense_units = 64
        dropout_rate = 0.3
        batch_size = 16
        epochs = 15
        
        # Veri setleri
        train_texts = training_data['train']['texts']
        train_labels = training_data['train']['labels']
        test_texts = training_data['test']['texts']
        test_labels = training_data['test']['labels']
        
        # Veri setini kontrol et
        if len(train_texts) < 10:
            logger.error("Yetersiz eğitim verisi! En az 10 örnek gerekiyor.")
            return None, None
        
        # Tokenizer oluştur ve eğit
        tokenizer = Tokenizer(num_words=max_words, oov_token='<OOV>')
        tokenizer.fit_on_texts(train_texts + test_texts)
        
        # Tokenizer'ı kaydet
        tokenizer_path = os.path.join(self.model_dir, 'tokenizer.pickle')
        with open(tokenizer_path, 'wb') as handle:
            pickle.dump(tokenizer, handle, protocol=pickle.HIGHEST_PROTOCOL)
        
        # Dizilere dönüştür
        X_train = tokenizer.texts_to_sequences(train_texts)
        X_test = tokenizer.texts_to_sequences(test_texts)
        
        # Padding uygula
        X_train = pad_sequences(X_train, maxlen=max_length, padding='post')
        X_test = pad_sequences(X_test, maxlen=max_length, padding='post')
        
        # Sınıfları say
        num_classes = len(set(train_labels + test_labels))
        
        # Modeli oluştur
        model = Sequential([
            Embedding(max_words, embedding_dim, input_length=max_length),
            Bidirectional(LSTM(lstm_units, return_sequences=True)),
            Dropout(dropout_rate),
            GlobalMaxPooling1D(),
            Dense(dense_units, activation='relu'),
            Dropout(dropout_rate),
            Dense(num_classes, activation='softmax')
        ])
        
        # Modeli derle
        model.compile(
            loss='sparse_categorical_crossentropy',
            optimizer=Adam(learning_rate=0.001),
            metrics=['accuracy']
        )
        
        # Modeli özeti
        model.summary()
        
        # Başlangıç modelini kaydet
        model_path = os.path.join(self.training_dir, 'model', 'lstm_model_initial.h5')
        model.save(model_path)
        logger.info(f"Başlangıç modeli kaydedildi: {model_path}")
        
        # Callbacks
        checkpoint_path = os.path.join(self.training_dir, 'model', 'lstm_model_best.h5')
        callbacks = [
            ModelCheckpoint(
                checkpoint_path,
                monitor='val_accuracy',
                save_best_only=True,
                mode='max',
                verbose=1
            ),
            EarlyStopping(
                monitor='val_loss',
                patience=5,
                restore_best_weights=True,
                verbose=1
            ),
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.2,
                patience=3,
                min_lr=0.0001,
                verbose=1
            )
        ]
        
        # Modeli eğit
        logger.info(f"Eğitim başlıyor: {epochs} epoch, {batch_size} batch size")
        try:
            history = model.fit(
                X_train,
                np.array(train_labels),
                batch_size=batch_size,
                epochs=epochs,
                validation_data=(X_test, np.array(test_labels)),
                callbacks=callbacks,
                verbose=1
            )
            
            # En iyi modeli kaydet
            final_model_path = os.path.join(self.model_dir, 'lstm_model.h5')
            model.save(final_model_path)
            logger.info(f"Final modeli kaydedildi: {final_model_path}")
            
            # Seq2Seq model için output_tokenizer.pickle dosyası oluştur
            output_tokenizer_path = os.path.join(self.model_dir, 'output_tokenizer.pickle')
            with open(output_tokenizer_path, 'wb') as handle:
                pickle.dump(tokenizer, handle, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info(f"Output tokenizer kaydedildi: {output_tokenizer_path}")
            
            # Model performansını değerlendir
            test_loss, test_acc = model.evaluate(X_test, np.array(test_labels))
            logger.info(f"Test doğruluğu: {test_acc:.4f}")
            
            # Test örnekleri üzerinde tahminler yap
            test_examples = [
                "TÜBİTAK 2209-A için 12 aylık proje planı oluşturabilir misin?",
                "1001 projesi için 3 aylık plan istiyorum",
                "6 aylık bir araştırma projesi planı yazabilir misin?",
                "Akıllı şehir uygulamaları için bir proje planı"
            ]
            
            logger.info("\nÖrnek Tahminler:")
            for example in test_examples:
                self._predict_class(model, tokenizer, example, max_length)
            
            return model, history
            
        except Exception as e:
            logger.error(f"Model eğitimi sırasında hata: {str(e)}")
            logger.error(traceback.format_exc())
            return None, None
    
    def _predict_class(self, model, tokenizer, text, max_length=100):
        """Sınıflandırma tahmini yap"""
        # Metni işle
        sequence = tokenizer.texts_to_sequences([text])
        padded = pad_sequences(sequence, maxlen=max_length, padding='post')
        
        # Tahmin yap
        prediction = model.predict(padded, verbose=0)[0]
        predicted_class = np.argmax(prediction)
        confidence = prediction[predicted_class] * 100
        
        # Sınıf adını belirle
        class_names = ["Genel Bilgi", "Kısa Vadeli (1-3 ay)", "Orta Vadeli (4-6 ay)", "Uzun Vadeli (7+ ay)"]
        class_name = class_names[predicted_class] if predicted_class < len(class_names) else f"Sınıf {predicted_class}"
        
        logger.info(f"Sorgu: {text}")
        logger.info(f"Tahmin: {class_name} (Güven: %{confidence:.2f})")
        
        return predicted_class, confidence

def main():
    """Ana fonksiyon"""
    logger.info("LSTM Eğitim Süreci Başlatılıyor...")
    
    try:
        # Veritabanı bağlantı bilgisi - trusted_connection kullan
        connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=tubitak_db;Trusted_Connection=yes;'
        
        # Veri işleyici
        data_processor = LSTMDataProcessor(connection_string)
        
        # Önce veritabanından veri çekmeyi dene
        try:
            # Tüm planları çek
            plans_df = data_processor.fetch_all_plans()
            logger.info(f"Veritabanından {len(plans_df)} adet plan çekildi")
        except Exception as e:
            logger.error(f"Veritabanı sorgusu sırasında hata: {str(e)}")
            logger.error(traceback.format_exc())
            logger.info("Manuel veri ile devam ediliyor...")
            plans_df = pd.DataFrame()
        
        # Eğitim verilerini hazırla (veritabanı verisi + manuel veri)
        training_data = data_processor.prepare_training_data()
        
        # Modeli eğit
        model, history = data_processor.train_lstm_model(training_data)
        
        if model is None:
            logger.error("LSTM model eğitimi başarısız oldu.")
            return False
        
        logger.info("LSTM model eğitimi başarıyla tamamlandı.")
        return True
        
    except Exception as e:
        logger.error(f"Eğitim sürecinde beklenmeyen hata: {str(e)}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    main()