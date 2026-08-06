# agent_ai/lstm_debugger.py
import os
import sys
import numpy as np
import pickle
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
import logging

# Günlük ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("LSTM_Debugger")

def load_resources():
    """Model kaynaklarını yükle ve test et"""
    try:
        # Dosya yolları
        model_path = 'models/lstm_seq2seq_model.h5'
        encoder_model_path = 'models/encoder_model.h5'
        decoder_model_path = 'models/decoder_model.h5'
        tokenizer_path = 'models/tokenizer.pickle'
        output_tokenizer_path = 'models/output_tokenizer.pickle'
        
        # Dosyaların varlığını kontrol et
        files_exist = True
        for path in [model_path, encoder_model_path, decoder_model_path, tokenizer_path, output_tokenizer_path]:
            if not os.path.exists(path):
                logger.error(f"HATA: {path} dosyası bulunamadı!")
                files_exist = False
        
        if not files_exist:
            return None, None, None, None
        
        # Ana model yükle
        model = load_model(model_path, compile=False)
        logger.info(f"Ana model yüklendi: {model_path}")
        
        # Encoder ve decoder modelleri yükle
        encoder_model = load_model(encoder_model_path, compile=False)
        decoder_model = load_model(decoder_model_path, compile=False)
        logger.info("Encoder ve decoder modelleri yüklendi")
        
        # Tokenizer'ları yükle
        with open(tokenizer_path, 'rb') as handle:
            tokenizer = pickle.load(handle)
        logger.info(f"Girdi tokenizer yüklendi: {tokenizer_path}")
        
        with open(output_tokenizer_path, 'rb') as handle:
            output_tokenizer = pickle.load(handle)
        logger.info(f"Çıktı tokenizer yüklendi: {output_tokenizer_path}")
        
        return model, encoder_model, decoder_model, tokenizer, output_tokenizer
        
    except Exception as e:
        logger.error(f"Model yüklenirken hata: {str(e)}")
        return None, None, None, None, None

