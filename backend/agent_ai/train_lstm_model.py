import os
import sys
import logging
import traceback
import tensorflow as tf
from datetime import datetime

# Proje kök dizinini Python yoluna ekleyin (gerekirse)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Kendi modüllerinizi import edin
from agent_ai.data_preparation import DataProcessor
from agent_ai.agent_ai_model import AgentAIModel

# Günlük ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_ai/training.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("TrainLSTM")

def train_model():
    """LSTM modelini eğit"""
    print("\n=============================================")
    print("   TÜBİTAK LSTM Seq2Seq Model Eğitimi")
    print("=============================================\n")
    
    # GPU kullanılabilirliğini kontrol et
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        print(f"GPU Bulundu: {len(gpus)} adet")
        # GPU bellek büyümesini sınırla
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    else:
        print("GPU bulunamadı, CPU kullanılacak. Bu işlem uzun sürebilir!")
    
    # Veri işleyici oluştur
    processor = DataProcessor()
    
    # Eğitim verisi hazırla
    print("Eğitim verisi hazırlanıyor...")
    input_texts, output_texts = processor.prepare_training_data()
    
    if not input_texts or len(input_texts) < 10:
        print("Yeterli eğitim verisi bulunamadı! En az 10 örnek gereklidir.")
        return False
    
    print(f"Toplam {len(input_texts)} eğitim örneği hazırlandı.")
    
    # Model dizinini oluştur
    os.makedirs('agent_ai/models', exist_ok=True)
    
    # Modeli oluştur
    model = AgentAIModel(
        model_path='agent_ai/models/lstm_seq2seq_model.h5',
        tokenizer_path='agent_ai/models/tokenizer.pickle',
        output_tokenizer_path='agent_ai/models/output_tokenizer.pickle',
        max_words=15000,
        max_length=100,
        max_output_length=500
    )
    
    # Eğitim parametreleri
    epochs = 20
    batch_size = 8
    validation_split = 0.2
    
    # Eğitim başlangıç zamanı
    start_time = datetime.now()
    print(f"Eğitim başlangıç zamanı: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Modeli eğit
    print("\nModel eğitimi başlıyor...")
    print(f"Parametreler: epochs={epochs}, batch_size={batch_size}, validation_split={validation_split}")
    
    try:
        history = model.train(
            input_texts=input_texts,
            output_texts=output_texts,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split
        )
        
        # Eğitim bitiş zamanı
        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\nEğitim tamamlandı!")
        print(f"Toplam süre: {duration}")
        
        if history:
            print("\nModel başarıyla eğitildi ve kaydedildi!")
            
            # Test örnekleri
            test_queries = [
                "TÜBİTAK 2209-A için 12 aylık bir proje planı oluşturabilir misin?",
                "1001 projesi için 24 aylık plan istiyorum",
                "6 aylık bir araştırma projesi planı yazabilir misin?"
            ]
            
            print("\nTest Sonuçları:")
            for query in test_queries:
                print(f"\nSorgu: {query}")
                try:
                    generated = model.generate_text(query)
                    print(f"Üretilen metin:\n{generated[:300]}...")
                except Exception as e:
                    print(f"Test sırasında hata: {str(e)}")
            
            return True
        else:
            print("Model eğitimi başarısız oldu!")
            return False
            
    except Exception as e:
        print(f"Eğitim sırasında hata: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    train_model()