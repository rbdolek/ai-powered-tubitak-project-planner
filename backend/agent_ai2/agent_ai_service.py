# agent_ai/agent_ai_service.py
import os
import re
import time
import logging
import traceback
from datetime import datetime
import json

from .agent_ai_model import AgentAIModel

# Günlük kaydı yapılandırma
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_ai2/logs/agent_ai_service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AgentAIService")

class AgentAIService:
    """Yapay zeka plan oluşturma servisi"""
    
    def __init__(self, model=None):
        """AI servisini başlat"""
        self.model = model or AgentAIModel()
    
    def classify(self, query):
        """Metni sınıflandır (geriye dönük uyumluluk için)"""
        try:
            if not query or len(query.strip()) == 0:
                return {
                    "class": 0,
                    "class_name": "Genel Bilgi",
                    "confidence": 0.0,
                    "all_scores": [0.0, 0.0, 0.0, 0.0],
                    "duration_months": 0
                }
            
            # Model kaynaklarını yükle
            if not hasattr(self.model, 'tokenizer') or self.model.tokenizer is None:
                if not self.model.load_resources():
                    logger.error("Model yüklenemedi!")
                    return {
                        "class": 0,
                        "confidence": 0.0,
                        "error": "Model yüklenemedi!"
                    }
            
            # Sınıflandırma yap
            result = self.model.predict(query)
            
            return result
            
        except Exception as e:
            error_msg = f"Sınıflandırma hatası: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {
                "class": 0,
                "confidence": 0.0,
                "error": error_msg
            }
    
    def generate_response(self, query, fon_id=None, fon_data=None):
        """Kullanıcı sorgusuna yanıt oluştur: GPT modeli ile metin üretir"""
        logger.info(f"Sorgu ile metin üretiliyor: {query[:50]}...")
        try:
            # Model kaynaklarını yükle
            if not hasattr(self.model, 'tokenizer') or self.model.tokenizer is None:
                if not self.model.load_resources():
                    logger.error("Model yüklenemedi!")
                    return "Model yüklenemedi. Lütfen sistem yöneticisiyle iletişime geçin.", None

            # Fon bilgilerini sorgudan çıkar
            fon_info = self._extract_fon_info(query)
            
            # Eğer dışardan fon_data verilmişse üzerine yaz
            if fon_data:
                fon_info.update({
                    'fon_kodu': fon_data.get('kod', fon_info.get('fon_kodu')),
                    'fon_turu': fon_data.get('tur', fon_info.get('fon_turu')),
                    'ay_suresi': fon_data.get('ay_suresi', fon_info.get('ay_suresi'))
                })

            # Zenginleştirilmiş sorgu oluştur
            enriched_query = query
            ay_suresi = fon_info.get('ay_suresi', 0) or 12
            fon_kodu = fon_info.get('fon_kodu', '')
            
            # Sorgu içinde fon bilgileri yoksa zenginleştir
            if fon_kodu and fon_kodu not in query:
                enriched_query = f"TÜBİTAK {fon_kodu} için " + query
            
            if ay_suresi > 0 and not re.search(r'\d+\s*ay', query, re.IGNORECASE):
                enriched_query = f"{ay_suresi} aylık " + enriched_query
            
            # Başlangıç zamanını kaydet
            start_time = time.time()
            
            # GPT modeli ile doğrudan metin üret
            generated_text = self.model.generate_text(enriched_query)
            
            # Geçen süreyi hesapla
            generation_time = time.time() - start_time
            
            # Üretilen metni TÜBİTAK formatına uygun hale getir
            formatted_text = self._format_generated_text(generated_text, fon_info)
            
            # GPT imzası
            if "[TÜBİTAK GPT AI tarafından oluşturuldu" not in formatted_text:
                formatted_text += f"\n\n[TÜBİTAK GPT AI tarafından oluşturuldu - {generation_time:.2f} saniye]"

            # Model değerlendirme bilgilerini yükle
            model_eval = {}
            eval_file = "agent_ai2/gpt_model_data/model_evaluation.json"
            if os.path.exists(eval_file):
                with open(eval_file, 'r') as f:
                    model_eval = json.load(f)
            
            # Meta veri
            response_meta = {
                'fon_info': fon_info,
                'plan_generated': True,
                'model_accuracy': model_eval.get('accuracy_estimate', 85.5),  # varsayılan değer
                'timestamp': datetime.now().isoformat(),
                'generation_time': generation_time,
                'generated_raw': generated_text,  # Ham üretilen metni de saklayalım
                'model_type': 'GPT2'  # Model tipi
            }
            
            return formatted_text, response_meta

        except Exception as e:
            error_msg = f"Metin üretme hatası: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return ("Üzgünüm, proje planı oluşturulurken bir hata oluştu.", None)
    
    def _extract_fon_info(self, query):
        """Sorgudan fon bilgilerini çıkar"""
        fon_info = {
            'fon_kodu': '',
            'fon_turu': '',
            'ay_suresi': 0
        }
        
        # Fon kodu
        fon_pattern = r'\b(TÜBİTAK\s+)?(\d{4}(-[A-Z])?)\b'
        fon_match = re.search(fon_pattern, query, re.IGNORECASE)
        if fon_match:
            fon_info['fon_kodu'] = fon_match.group(2)
            
            # Fon türünü belirle
            if fon_info['fon_kodu'].startswith('1001'):
                fon_info['fon_turu'] = 'Bilimsel ve Teknolojik Araştırma Projelerini Destekleme Programı'
            elif fon_info['fon_kodu'].startswith('1005'):
                fon_info['fon_turu'] = 'Ulusal Yeni Fikirler ve Ürünler Araştırma Destek Programı'
            elif fon_info['fon_kodu'].startswith('3501'):
                fon_info['fon_turu'] = 'Kariyer Geliştirme Programı'
            elif fon_info['fon_kodu'].startswith('2209'):
                fon_info['fon_turu'] = 'Üniversite Öğrencileri Araştırma Projeleri Destekleme Programı'
        
        # Ay süresi
        month_pattern = r'(\d+)\s*ayl[ıiİI]k'
        month_match = re.search(month_pattern, query, re.IGNORECASE)
        if month_match:
            fon_info['ay_suresi'] = int(month_match.group(1))
        
        return fon_info
    
    def _format_generated_text(self, text, fon_info):
        """Üretilen metni düzenle ve format sorunlarını gider"""
        # Başlık ekle
        ay_suresi = fon_info.get('ay_suresi', 0) or 12
        fon_kodu = fon_info.get('fon_kodu', '')
        
        # Eğer metin zaten formatlanmışsa ve temizse, fazla düzenleme yapma
        if text.strip().startswith("TÜBİTAK") and ":" in text and "-" in text:
            return text
        
        # Başlık oluştur
        header = f"TÜBİTAK {fon_kodu} PROJESİ - {ay_suresi} AYLIK PLAN\n\n"
        
        # Üretilen metinde zaten başlık varsa silme
        if re.search(r'TÜBİTAK.*Plan', text[:100], re.IGNORECASE):
            header = ""
        
        # Metin düzenleme
        # 1. Fazlalık boşlukları temizle
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 2. Her satırın başındaki - işaretini düzgün hale getir
        text = re.sub(r'(?<=\n)\s*-\s*', '- ', text)
        
        # 3. Ay: formatını düzgün hale getir
        text = re.sub(r'(?<=\n)Ay\s*(\d+)\s*:?', r'Ay \1:', text)
        text = re.sub(r'(?<=\n)Ay\s*(\d+)-(\d+)\s*:?', r'Ay \1-\2:', text)
        
        # 4. Tamamlanmamış cümleleri temizle
        text = re.sub(r'\b\w{1,2}$', '', text)
        
        # 5. Madde işaretlerini ekle
        lines = text.split('\n')
        result_lines = []
        
        for line in lines:
            line = line.strip()
            if line and ":" not in line and not line.startswith("-") and not line.startswith("•"):
                if line.lower().startswith(("ay ", "hafta ", "gün ")):
                    result_lines.append(line)
                else:
                    result_lines.append("- " + line)
            else:
                result_lines.append(line)
        
        text = '\n'.join(result_lines)
        
        # Fazlalık satır sonlarını düzelt
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return header + text