def decode_sequence(input_text, encoder_model, decoder_model, tokenizer, output_tokenizer, max_length=100, max_output_words=150):
    """Bir girdi metnini kodlayıp çözümleyerek çıktı üret"""
    try:
        # Girdiyi tokenize et
        input_seq = tokenizer.texts_to_sequences([input_text])
        input_seq = pad_sequences(input_seq, maxlen=max_length, padding='post')
        
        # Tokenize edilmiş girdiyi incele
        logger.info(f"Tokenize edilmiş girdi: {input_seq}")
        logger.info(f"Tokenize edilmiş girdi şekli: {input_seq.shape}")
        
        # Encoder ile girdiyi kodla
        states_value = encoder_model.predict(input_seq, verbose=1)
        
        # Encoder çıktılarını incele
        logger.info(f"Encoder states değerleri türü: {type(states_value)}")
        if isinstance(states_value, list):
            logger.info(f"Encoder states uzunluğu: {len(states_value)}")
            for i, state in enumerate(states_value):
                logger.info(f"Encoder state {i} şekli: {state.shape}")
        
        # Hedef dizisi başlat
        target_seq = np.zeros((1, 1))
        
        # İlk karakteri başlangıç karakteri olarak ayarla
        start_word = 'tubitak'
        if start_word in output_tokenizer.word_index:
            target_seq[0, 0] = output_tokenizer.word_index[start_word]
            logger.info(f"Başlangıç kelimesi '{start_word}' bulundu, index: {output_tokenizer.word_index[start_word]}")
        else:
            target_seq[0, 0] = 1  # İlk token
            logger.info(f"Başlangıç kelimesi '{start_word}' bulunamadı, varsayılan index 1 kullanılıyor")
        
        # Çözümleme döngüsü
        decoded_sentence = ''
        decoded_words = []
        stop_condition = False
        word_count = 0
        
        logger.info("Decoder döngüsü başlıyor...")
        
        while not stop_condition:
            logger.info(f"Decoder adımı {word_count+1}...")
            
            # Decoder tahmini
            output_tokens, h, c = decoder_model.predict(
                [target_seq] + states_value, verbose=1
            )
            
            # Output inceleme
            logger.info(f"Decoder çıktı şekli: {output_tokens.shape}")
            logger.info(f"En yüksek olasılık: {np.max(output_tokens[0, 0, :])}")
            
            # Bir sonraki token'ı örnekle
            sampled_token_index = np.argmax(output_tokens[0, 0, :])
            logger.info(f"Seçilen token indeksi: {sampled_token_index}")
            
            # Index'ten kelimeyi bul
            sampled_word = ''
            for word, index in output_tokenizer.word_index.items():
                if index == sampled_token_index:
                    sampled_word = word
                    break
            
            logger.info(f"Seçilen kelime: '{sampled_word}'")
            
            # Kelimeyi cümleye ekle
            if sampled_word:
                decoded_words.append(sampled_word)
                if word_count > 0:  # İlk kelime değilse boşluk ekle
                    decoded_sentence += ' '
                decoded_sentence += sampled_word
                word_count += 1
            
            # Çıkış koşulu: max_output_words'e ulaşıldı veya <end> token'ı bulundu
            if word_count >= max_output_words or sampled_token_index == 0:
                stop_condition = True
                logger.info(f"Durma koşulu: {'Maksimum kelime sayısı' if word_count >= max_output_words else 'EOS token'}")
            
            # Hedef dizisini güncelle
            target_seq = np.zeros((1, 1))
            target_seq[0, 0] = sampled_token_index
            
            # Decoder durumlarını güncelle
            states_value = [h, c]
        
        logger.info(f"Toplam üretilen kelime sayısı: {word_count}")
        logger.info(f"Üretilen kelimeler: {decoded_words}")
        
        return decoded_sentence
        
    except Exception as e:
        logger.error(f"Decode sequence hatası: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"LSTM decoder hatası: {str(e)}"

def test_lstm_seq2seq():
    """LSTM Seq2Seq modelini test et"""
    logger.info("LSTM Seq2Seq model testi başlıyor...")
    
    # Kaynakları yükle
    model, encoder_model, decoder_model, tokenizer, output_tokenizer = load_resources()
    
    if model is None or encoder_model is None or decoder_model is None:
        logger.error("Model kaynakları yüklenemedi, test sonlandırılıyor.")
        return False
    
    # Tokenizer incelemesi
    logger.info(f"Girdi tokenizer kelime sayısı: {len(tokenizer.word_index)}")
    logger.info(f"Çıktı tokenizer kelime sayısı: {len(output_tokenizer.word_index)}")
    
    # Yaygın kelimeleri göster
    common_input_words = sorted(tokenizer.word_index.items(), key=lambda x: x[1])[:20]
    logger.info(f"Girdi tokenizer en yaygın 20 kelime: {common_input_words}")
    
    common_output_words = sorted(output_tokenizer.word_index.items(), key=lambda x: x[1])[:20]
    logger.info(f"Çıktı tokenizer en yaygın 20 kelime: {common_output_words}")
    
    # Test sorguları
    test_queries = [
        "TÜBİTAK 1001 için 12 aylık yapay zeka projesi",
        "TÜBİTAK 2209-A için 6 aylık robotik projesi",
        "3 aylık yazılım projesi planı oluştur"
    ]
    
    # Her sorgu için test et
    for query in test_queries:
        logger.info(f"\n{'='*50}\nSORGU: {query}\n{'='*50}")
        
        # Metin üret
        generated_text = decode_sequence(
            query, 
            encoder_model, 
            decoder_model, 
            tokenizer, 
            output_tokenizer
        )
        
        logger.info(f"\nÜRETİLEN METİN:\n{'-'*50}\n{generated_text}\n{'-'*50}")
    
    return True

if __name__ == "__main__":
    logger.info("LSTM Seq2Seq Debug Aracı Başlatılıyor...")
    test_lstm_seq2seq()