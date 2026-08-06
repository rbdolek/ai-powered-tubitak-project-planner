# data_preparation.py
import re
import json
import os
import logging
import traceback  # traceback'i import edin
from datetime import datetime

logger = logging.getLogger("DataProcessor")

class DataProcessor:
    """Veri hazırlama ve işleme sınıfı"""
    
    def __init__(self, db_connection_string=None):
        """Veri işleyici başlat"""
        self.db_connection = db_connection_string
        self.dataset_path = 'agent_memory/training_data.json'
        self.feedback_path = 'agent_memory/feedback_data.json'
        
        # Dizinleri oluştur
        os.makedirs(os.path.dirname(self.dataset_path), exist_ok=True)
        
        logger.info("DataProcessor başlatıldı")
    
    def prepare_data(self, query, fon_info=None):
        """
        Kullanıcı sorgusunu ve fon bilgilerini işleyerek model için hazırla
        
        Args:
            query (str): Kullanıcı sorusu/talebi
            fon_info (dict, optional): Fon bilgileri
            
        Returns:
            dict: İşlenmiş veri
        """
        try:
            # Metni temizle
            cleaned_text = self.clean_text(query)
            
            # Anahtar kelimeleri çıkar
            keywords = self.extract_keywords(cleaned_text)
            
            # Veri sözlüğünü oluştur
            processed_data = {
                "query": query,
                "cleaned_query": cleaned_text,
                "keywords": keywords
            }
            
            # Fon bilgilerini ekle (varsa)
            if fon_info:
                processed_data["fon_kodu"] = fon_info.get("fon_kodu", "")
                processed_data["fon_turu"] = fon_info.get("fon_turu", "")
                processed_data["ay_suresi"] = fon_info.get("ay_suresi", 0)
            else:
                # Sorgudan fon bilgilerini çıkarmaya çalış
                fon_kodu = self.extract_fon_code(cleaned_text)
                ay_suresi = self.extract_months(cleaned_text)
                
                if fon_kodu:
                    processed_data["fon_kodu"] = fon_kodu
                    
                if ay_suresi:
                    processed_data["ay_suresi"] = ay_suresi
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Veri hazırlama hatası: {str(e)}")
            # Hata durumunda en azından orijinal sorguyu içeren basit bir veri yapısı döndür
            return {"query": query}
    
    def clean_text(self, text):
        """Metni temizle"""
        # Küçük harfe çevir
        text = text.lower()
        
        # Gereksiz boşlukları temizle
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Özel karakterleri temizle (noktalama işaretleri hariç)
        text = re.sub(r'[^a-zA-ZçğıöşüÇĞİÖŞÜ0-9\s\.,;:!?]', '', text)
        
        return text
    
    def extract_keywords(self, text):
        """Metinden anahtar kelimeleri çıkar"""
        # Stopwords (durma kelimeleri)
        stopwords = ['ve', 'veya', 'ile', 'için', 'bu', 'bir', 'da', 'de', 'mi', 'mı']
        
        # Kelimelere ayır
        words = text.split()
        
        # Durma kelimelerini çıkar
        keywords = [word for word in words if word not in stopwords and len(word) > 2]
        
        # En sık geçen kelimeleri al (max 10)
        from collections import Counter
        word_counts = Counter(keywords)
        top_keywords = [word for word, count in word_counts.most_common(10)]
        
        return top_keywords
    
    def extract_fon_code(self, text):
        """Metinden TÜBİTAK fon kodunu çıkar"""
        # TÜBİTAK fon kodları genelde 4 basamaklıdır (örn: 1001, 3501)
        fon_match = re.search(r'\b([1-9]\d{3})\b', text)
        
        if fon_match:
            return fon_match.group(1)
        
        # Bazı özel durumlar
        if "bilimsel araştırma" in text or "akademik" in text:
            return "1001"
        elif "kariyer" in text:
            return "3501"
        elif "sanayi" in text or "ar-ge" in text:
            return "1505"
        
        return ""
    
    def extract_months(self, text):
        """Metinden ay süresini çıkar"""
        # "X aylık" gibi ifadeleri ara
        ay_match = re.search(r'(\d+)\s*ayl[ıi]k', text, re.IGNORECASE)
        
        if ay_match:
            return int(ay_match.group(1))
        
        # Diğer anahtar ifadeleri kontrol et
        if "doktora" in text:
            return 36  # Tipik doktora projesi
        elif "yüksek lisans" in text or "master" in text:
            return 24  # Tipik yüksek lisans projesi
        
        return 0
    
    def update_dataset_with_feedback(self, query, response, feedback_score, features=None):
        """
        Kullanıcı geri bildirimiyle veri setini güncelle
        
        Args:
            query (str): Kullanıcı sorusu
            response (str): Oluşturulan yanıt
            feedback_score (int): Kullanıcı puanı (1-5)
            features (dict, optional): Ek özellikler
        """
        # Feedback verisi oluştur
        feedback_item = {
            'query': query,
            'response': response,
            'score': feedback_score,
            'features': features,
            'timestamp': datetime.now().isoformat()
        }
        
        # Feedback verisini kaydet
        try:
            # Mevcut verileri yükle veya yeni dosya oluştur
            feedback_data = []
            
            if os.path.exists(self.feedback_path):
                with open(self.feedback_path, 'r', encoding='utf-8') as f:
                    feedback_data = json.load(f)
            
            # Yeni veriyi ekle
            feedback_data.append(feedback_item)
            
            # Dosyaya kaydet
            with open(self.feedback_path, 'w', encoding='utf-8') as f:
                json.dump(feedback_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Geri bildirim verisi kaydedildi: {self.feedback_path}")
            
        except Exception as e:
            logger.error(f"Geri bildirim verisi kaydedilirken hata: {e}")
    
    def load_training_data(self):
        """Eğitim verilerini yükle"""
        try:
            if os.path.exists(self.dataset_path):
                with open(self.dataset_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"Eğitim veri dosyası bulunamadı: {self.dataset_path}")
                return []
                
        except Exception as e:
            logger.error(f"Eğitim verileri yüklenirken hata: {e}")
            return []
    
    def load_feedback_data(self):
        """Geri bildirim verilerini yükle"""
        try:
            if os.path.exists(self.feedback_path):
                with open(self.feedback_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"Geri bildirim veri dosyası bulunamadı: {self.feedback_path}")
                return []
                
        except Exception as e:
            logger.error(f"Geri bildirim verileri yüklenirken hata: {e}")
            return []

    def prepare_training_data(self):
        """Eğitim verilerini hazırla"""
        try:
            # Veri dizinlerini oluştur
            os.makedirs('agent_memory/data', exist_ok=True)
            
            # Şablon ve geri bildirim verilerini yükle
            templates_path = 'agent_memory/templates/plan_templates.json'
            feedback_path = 'agent_memory/feedback_data.json'
            
            input_texts = []
            output_texts = []
            
            # Şablonlardan veri oluştur
            if os.path.exists(templates_path):
                with open(templates_path, 'r', encoding='utf-8') as f:
                    templates = json.load(f)
                
                # Her şablon türü için örnek girdiler ve çıktılar oluştur
                for duration_type, template in templates.items():
                    # Süre bilgisini çıkar
                    if duration_type == "short":
                        months = [1, 2, 3]
                    elif duration_type == "medium":
                        months = [4, 5, 6]
                    else:  # "long"
                        months = [12, 18, 24]
                    
                    # Farklı fon kodları
                    fon_codes = ["1001", "1002", "1005", "2209-A", "2209-B", "3501"]
                    
                    # Her süre ve fon kodu için örnek cümleler oluştur
                    for month in months:
                        for fon_code in fon_codes:
                            # Girdi cümleleri
                            input_examples = [
                                f"TÜBİTAK {fon_code} için {month} aylık proje planı oluştur",
                                f"{month} aylık {fon_code} projesi nasıl yapılır?",
                                f"{fon_code} araştırma projesi için {month} aylık plan yazar mısın?",
                                f"{month} aylık bir {fon_code} fonuna başvurmak istiyorum. Plan hazırlar mısın?"
                            ]
                            
                            # Her faz için çıktı metni oluştur
                            output_text = ""
                            output_text += f"TÜBİTAK {fon_code} Projesi - {month} Aylık Plan\n\n"
                            
                            # Fazları ekleme
                            for phase in template["structure"]:
                                output_text += f"{phase}:\n"
                                # Görevleri ekleme
                                for task in template["tasks"].get(phase, ["Görev belirlenmedi"]):
                                    output_text += f"- {task}\n"
                                output_text += "\n"
                            
                            # Veri setine ekle
                            for input_example in input_examples:
                                input_texts.append(input_example)
                                output_texts.append(output_text)
            
            # Geri bildirimlerden veri oluştur
            if os.path.exists(feedback_path):
                with open(feedback_path, 'r', encoding='utf-8') as f:
                    feedback_data = json.load(f)
                
                # Yüksek puanlı geri bildirimleri seç
                high_quality_feedback = [
                    item for item in feedback_data
                    if item.get('score', 0) >= 4  # 4 ve 5 puanlı geri bildirimler
                    and 'query' in item
                    and 'response' in item
                ]
                
                # Veri setine ekle
                for item in high_quality_feedback:
                    input_texts.append(item['query'])
                    output_texts.append(item['response'])
            
            # Eğitim verisini kaydet
            train_data = {
                "input_texts": input_texts,
                "output_texts": output_texts
            }
            
            with open('agent_memory/data/training_data.json', 'w', encoding='utf-8') as f:
                json.dump(train_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Eğitim verisi hazırlandı: {len(input_texts)} örnek")
            return input_texts, output_texts
            
        except Exception as e:
            logger.error(f"Eğitim verisi hazırlanırken hata: {str(e)}")
            logger.error(traceback.format_exc())
            return [], []


# Fonksiyonları dışa aktar (geriye dönük uyumluluk için)
prepare_data = DataProcessor.prepare_data
clean_text = DataProcessor.clean_text
extract_keywords = DataProcessor.extract_keywords
extract_fon_code = DataProcessor.extract_fon_code
extract_months = DataProcessor.extract_months
prepare_training_data = DataProcessor.prepare_training_data