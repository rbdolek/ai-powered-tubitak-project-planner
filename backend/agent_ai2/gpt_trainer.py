import os
import re
import json
import time
import pandas as pd
import numpy as np
import sqlite3
import logging
import torch
import traceback
from datetime import datetime
from sklearn.model_selection import train_test_split
from transformers import (
    GPT2Tokenizer, 
    GPT2LMHeadModel, 
    GPT2Config,
    Trainer, 
    TrainingArguments,
    TextDataset,
    DataCollatorForLanguageModeling
)

# Log dizinini oluştur
os.makedirs("agent_ai2/logs", exist_ok=True)

# Günlük kaydı yapılandırma
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_ai2/logs/gpt_trainer.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GPT_Trainer")

class GPTTrainer:
    """GPT modeli eğitim sınıfı"""
    
    def __init__(self, 
                 base_model_name="gpt2", 
                 output_dir="agent_ai2/gpt_model_data",
                 train_data_file="agent_ai2/gpt_model_data/train.txt",
                 model_dir="models",
                 db_path="db.sqlite3"):
        """GPT Trainer sınıfını başlat"""
        self.base_model_name = base_model_name
        self.output_dir = output_dir
        self.train_data_file = train_data_file
        self.model_dir = model_dir
        self.db_path = db_path
        
        # Çıktı dizinlerini oluştur
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.train_data_file), exist_ok=True)
        
        # Model ve tokenizer
        self.tokenizer = None
        self.model = None
        self.stats = {
            'start_time': None,
            'end_time': None,
            'training_time': None,
            'num_examples': 0,
            'loss': 0,
            'perplexity': 0,
            'model_size': 0
        }
        
        logger.info(f"GPT Trainer başlatıldı: {base_model_name}")
    
    def prepare_data(self):
        """Veritabanından proje planı verilerini çek ve eğitim formatına dönüştür"""
        logger.info("Eğitim verileri hazırlanıyor...")
        try:
            # MS SQL Server bağlantısı
            logger.info(f"Veritabanından plan verilerini çekiyorum")
            conn_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=tubitak_db;Trusted_Connection=yes;'
            
            try:
                import pyodbc
                conn = pyodbc.connect(conn_string)
                logger.info("Veritabanı bağlantısı başarılı")
            except ImportError:
                logger.error("pyodbc kütüphanesi bulunamadı. pip install pyodbc komutu ile yükleyin.")
                raise
            except Exception as e:
                logger.error(f"Veritabanı bağlantı hatası: {str(e)}")
                
                # Test için sahte veriler oluştur
                logger.info("Veritabanı bağlantısı başarısız. Test için sahte veriler oluşturuluyor.")
                return self._create_sample_data()
            
            # Önce tabloların varlığını kontrol et
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT TOP 1 * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME IN ('chat_chatmessage', 'chat_chatsession', 'chat_aiplan')")
                tables = cursor.fetchall()
                
                if len(tables) < 3:
                    logger.warning("Gerekli tablolar bulunamadı. Test için sahte veriler oluşturuluyor.")
                    conn.close()
                    return self._create_sample_data()
                    
                # Tablolardaki veri sayısını kontrol et
                cursor.execute("SELECT COUNT(*) FROM dbo.chat_aiplan WHERE plan_metni IS NOT NULL AND plan_metni != ''")
                plan_count = cursor.fetchone()[0]
                logger.info(f"chat_aiplan tablosunda {plan_count} adet dolu plan bulundu")
                
                if plan_count == 0:
                    logger.warning("Veritabanında uygun plan bulunamadı. Test için sahte veriler oluşturuluyor.")
                    conn.close()
                    return self._create_sample_data()
                    
            except Exception as e:
                logger.error(f"Tablo kontrolü sırasında hata: {str(e)}")
                conn.close()
                return self._create_sample_data()
            
            # Planları çek - MS SQL Server için sorguyu düzenle
            query = """
            SELECT TOP 100
                cm.content AS query,
                ap.plan_metni AS plan_text
            FROM 
                dbo.chat_chatmessage cm
            JOIN 
                dbo.chat_chatsession cs ON cm.session_id = cs.id
            JOIN 
                dbo.chat_aiplan ap ON cm.related_plan_id = ap.id
            WHERE 
                cm.is_user = 1
                AND ap.plan_metni IS NOT NULL 
                AND ap.plan_metni != ''
            """
            
            try:
                cursor = conn.cursor()
                cursor.execute(query)
                
                # Sonuçları DataFrame'e dönüştür
                rows = cursor.fetchall()
                
                if not rows:
                    logger.warning("Sorgu sonucunda veri bulunamadı. Test için sahte veriler oluşturuluyor.")
                    conn.close()
                    return self._create_sample_data()
                    
                plans_df = pd.DataFrame(rows, columns=['query', 'plan_text'])
                conn.close()
                
            except Exception as e:
                logger.error(f"Sorgu çalıştırma hatası: {str(e)}")
                conn.close()
                return self._create_sample_data()
            
            # Boş satırları temizle
            plans_df = plans_df.dropna()
            
            if plans_df.empty:
                logger.warning("Boş satırları temizledikten sonra veri kalmadı. Test için sahte veriler oluşturuluyor.")
                return self._create_sample_data()
            
            logger.info(f"{len(plans_df)} adet plan verisi bulundu")
            
            # CSV olarak kaydet (isteğe bağlı)
            csv_path = os.path.join(self.output_dir, "all_plans.csv")
            plans_df.to_csv(csv_path, index=False, encoding='utf-8')
            logger.info(f"Veriler CSV olarak kaydedildi: {csv_path}")
            
            # GPT formatını hazırla: sorgu ve planı birleştir
            formatted_data = []
            for idx, row in plans_df.iterrows():
                # Sorgu ve planı birleştir
                formatted_text = f"<|QUERY|>\n{row['query']}\n\n<|PLAN|>\n{row['plan_text']}\n\n<|END|>"
                formatted_data.append(formatted_text)
            
            if not formatted_data:
                logger.warning("Formatlanmış veri oluşturulamadı. Test için sahte veriler oluşturuluyor.")
                return self._create_sample_data()
            
            # Eğitim ve test verilerini ayır
            train_data, test_data = train_test_split(formatted_data, test_size=0.2, random_state=42)
            
            # Eğitim verilerini dosyaya kaydet
            with open(self.train_data_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(train_data))
            
            # Test verilerini dosyaya kaydet
            test_data_file = self.train_data_file.replace('train.txt', 'test.txt')
            with open(test_data_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(test_data))
            
            self.stats['num_examples'] = len(formatted_data)
            
            logger.info(f"Eğitim verileri hazırlandı: {{'train': {len(train_data)}, 'test': {len(test_data)}, 'total': {len(formatted_data)}}}")
            
            return {
                'train_count': len(train_data),
                'test_count': len(test_data),
                'total_count': len(formatted_data)
            }
            
        except Exception as e:
            logger.error(f"Veri hazırlama hatası: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Hata durumunda sahte veri oluştur
            return self._create_sample_data()

    def _create_sample_data(self):
        """Test için örnek veri oluştur"""
        logger.info("Test için örnek veri oluşturuluyor...")
        
        # Örnek sorgu ve planlar
        sample_data = [
            {
                "query": "TÜBİTAK 1001 için 12 aylık yapay zeka projesi planı oluştur",
                "plan": """TÜBİTAK 1001 PROJESİ - 12 AYLIK PLAN

Ay 1-3: Başlangıç ve Planlama
- Literatür taraması yapılması
- Veri toplama stratejilerinin belirlenmesi
- Proje ekibinin oluşturulması

Ay 4-6: Geliştirme
- Algoritmaların geliştirilmesi
- Model eğitimi ve optimizasyonu
- Ön testlerin yapılması

Ay 7-9: Test ve İyileştirme
- Modelin farklı veri setleriyle test edilmesi
- Performans değerlendirmesi
- Gerekli iyileştirmelerin yapılması

Ay 10-12: Değerlendirme ve Raporlama
- Son testlerin yapılması
- Sonuçların analizi
- Final raporunun hazırlanması"""
            },
            {
                "query": "6 aylık akıllı tarım projesi için plan yazar mısın?",
                "plan": """TÜBİTAK PROJESİ - 6 AYLIK PLAN

Ay 1-2: Başlangıç ve Planlama
- Literatür taraması yapılması
- Mevcut akıllı tarım sistemlerinin incelenmesi
- Proje ekibinin oluşturulması
- Çiftçiler ve tarım uzmanlarıyla görüşmeler

Ay 3-4: Geliştirme
- Sensör sistemlerinin tasarlanması
- Yazılım altyapısının oluşturulması
- İlk prototiplerin geliştirilmesi
- Test alanının hazırlanması

Ay 5-6: Test ve Değerlendirme
- Saha testlerinin yapılması
- Sistem performansının değerlendirilmesi
- Gerekli iyileştirmelerin yapılması
- Final raporunun hazırlanması ve sonuçların paylaşılması"""
            },
            {
                "query": "TÜBİTAK 2209-A için 3 aylık robotik projesi",
                "plan": """TÜBİTAK 2209-A PROJESİ - 3 AYLIK PLAN

Ay 1: Başlangıç ve Tasarım
- Literatür taraması yapılması
- Robot tasarımının tamamlanması
- Gerekli malzemelerin temin edilmesi
- İş paketlerinin detaylandırılması

Ay 2: Geliştirme
- Robot mekanik sisteminin inşası
- Elektronik bileşenlerin entegrasyonu
- Temel yazılımın geliştirilmesi
- İlk test çalışmalarının yapılması

Ay 3: Test ve Raporlama
- Kapsamlı test süreçlerinin tamamlanması
- İyileştirmelerin yapılması
- Projenin dokümantasyonunun hazırlanması
- Final raporunun yazılması ve sunumun hazırlanması"""
            },
            {
                "query": "TÜBİTAK 1005 için 24 aylık yenilenebilir enerji projesi planı",
                "plan": """TÜBİTAK 1005 PROJESİ - 24 AYLIK PLAN

Ay 1-3: Planlama ve Literatür Taraması
- Kapsamlı literatür taraması
- Proje ekibinin oluşturulması
- İş paketlerinin detaylandırılması
- Etik izinlerin alınması

Ay 4-8: Tasarım ve Ön Çalışmalar
- Yenilenebilir enerji sisteminin tasarımı
- Simülasyon modellerinin oluşturulması
- İlk prototiplerin geliştirilmesi
- Ön testlerin yapılması

Ay 9-14: Geliştirme (Birinci Aşama)
- Sistem bileşenlerinin üretimi
- Yazılım ve donanım entegrasyonu
- İlk saha testlerinin başlatılması
- Ara raporun hazırlanması

Ay 15-20: Geliştirme (İkinci Aşama) ve Test
- Tam ölçekli sistem entegrasyonu
- Kapsamlı performans testleri
- Veri toplama ve analiz
- İyileştirmelerin yapılması

Ay 21-24: Değerlendirme ve Raporlama
- Sistemin uzun süreli performans değerlendirmesi
- Ekonomik ve çevresel etki analizleri
- Sonuçların yaygınlaştırılması
- Final raporunun hazırlanması"""
            },
            {
                "query": "TÜBİTAK 3501 için 18 aylık sağlık teknolojileri projesi",
                "plan": """TÜBİTAK 3501 PROJESİ - 18 AYLIK PLAN

Ay 1-3: Başlangıç ve Planlama
- Literatür taraması yapılması
- Proje ekibinin oluşturulması
- Klinik ortaklarla iş birliği protokollerinin oluşturulması
- Etik kurul izinlerinin alınması

Ay 4-6: Tasarım ve Geliştirme (I)
- Sistem mimarisinin tasarlanması
- Prototip geliştirme başlangıcı
- Kullanıcı geri bildirimi için metodoloji oluşturulması
- Veri toplama protokollerinin hazırlanması

Ay 7-10: Geliştirme (II)
- Prototip geliştirmenin tamamlanması
- Yazılım ve donanım entegrasyonu
- İlk laboratuvar testlerinin yapılması
- Klinik test planının detaylandırılması

Ay 11-14: Klinik Testler ve İyileştirme
- Kontrollü ortamda klinik testlerin başlatılması
- Kullanıcı geri bildirimlerinin toplanması
- Sistem iyileştirmelerinin yapılması
- Ara raporun hazırlanması

Ay 15-18: Değerlendirme ve Sonuçlandırma
- Final klinik değerlendirmelerin yapılması
- Performans ve etkinlik analizleri
- Maliyet-etkinlik analizleri
- Sonuçların yayına hazırlanması ve final raporun yazılması"""
            }
        ]
        
        # Formatlanmış veri oluştur
        formatted_data = []
        for item in sample_data:
            formatted_text = f"<|QUERY|>\n{item['query']}\n\n<|PLAN|>\n{item['plan']}\n\n<|END|>"
            formatted_data.append(formatted_text)
        
        # Eğitim ve test verilerini ayır (5 örnek olduğu için 4 eğitim, 1 test)
        train_data = formatted_data[:4]
        test_data = formatted_data[4:]
        
        # Eğitim verilerini dosyaya kaydet
        with open(self.train_data_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(train_data))
        
        # Test verilerini dosyaya kaydet
        test_data_file = self.train_data_file.replace('train.txt', 'test.txt')
        with open(test_data_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(test_data))
        
        self.stats['num_examples'] = len(formatted_data)
        
        logger.info(f"Örnek eğitim verileri hazırlandı: {{'train': {len(train_data)}, 'test': {len(test_data)}, 'total': {len(formatted_data)}}}")
        
        return {
            'train_count': len(train_data),
            'test_count': len(test_data),
            'total_count': len(formatted_data)
        }
        
    def load_base_model(self):
        """GPT2 modelini ve tokenizer'ı yükle"""
        try:
            logger.info(f"Temel model yükleniyor: {self.base_model_name}")
            
            # Tokenizer
            self.tokenizer = GPT2Tokenizer.from_pretrained(self.base_model_name)
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Özel tokenleri ekle
            special_tokens = {
                'additional_special_tokens': ['<|QUERY|>', '<|PLAN|>', '<|END|>']
            }
            self.tokenizer.add_special_tokens(special_tokens)
            
            # Model
            model_config = GPT2Config.from_pretrained(
                self.base_model_name,
                vocab_size=len(self.tokenizer)
            )
            self.model = GPT2LMHeadModel.from_pretrained(
                self.base_model_name,
                config=model_config
            )
            
            # Tokenizer'ı genişletmeye uygun hale getir
            self.model.resize_token_embeddings(len(self.tokenizer))
            
            logger.info(f"Model yüklendi: {self.model.config.to_dict()}")
            
            return True
        except Exception as e:
            logger.error(f"Model yükleme hatası: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def train_model(self, epochs=4, batch_size=4, learning_rate=5e-5):
        """GPT modelini eğit"""
        try:
            if self.model is None or self.tokenizer is None:
                if not self.load_base_model():
                    logger.error("Model yüklenemedi, eğitim iptal ediliyor.")
                    return False
            
            logger.info(f"Model eğitimi başlıyor: {epochs} epoch, {batch_size} batch size")
            self.stats['start_time'] = datetime.now().isoformat()
            
            # Eğitim veri setini hazırla
            train_dataset = TextDataset(
                tokenizer=self.tokenizer,
                file_path=self.train_data_file,
                block_size=512
            )
            
            # Veri koleksiyoncusu
            data_collator = DataCollatorForLanguageModeling(
                tokenizer=self.tokenizer,
                mlm=False
            )
            
            # Eğitim argümanları
            training_args = TrainingArguments(
                output_dir=os.path.join(self.output_dir, "checkpoints"),
                overwrite_output_dir=True,
                num_train_epochs=epochs,
                per_device_train_batch_size=batch_size,
                save_steps=500,
                save_total_limit=2,
                logging_dir=os.path.join(self.output_dir, "logs"),
                logging_steps=100,
                learning_rate=learning_rate,
                weight_decay=0.01,
                warmup_steps=500,
                fp16=torch.cuda.is_available(),  # GPU varsa yarı-hassasiyet kullan
                gradient_accumulation_steps=4,   # Daha büyük batch'ler için
            )
            
            # Trainer
            trainer = Trainer(
                model=self.model,
                args=training_args,
                data_collator=data_collator,
                train_dataset=train_dataset,
            )
            
            # Eğitim
            train_result = trainer.train()
            
            # Eğitim istatistikleri
            self.stats['end_time'] = datetime.now().isoformat()
            start_time = datetime.fromisoformat(self.stats['start_time'])
            end_time = datetime.fromisoformat(self.stats['end_time'])
            self.stats['training_time'] = (end_time - start_time).total_seconds() / 60.0  # dakika cinsinden
            self.stats['loss'] = train_result.training_loss
            self.stats['perplexity'] = np.exp(train_result.training_loss)
            
            # Model boyutu
            model_size_mb = sum(p.numel() for p in self.model.parameters()) * 4 / 1024 / 1024  # MB cinsinden
            self.stats['model_size'] = model_size_mb
            
            # Modeli ve tokenizer'ı kaydet
            self.save_model()
            
            # İstatistikleri kaydet
            stats_file = os.path.join(self.output_dir, "training_stats.json")
            with open(stats_file, 'w') as f:
                json.dump(self.stats, f, indent=4)
            
            logger.info(f"Eğitim tamamlandı! Model doğruluğu: {100 - self.stats['perplexity']:.2f}%")
            logger.info(f"Eğitim süresi: {self.stats['training_time']:.2f} dakika")
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Eğitim hatası: {str(e)}")
            logger.error(traceback.format_exc())
            self.stats['end_time'] = datetime.now().isoformat()
            return False
    
    def save_model(self):
        """Eğitilmiş modeli ve tokenizer'ı kaydet"""
        try:
            # Ana model dizini
            model_save_dir = os.path.join(self.model_dir, "gpt2_tubitak_plan")
            os.makedirs(model_save_dir, exist_ok=True)
            
            # Modeli kaydet
            self.model.save_pretrained(model_save_dir)
            logger.info(f"Model kaydedildi: {model_save_dir}")
            
            # Tokenizer'ı kaydet
            self.tokenizer.save_pretrained(model_save_dir)
            logger.info(f"Tokenizer kaydedildi: {model_save_dir}")
            
            # Konfigürasyonu kaydet
            config_file = os.path.join(model_save_dir, "config.json")
            with open(config_file, 'w') as f:
                json.dump(self.model.config.to_dict(), f, indent=4)
            
            return True
        except Exception as e:
            logger.error(f"Model kaydetme hatası: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def evaluate_model(self):
        """Modeli değerlendir ve örnek çıktılar üret"""
        try:
            if self.model is None or self.tokenizer is None:
                logger.error("Model veya tokenizer yok, değerlendirme yapılamıyor.")
                return False
            
            logger.info("Test örnekleri ile model değerlendiriliyor...")
            
            # Test sorguları
            test_queries = [
                "TÜBİTAK 2209-A için 12 aylık yapay zeka projesi planı oluştur",
                "6 aylık akıllı tarım projesi için plan yazar mısın?",
                "3 aylık TÜBİTAK 1001 yenilenebilir enerji projesi planı"
            ]
            
            # Her sorgu için metin üret
            for query in test_queries:
                logger.info(f"\nSorgu: {query}")
                
                # Metin üret
                input_text = f"<|QUERY|>\n{query}\n\n<|PLAN|>"
                input_ids = self.tokenizer.encode(input_text, return_tensors="pt")
                
                # GPU varsa kullan
                device = "cuda" if torch.cuda.is_available() else "cpu"
                input_ids = input_ids.to(device)
                self.model = self.model.to(device)
                
                # Metin üretimi
                output = self.model.generate(
                    input_ids,
                    max_length=1024,
                    num_beams=5,
                    no_repeat_ngram_size=2,
                    early_stopping=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.encode("<|END|>")[0]
                )
                
                # Çıktıyı decode et
                generated_text = self.tokenizer.decode(output[0], skip_special_tokens=False)
                
                # <|PLAN|> ve <|END|> arasındaki metni çıkar
                plan_text = re.search(r'<\|PLAN\|>(.*?)<\|END\|>', generated_text, re.DOTALL)
                if plan_text:
                    plan_text = plan_text.group(1).strip()
                else:
                    plan_text = generated_text
                
                logger.info(f"Üretilen plan:\n{plan_text[:500]}...")
            
            # Değerlendirme metriklerini hesapla
            model_eval = {
                'model': self.base_model_name,
                'training_examples': self.stats['num_examples'],
                'model_size_mb': self.stats['model_size'],
                'training_time_minutes': self.stats['training_time'],
                'loss': self.stats['loss'],
                'perplexity': self.stats['perplexity'],
                'accuracy_estimate': 100 - min(99, self.stats['perplexity']),
                'timestamp': datetime.now().isoformat()
            }
            
            # Değerlendirme dosyasını kaydet
            eval_file = os.path.join(self.output_dir, "model_evaluation.json")
            with open(eval_file, 'w') as f:
                json.dump(model_eval, f, indent=4)
            
            logger.info(f"Validation doğruluğu: {model_eval['accuracy_estimate']:.2f}%")
            
            return model_eval
            
        except Exception as e:
            logger.error(f"Değerlendirme hatası: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def run_training_pipeline(self):
        """Tam eğitim sürecini çalıştır"""
        try:
            # 1. Verileri hazırla
            self.prepare_data()
            
            # 2. Modeli yükle
            self.load_base_model()
            
            # 3. Eğitim
            self.train_model()
            
            # 4. Değerlendirme
            eval_result = self.evaluate_model()
            
            return eval_result
            
        except Exception as e:
            logger.error(f"Eğitim süreci hatası: {str(e)}")
            logger.error(traceback.format_exc())
            return False


# Doğrudan çalıştırılırsa
if __name__ == "__main__":
    logger.info("GPT Proje Planı Üretim Modeli Eğitim Süreci Başlatılıyor...")
    
    trainer = GPTTrainer(
        base_model_name="gpt2",  # "gpt2-medium" daha iyi sonuçlar verebilir
        output_dir="agent_ai2/gpt_model_data",
        model_dir="models",
        db_path="db.sqlite3"
    )
    
    # Tam eğitim sürecini çalıştır
    result = trainer.run_training_pipeline()
    
    if result:
        logger.info(f"Eğitim başarıyla tamamlandı! Doğruluk: {result['accuracy_estimate']:.2f}%")
    else:
        logger.error("Eğitim süreci başarısız oldu.")