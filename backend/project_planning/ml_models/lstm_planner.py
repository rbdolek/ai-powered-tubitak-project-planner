import os
import json
import pyodbc
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import Input, Embedding, LSTM, Dense, Dropout, concatenate
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from datetime import datetime, timedelta


class DataLoader:
    """Veriyi MS SQL'den çekip eğitim ve tahmin için hazırlar."""
    def __init__(self, conn_str, text_col, fund_col, target_col, max_vocab=20000, max_len=200):
        self.conn_str = conn_str
        self.text_col = text_col
        self.fund_col = fund_col
        self.target_col = target_col
        self.max_vocab = max_vocab
        self.max_len = max_len
        self.tokenizer = Tokenizer(num_words=self.max_vocab, oov_token='<OOV>')
        self.fund_mapping = {}

    def load_data(self, query):
        cnxn = pyodbc.connect(self.conn_str)
        df = np.array([])
        try:
            df = np.array([row for row in cnxn.execute(query)])
        finally:
            cnxn.close()
        return df

    def preprocess(self, rows):
        texts = [str(r[self.text_col]) for r in rows]
        funds = [r[self.fund_col] for r in rows]
        targets = np.array([float(r[self.target_col]) for r in rows])

        # Text tokenization
        self.tokenizer.fit_on_texts(texts)
        seqs = self.tokenizer.texts_to_sequences(texts)
        X_text = pad_sequences(seqs, maxlen=self.max_len, padding='post')

        # Fund encoding
        unique_funds = sorted(set(funds))
        self.fund_mapping = {f: i for i, f in enumerate(unique_funds)}
        X_fund = np.array([self.fund_mapping[f] for f in funds])

        return X_text, X_fund, targets


class PlannerModel:
    """LSTM tabanlı süre tahmin modeli ve plan üretim mantığı."""
    def __init__(self, vocab_size, fund_count, max_len, emb_dim=128, lstm_units=64):
        # Metin girdisi
        text_in = Input(shape=(max_len,), name='text_input')
        emb_text = Embedding(vocab_size, emb_dim, mask_zero=True)(text_in)
        lstm_out = LSTM(lstm_units)(emb_text)
        lstm_out = Dropout(0.3)(lstm_out)

        # Fon girdisi
        fund_in = Input(shape=(1,), name='fund_input')
        emb_fund = Embedding(fund_count, emb_dim)(fund_in)
        fund_vec = tf.squeeze(emb_fund, axis=1)

        # Birleştir ve regresyon
        merged = concatenate([lstm_out, fund_vec])
        dense = Dense(64, activation='relu')(merged)
        dense = Dropout(0.3)(dense)
        duration_out = Dense(1, activation='linear', name='duration')(dense)

        self.model = Model(inputs=[text_in, fund_in], outputs=duration_out)
        self.model.compile(optimizer='adam', loss='mae', metrics=['mae'])

    def train(self, X_text, X_fund, y, batch_size=32, epochs=20, model_path='lstm_planner.h5'):
        callbacks = [
            EarlyStopping(patience=3, restore_best_weights=True),
            ModelCheckpoint(model_path, save_best_only=True)
        ]
        return self.model.fit(
            {'text_input': X_text, 'fund_input': X_fund},
            y,
            batch_size=batch_size,
            epochs=epochs,
            validation_split=0.1,
            callbacks=callbacks
        )

    def save(self, path):
        self.model.save(path)

    def load(self, path):
        self.model = load_model(path)

    def predict_duration(self, text_seq, fund_id):
        return float(self.model.predict({'text_input': text_seq, 'fund_input': np.array([[fund_id]])})[0][0])

    @staticmethod
    def generate_schedule(duration_months, fund_type):
        # Örnek aylık ve haftalık plan üretimi (eski iş mantığı)
        start = datetime.now()
        end = start + timedelta(days=duration_months*30)
        weekly = []
        for w in range(1, duration_months*4 + 1):
            weekly.append({'week': w, 'phase': 'Genel Çalışma',
                           'tasks': f'{fund_type} aşama {w}'})
        monthly = []
        for m in range(1, duration_months + 1):
            monthly.append({'month': m, 'milestone': f'{m}. ay değerlendirme'})
        return {
            'start_date': start.strftime('%Y-%m-%d'),
            'end_date': end.strftime('%Y-%m-%d'),
            'weekly_plan': weekly,
            'monthly_plan': monthly
        }

    @staticmethod
    def progress_bar(start_date, end_date):
        now = datetime.now()
        total = (end_date - start_date).total_seconds()
        elapsed = (now - start_date).total_seconds()
        pct = max(0, min(100, (elapsed/total)*100))
        return int(pct)


if __name__ == '__main__':
    # Bağlantı dizesi ve sorgu örneği
    conn_str = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=DESKTOP-M37M8RJ;'           
    'DATABASE=tubitak_db;'        
    'Trusted_Connection=yes;'
)
    query = 'SELECT description, fund_type, duration_months FROM project_responses'

    # Veri hazırlık
    loader = DataLoader(conn_str, text_col=0, fund_col=1, target_col=2)
    rows = loader.load_data(query)
    X_text, X_fund, y = loader.preprocess(rows)

    # Model oluştur ve eğit
    planner = PlannerModel(
        vocab_size=loader.max_vocab,
        fund_count=len(loader.fund_mapping),
        max_len=loader.max_len
    )
    planner.train(X_text, X_fund, y)

    # Kayıtlıysa yükle ve tahmin et
    # planner.load('lstm_planner.h5')
    sample_idx = 0
    duration_pred = planner.predict_duration(
        np.expand_dims(X_text[sample_idx], axis=0),
        loader.fund_mapping[rows[sample_idx][1]]
    )
    schedule = planner.generate_schedule(int(round(duration_pred)), rows[sample_idx][1])
    print(json.dumps(schedule, indent=2))
