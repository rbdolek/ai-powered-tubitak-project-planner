# agent_ai/lstm_seq2seq_train.py
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
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import Input, LSTM, Dense, Embedding, Dropout, Bidirectional
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam

# UTF-8 karakter desteğini sağla
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Günlük ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_ai/lstm_seq2seq_training.log", encoding='utf-8'),
        logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8'))
    ]
)

logger = logging.getLogger("LSTM_Seq2Seq_Training")

class LSTMSeq2SeqTrainer:
    """LSTM Seq2Seq model eğitim sınıfı"""
    
    def __init__(self, connection_string=None):
        """Veri işleyiciyi başlat"""
        self.connection_string = connection_string or 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=tubitak_db;Trusted_Connection=yes;'
        self.training_dir = 'agent_ai/lstm_seq2seq_data'
        self.model_dir = 'models'  # Kodunuzun beklediği dizin
        
        # Dizinleri oluştur
        os.makedirs(self.training_dir, exist_ok=True)
        os.makedirs(os.path.join(self.training_dir, 'model'), exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Model parametreleri
        self.max_input_length = 100
        self.max_output_length = 500
        self.max_input_words = 15000
        self.max_output_words = 15000
        self.embedding_dim = 256
        self.lstm_units = 256
        self.batch_size = 16
        self.epochs = 10
        
        logger.info("LSTM Seq2Seq Trainer başlatıldı")
    
    def connect_to_db(self):
        """Veritabanına bağlan"""
        try:
            conn = pyodbc.connect(self.connection_string)
            logger.info("Veritabanı bağlantısı başarılı")
            return conn
        except Exception as e:
            logger.error(f"Veritabanı bağlantı hatası: {str(e)}")
            raise
    
    def fetch_plans_from_db(self):
        """Veritabanından plan verilerini çek"""
        logger.info("Veritabanından plan verilerini çekiyorum...")
        
        # NOT: Burada kendi veritabanı şemanıza uygun SQL sorgusunu kullanın
        # Örnek: Aşağıda verdiğiniz şemaya uygun SQL sorgusu
        query = """
        SELECT 
            p.id AS plan_id,
            p.plan_metni AS plan_text,
            p.ay_suresi AS duration_months,
            s.title AS session_title,
            fon.kod AS fon_code,
            fon.tur AS fon_type
        FROM 
            dbo.chat_aiplan p
        LEFT JOIN 
            dbo.chat_chatsession s ON s.plan_id = p.id
        LEFT JOIN 
            dbo.chat_fon fon ON p.fon_id = fon.id
        WHERE 
            p.plan_metni IS NOT NULL AND LEN(p.plan_metni) > 100
        ORDER BY 
            p.id DESC
        """
        
        try:
            # Bağlantı hatası ODBC SQL type -155 hatasını önle
            conn = self.connect_to_db()
            cursor = conn.cursor()
            cursor.execute(query)
            
            # Sonuçları manuel olarak çek
            columns = [column[0] for column in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            conn.close()
            
            # DataFrame oluştur
            df = pd.DataFrame(results)
            
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
    
    def generate_input_text(self, row):
        """Her bir satır için girdi metni oluştur"""
        title = row.get('session_title', '') if pd.notna(row.get('session_title', '')) else ''
        fon_code = row.get('fon_code', '') if pd.notna(row.get('fon_code', '')) else ''
        duration = row.get('duration_months', 0) if pd.notna(row.get('duration_months', 0)) else 0
        
        # Başlıktan sorgu oluştur
        if title:
            # Fon kodu ve süre referanslarını kaldır
            query = re.sub(r'^\s*TÜBİTAK\s+\d{4}(-[A-Z])?\s*', '', title)
            query = re.sub(r'\s*\d+\s*ayl[ıi]k\s*', '', query)
            query = query.strip()
        else:
            query = "Proje planı oluştur"
        
        # Girdi metni oluştur
        input_text = query
        
        # Fon kodunu ekle
        if fon_code and fon_code not in input_text:
            input_text = f"TÜBİTAK {fon_code} için " + input_text
        
        # Süreyi ekle
        if duration > 0 and not re.search(r'\d+\s*ayl[ıi]k', input_text):
            input_text = f"{duration} aylık " + input_text
        
        return input_text
    
    def prepare_training_data(self):
        """Seq2Seq eğitimi için verileri hazırla"""
        logger.info("Eğitim verileri hazırlanıyor...")
        
        # Veritabanından planları çek
        df = self.fetch_plans_from_db()
        
        if len(df) < 10:
            logger.warning("Veritabanında yeterli plan verisi bulunamadı!")
            # Alternatif: Manuel veri oluştur
            return self.create_manual_training_data()
        
        # Veri ön işleme
        input_texts = []
        output_texts = []
        
        for _, row in df.iterrows():
            plan_text = row.get('plan_text', '')
            
            # Plan metni kontrolü
            if not pd.isna(plan_text) and len(plan_text) > 100:
                # Girdi metni oluştur
                input_text = self.generate_input_text(row)
                
                # Çıktı metni olarak plan metnini kullan
                output_text = plan_text
                
                input_texts.append(input_text)
                output_texts.append(output_text)
        
        # Çok az veri varsa manuel veri ile destekle
        if len(input_texts) < 20:
            logger.warning(f"Yetersiz veri: Sadece {len(input_texts)} plan bulundu. Manuel veri eklenecek.")
            manual_inputs, manual_outputs = self.create_manual_seq2seq_data()
            input_texts.extend(manual_inputs)
            output_texts.extend(manual_outputs)
        
        # Eğitim ve test verilerini böl
        split_ratio = 0.2
        train_inputs, test_inputs, train_outputs, test_outputs = train_test_split(
            input_texts, output_texts, test_size=split_ratio, random_state=42
        )
        
        # Veri kümelerini kaydet
        data = {
            'train': {
                'inputs': train_inputs,
                'outputs': train_outputs
            },
            'test': {
                'inputs': test_inputs,
                'outputs': test_outputs
            },
            'all': {
                'inputs': input_texts,
                'outputs': output_texts
            }
        }
        
        # JSON olarak kaydet
        json_path = os.path.join(self.training_dir, 'seq2seq_data.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Özet bilgileri
        summary = {
            'num_samples': {
                'train': len(train_inputs),
                'test': len(test_inputs),
                'total': len(input_texts)
            }
        }
        
        logger.info(f"Eğitim verileri hazırlandı: {summary['num_samples']}")
        return data
    
    def create_manual_seq2seq_data(self):
        """Manuel seq2seq eğitim verileri oluştur"""
        logger.info("Manuel seq2seq eğitim verileri oluşturuluyor...")
        
        # TÜBİTAK Fon Kodları
        fon_codes = ["1001", "1002", "1005", "2209-A", "2209-B", "3501", "4004", "4005"]
        
        # Süre kategorileri
        durations = [3, 6, 12, 18, 24]
        
        # Araştırma alanları
        research_areas = [
            "yapay zeka", "makine öğrenmesi", "veri bilimi", "robotik", "otomasyon",
            "yenilenebilir enerji", "sürdürülebilirlik", "iklim değişikliği", "çevre yönetimi",
            "sağlık teknolojileri", "biyomedikal", "teşhis sistemleri", "uzaktan sağlık",
            "akıllı şehirler", "nesnelerin interneti", "sensör ağları", "akıllı ulaşım",
            "tarım teknolojileri", "akıllı tarım", "gıda güvenliği", "hassas tarım",
            "malzeme bilimi", "nanoteknoloji", "kompozit malzemeler", "yenilikçi malzemeler"
        ]
        
        # Soru formatları
        query_formats = [
            "{} için {} aylık proje planı oluştur",
            "{} projesi için {} aylık plan yazar mısın?",
            "{} araştırması için {} aylık TÜBİTAK projesi planı",
            "TÜBİTAK {} kodlu {} aylık {} projesi nasıl planlanır?",
            "{} konusunda {} aylık bir araştırma projesi"
        ]
        
        # Manuel veri için girdi ve çıktı metinleri
        input_texts = []
        output_texts = []
        
        # Farklı kombinasyonlarla veri oluştur
        for area in research_areas:
            for duration in durations:
                for fon in fon_codes[:3]:  # Her araştırma alanı için ilk 3 fon kodunu kullan
                    # Girdi metni oluştur
                    query_format = np.random.choice(query_formats)
                    
                    if "{}" in query_format:
                        if "TÜBİTAK" in query_format and "kodlu" in query_format:
                            input_text = query_format.format(fon, duration, area)
                        else:
                            input_text = query_format.format(area, duration)
                    
                    # Çıktı metni oluştur (plan şablonu)
                    output_text = self._generate_plan_template(area, duration, fon)
                    
                    input_texts.append(input_text)
                    output_texts.append(output_text)
        
        logger.info(f"Manuel seq2seq veri oluşturuldu: {len(input_texts)} örnek")
        return input_texts, output_texts
    
    def _generate_plan_template(self, area, duration, fon_code):
        """Plan şablonu oluştur"""
        # Başlık
        plan = f"TÜBİTAK {fon_code} Projesi - {duration} Aylık Plan\n\n"
        
        # Fazları belirle
        if duration <= 3:
            phases = ["Ay 1: Hazırlık", "Ay 2: Uygulama", "Ay 3: Değerlendirme"]
        elif duration <= 6:
            phases = ["Ay 1-2: Hazırlık", "Ay 3-4: Uygulama", "Ay 5-6: Değerlendirme ve Raporlama"]
        elif duration <= 12:
            phases = ["Ay 1-3: Hazırlık ve Literatür Taraması", 
                     "Ay 4-8: Uygulama ve Veri Toplama", 
                     "Ay 9-11: Değerlendirme ve Analiz", 
                     "Ay 12: Final Raporu ve Yayın Hazırlığı"]
        else:
            phases = ["Ay 1-4: Hazırlık ve Literatür Taraması", 
                     "Ay 5-10: Tasarım ve Geliştirme", 
                     "Ay 11-16: Uygulama ve Veri Toplama", 
                     "Ay 17-20: Analiz ve Değerlendirme", 
                     "Ay 21-24: Raporlama ve Yaygınlaştırma"]
        
        # Her faz için görevler ekle
        for phase in phases:
            plan += f"{phase}:\n"
            
            # Faz türüne göre görevler
            if "Hazırlık" in phase or "Literatür" in phase:
                tasks = [
                    f"{area} alanında literatür taraması",
                    "Proje ekibinin oluşturulması",
                    "İş paketlerinin detaylandırılması",
                    "Etik kurul başvurularının yapılması (gerekli ise)",
                    f"{area} için güncel yöntemlerin incelenmesi",
                    "Veri toplama protokollerinin belirlenmesi"
                ]
            elif "Tasarım" in phase or "Geliştirme" in phase:
                tasks = [
                    f"{area} için sistem tasarımı",
                    "Prototip geliştirme",
                    "Yazılım altyapısının oluşturulması",
                    "Donanım entegrasyonu",
                    "Algoritma geliştirme ve optimizasyon",
                    "Ara testlerin gerçekleştirilmesi"
                ]
            elif "Uygulama" in phase or "Veri" in phase:
                tasks = [
                    "Veri toplama sürecinin başlatılması",
                    "Deneysel çalışmaların yürütülmesi",
                    f"{area} alanında pilot uygulamaların gerçekleştirilmesi",
                    "Performans ölçümlerinin yapılması",
                    "Sistemin saha testleri",
                    "Geliştirme sürecinin dokümantasyonu"
                ]
            elif "Değerlendirme" in phase or "Analiz" in phase:
                tasks = [
                    "Toplanan verilerin analizi",
                    "Sonuçların değerlendirilmesi",
                    "Karşılaştırmalı analizlerin yapılması",
                    "İyileştirme önerilerinin geliştirilmesi",
                    "Bulguların literatürle karşılaştırılması",
                    f"{area} alanına katkıların belirlenmesi"
                ]
            else:  # Raporlama, Yaygınlaştırma
                tasks = [
                    "Final raporunun hazırlanması",
                    "Sonuçların yayına hazırlanması",
                    "Proje çıktılarının paydaşlarla paylaşılması",
                    "Fikri mülkiyet haklarının korunması",
                    "Proje sonuçlarının yaygınlaştırılması",
                    "Gelecek çalışmaların planlanması"
                ]
            
            # Görevleri metne ekle
            for task in tasks:
                plan += f"- {task}\n"
            
            plan += "\n"
        
        return plan
    
    def create_manual_training_data(self):
        """Tam manuel eğitim veri seti oluştur"""
        input_texts, output_texts = self.create_manual_seq2seq_data()
        
        # Veriyi eğitim/test olarak böl
        split_ratio = 0.2
        train_inputs, test_inputs, train_outputs, test_outputs = train_test_split(
            input_texts, output_texts, test_size=split_ratio, random_state=42
        )
        
        # Veri kümelerini oluştur
        data = {
            'train': {
                'inputs': train_inputs,
                'outputs': train_outputs
            },
            'test': {
                'inputs': test_inputs,
                'outputs': test_outputs
            },
            'all': {
                'inputs': input_texts,
                'outputs': output_texts
            }
        }
        
        # JSON olarak kaydet
        json_path = os.path.join(self.training_dir, 'seq2seq_data.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Özet bilgileri
        summary = {
            'num_samples': {
                'train': len(train_inputs),
                'test': len(test_inputs),
                'total': len(input_texts)
            }
        }
        
        logger.info(f"Manuel eğitim verileri hazırlandı: {summary['num_samples']}")
        return data
    
    def train_seq2seq_model(self, training_data):
        """LSTM Seq2Seq modelini eğit"""
        logger.info("LSTM Seq2Seq model eğitimi başlıyor...")
        
        # Eğitim verilerini al
        train_inputs = training_data['train']['inputs']
        train_outputs = training_data['train']['outputs']
        test_inputs = training_data['test']['inputs']
        test_outputs = training_data['test']['outputs']
        
        # Girdi tokenizer'ı oluştur ve eğit
        input_tokenizer = Tokenizer(num_words=self.max_input_words, oov_token='<OOV>')
        input_tokenizer.fit_on_texts(train_inputs + test_inputs)
        
        # Çıktı tokenizer'ı oluştur ve eğit
        output_tokenizer = Tokenizer(num_words=self.max_output_words, oov_token='<OOV>')
        output_tokenizer.fit_on_texts(train_outputs + test_outputs)
        
        # Tokenizer'ları kaydet
        input_tokenizer_path = os.path.join(self.model_dir, 'tokenizer.pickle')
        with open(input_tokenizer_path, 'wb') as handle:
            pickle.dump(input_tokenizer, handle, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info(f"Girdi tokenizer kaydedildi: {input_tokenizer_path}")
        
        output_tokenizer_path = os.path.join(self.model_dir, 'output_tokenizer.pickle')
        with open(output_tokenizer_path, 'wb') as handle:
            pickle.dump(output_tokenizer, handle, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info(f"Çıktı tokenizer kaydedildi: {output_tokenizer_path}")
        
        # Girdileri sayısal dizilere dönüştür
        input_sequences = input_tokenizer.texts_to_sequences(train_inputs)
        input_padded = pad_sequences(input_sequences, maxlen=self.max_input_length, padding='post')
        
        # Çıktıları sayısal dizilere dönüştür
        target_sequences = output_tokenizer.texts_to_sequences(train_outputs)
        
        # Çıktılar için <start> ve <end> tokenlerini oluştur
        # NOT: Bu basitleştirilmiş bir yaklaşım, gerçek uygulamada özel start/end tokenleri eklenmelidir
        decoder_input_data = pad_sequences(target_sequences, maxlen=self.max_output_length, padding='post')
        
        # Decoder target data: Decoder input'un bir timestep sonrası
        decoder_target_data = np.zeros_like(decoder_input_data)
        decoder_target_data[:, :-1] = decoder_input_data[:, 1:]
        
        # Validation verilerini hazırla
        val_input_sequences = input_tokenizer.texts_to_sequences(test_inputs)
        val_input_padded = pad_sequences(val_input_sequences, maxlen=self.max_input_length, padding='post')
        
        val_target_sequences = output_tokenizer.texts_to_sequences(test_outputs)
        val_decoder_input_data = pad_sequences(val_target_sequences, maxlen=self.max_output_length, padding='post')
        
        val_decoder_target_data = np.zeros_like(val_decoder_input_data)
        val_decoder_target_data[:, :-1] = val_decoder_input_data[:, 1:]
        
        # Encoder (LSTM)
        encoder_inputs = Input(shape=(self.max_input_length,))
        encoder_embedding = Embedding(self.max_input_words, self.embedding_dim, 
                                     input_length=self.max_input_length)(encoder_inputs)
        encoder_lstm = Bidirectional(LSTM(self.lstm_units, return_state=True))
        encoder_outputs, forward_h, forward_c, backward_h, backward_c = encoder_lstm(encoder_embedding)
        
        # Bidirectional LSTM'den gelen state'leri birleştir
        state_h = tf.keras.layers.Concatenate()([forward_h, backward_h])
        state_c = tf.keras.layers.Concatenate()([forward_c, backward_c])
        
        # Encoder state'lerini decoder'a başlangıç durumu olarak ver
        encoder_states = [state_h, state_c]
        
        # Decoder (LSTM)
        decoder_inputs = Input(shape=(self.max_output_length,))
        decoder_embedding = Embedding(self.max_output_words, self.embedding_dim, 
                                     input_length=self.max_output_length)(decoder_inputs)
        decoder_lstm = LSTM(self.lstm_units * 2, return_sequences=True, return_state=True)
        decoder_outputs, _, _ = decoder_lstm(decoder_embedding, initial_state=encoder_states)
        decoder_dense = Dense(self.max_output_words, activation='softmax')
        decoder_outputs = decoder_dense(decoder_outputs)
        
        # Tam modeli tanımla
        model = Model([encoder_inputs, decoder_inputs], decoder_outputs)
        
        # Modeli derle
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        # Model özeti
        model.summary()
        
        # Callbacks
        checkpoint_path = os.path.join(self.training_dir, 'model', 'seq2seq_best.h5')
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
        logger.info(f"Eğitim başlıyor: {self.epochs} epoch, {self.batch_size} batch size")
        history = model.fit(
            [input_padded, decoder_input_data],
            np.expand_dims(decoder_target_data, -1),
            batch_size=self.batch_size,
            epochs=self.epochs,
            validation_data=(
                [val_input_padded, val_decoder_input_data],
                np.expand_dims(val_decoder_target_data, -1)
            ),
            callbacks=callbacks,
            verbose=1
        )
        
        # Final modelini kaydet
        final_model_path = os.path.join(self.model_dir, 'lstm_seq2seq_model.h5')
        model.save(final_model_path)
        logger.info(f"Final model kaydedildi: {final_model_path}")
        
        # Çıkarım (inference) modeli
        # Encoder modeli
        encoder_model = Model(encoder_inputs, encoder_states)
        
        # Decoder için placeholder'lar
        decoder_state_input_h = Input(shape=(self.lstm_units * 2,))
        decoder_state_input_c = Input(shape=(self.lstm_units * 2,))
        decoder_states_inputs = [decoder_state_input_h, decoder_state_input_c]
        
        # Decoder çıktısı
        decoder_outputs, state_h, state_c = decoder_lstm(
            decoder_embedding, initial_state=decoder_states_inputs
        )
        decoder_states = [state_h, state_c]
        decoder_outputs = decoder_dense(decoder_outputs)
        
        # Çıkarım decoder modeli
        decoder_model = Model(
            [decoder_inputs] + decoder_states_inputs,
            [decoder_outputs] + decoder_states
        )
        
        # Çıkarım modellerini kaydet
        encoder_model.save(os.path.join(self.model_dir, 'encoder_model.h5'))
        decoder_model.save(os.path.join(self.model_dir, 'decoder_model.h5'))
        
        # Test örnekleri
        self.test_seq2seq_model(encoder_model, decoder_model, input_tokenizer, output_tokenizer)
        
        # Doğruluk hesapla
        val_loss, val_acc = model.evaluate(
            [val_input_padded, val_decoder_input_data],
            np.expand_dims(val_decoder_target_data, -1)
        )
        
        logger.info(f"Validation doğruluğu: {val_acc:.4f} ({val_acc*100:.2f}%)")
        
        return model, history, val_acc
    
    def test_seq2seq_model(self, encoder_model, decoder_model, input_tokenizer, output_tokenizer):
        """Test verileri ile seq2seq modeli dene"""
        logger.info("Test örnekleri ile model değerlendiriliyor...")
        
        test_queries = [
            "TÜBİTAK 2209-A için 12 aylık yapay zeka projesi planı oluştur",
            "6 aylık akıllı tarım projesi için plan yazar mısın?",
            "3 aylık TÜBİTAK 1001 yenilenebilir enerji projesi planı"
        ]
        
        for query in test_queries:
            generated = self.decode_sequence(query, encoder_model, decoder_model, 
                                            input_tokenizer, output_tokenizer)
            
            logger.info(f"\nSorgu: {query}")
            logger.info(f"Üretilen plan:\n{generated[:300]}...")
    
    def decode_sequence(self, input_text, encoder_model, decoder_model, 
                       input_tokenizer, output_tokenizer):
        """Bir girdi metnini kodlayıp çözümleyerek çıktı üret"""
        # Girdiyi tokenize et
        input_seq = input_tokenizer.texts_to_sequences([input_text])
        input_seq = pad_sequences(input_seq, maxlen=self.max_input_length, padding='post')
        
        # Encoder ile girdiyi kodla
        states_value = encoder_model.predict(input_seq, verbose=0)
        
        # Hedef dizisi başlat
        target_seq = np.zeros((1, 1))
        
        # İlk karakteri başlangıç karakteri olarak ayarla
        target_seq[0, 0] = output_tokenizer.word_index.get('tubitak', 1)  # 'tubitak' kelimesiyle başlayalım
        
        # Çözümleme döngüsü
        decoded_sentence = ''
        stop_condition = False
        word_count = 0
        
        while not stop_condition:
            output_tokens, h, c = decoder_model.predict(
                [target_seq] + states_value, verbose=0
            )
            
            # Bir sonraki token'ı örnekle
            sampled_token_index = np.argmax(output_tokens[0, 0, :])
            
            # Index'ten kelimeyi bul
            sampled_word = ''
            for word, index in output_tokenizer.word_index.items():
                if index == sampled_token_index:
                    sampled_word = word
                    break
            
            # Kelimeyi cümleye ekle
            if sampled_word:
                decoded_sentence += sampled_word + ' '
                word_count += 1
            
            # Çıkış koşulu: max_output_length'e ulaşıldı veya <end> token'ı bulundu
            if word_count > self.max_output_length // 5 or sampled_token_index == 0:
                stop_condition = True
            
            # Hedef dizisini güncelle
            target_seq = np.zeros((1, 1))
            target_seq[0, 0] = sampled_token_index
            
            # Decoder durumlarını güncelle
            states_value = [h, c]
        
        return decoded_sentence

def main():
    """Ana fonksiyon"""
    logger.info("LSTM Seq2Seq Eğitim Süreci Başlatılıyor...")
    
    try:
        # Veritabanı bağlantı bilgisi - varsayılan güvenilir bağlantı
        connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=tubitak_db;Trusted_Connection=yes;'
        
        # Eğitici örneğini oluştur
        trainer = LSTMSeq2SeqTrainer(connection_string)
        
        # Eğitim verilerini hazırla
        training_data = trainer.prepare_training_data()
        
        # Modeli eğit
        model, history, val_accuracy = trainer.train_seq2seq_model(training_data)
        
        logger.info(f"Eğitim tamamlandı! Model doğruluğu: {val_accuracy*100:.2f}%")
        logger.info(f"Model ve tokenizer'lar şurada: {trainer.model_dir}/")
        
        return True
        
    except Exception as e:
        logger.error(f"Eğitim sürecinde beklenmeyen hata: {str(e)}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    main()