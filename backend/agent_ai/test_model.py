# agent_ai/test_model.py
import tensorflow as tf
import numpy as np
import pickle

# Model ve tokenizer'ı yükle
model = tf.keras.models.load_model('agent_ai/models/lstm_model.h5')
with open('agent_ai/models/tokenizer.pickle', 'rb') as handle:
    tokenizer = pickle.load(handle)

# Test metni
test_texts = [
    "2247-B kapsamında 6 aylık bir araştırma planı hazırlar mısın?",
    "1 yıllık proje için TÜBİTAK planı oluştur",
    "3 aylık kısa bir akademik araştırma için plan yapar mısın?"
]

# Metni işle
sequences = tokenizer.texts_to_sequences(test_texts)
padded = tf.keras.preprocessing.sequence.pad_sequences(sequences, maxlen=50, padding='post')

# Tahmin yap
predictions = model.predict(padded)

# Sınıf anlamları
class_meanings = {
    0: "Bilinmeyen/Belirsiz",
    1: "Kisa/Orta vadeli (1-6 ay)",
    2: "Uzun vadeli (6+ ay)"
}

for i, text in enumerate(test_texts):
    pred_class = np.argmax(predictions[i])
    confidence = predictions[i][pred_class]
    
    print(f"Test metni: {text}")
    print(f"Tahmin edilen sınıf: {pred_class}")
    print(f"Güven skoru: {confidence:.4f}")
    print(f"Anlamı: {class_meanings.get(pred_class, 'Bilinmiyor')}")
    print("--------------------")