# agent_ai/agent_ai_model.py
import os
import re
import json
import logging
import traceback
import torch
import numpy as np
from datetime import datetime
from transformers import GPT2LMHeadModel, GPT2Tokenizer

logger = logging.getLogger("AgentAI")

class AgentAIModel:
    """GPT tabanlı proje planı üretim modeli"""

    def __init__(self, 
                model_dir='models/gpt2_tubitak_plan',
                max_length=1024):
        """Model nesnesi oluştur"""
        self.model_dir = model_dir
        self.max_length = max_length
        
        # Model ve tokenizer
        self.model = None
        self.tokenizer = None
        
        # Sınıf isimleri (geriye dönük uyumluluk için)
        self.class_names = ["Genel Bilgi", "Kısa Vadeli (1-3 ay)", "Orta Vadeli (4-6 ay)", "Uzun Vadeli (7+ ay)"]
        
    def load_resources(self):
        """Model ve tokenizer'ı yükle"""
        try:
            # Model ve tokenizer'ı kontrol et
            if not os.path.exists(self.model_dir):
                logger.error(f"Model dizini bulunamadı: {self.model_dir}")
                return False
            
            # Tokenizer'ı yükle
            self.tokenizer = GPT2Tokenizer.from_pretrained(self.model_dir)
            logger.info(f"Tokenizer yüklendi: {self.model_dir}")
            
            # Model'i yükle
            self.model = GPT2LMHeadModel.from_pretrained(self.model_dir)
            logger.info(f"Model yüklendi: {self.model_dir}")
            
            # Pad token kontrolü
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # GPU varsa kullan
            if torch.cuda.is_available():
                self.model = self.model.to("cuda")
                logger.info("Model GPU'ya taşındı")
            
            return True
            
        except Exception as e:
            logger.error(f"Model kaynakları yüklenirken hata: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def predict(self, text):
        """Metni sınıflandır (geriye dönük uyumluluk için)"""
        try:
            # Plan süresini tahmini çıkar
            duration_months = self._extract_duration_from_query(text)
            
            if duration_months <= 0:
                predicted_class = 0  # Genel
                confidence = 0.6
            elif duration_months <= 3:
                predicted_class = 1  # Kısa Vadeli
                confidence = 0.8
            elif duration_months <= 6:
                predicted_class = 2  # Orta Vadeli
                confidence = 0.8
            else:
                predicted_class = 3  # Uzun Vadeli
                confidence = 0.8
            
            # Sınıf adını belirle
            class_name = self.class_names[predicted_class]
            
            # Yapay skorları oluştur
            all_scores = [0.1, 0.1, 0.1, 0.1]
            all_scores[predicted_class] = confidence
            
            return {
                "class": predicted_class,
                "class_name": class_name,
                "confidence": confidence,
                "all_scores": all_scores,
                "duration_months": duration_months
            }
            
        except Exception as e:
            logger.error(f"Tahmin hatası: {str(e)}")
            logger.error(traceback.format_exc())
            return {"class": 0, "confidence": 0, "error": str(e)}
    
    def _extract_duration_from_query(self, query):
        """Sorgudan ay süresini çıkar"""
        month_pattern = r'(\d+)\s*ayl[ıiİI]k'
        match = re.search(month_pattern, query)
        if match:
            return int(match.group(1))
        return 0
    
    def generate_text(self, query):
        """GPT modeli ile metin üret"""
        try:
            # Model ve tokenizer kontrolü
            if self.model is None or self.tokenizer is None:
                if not self.load_resources():
                    raise ValueError("Model ve tokenizer'lar yüklenemedi!")
            
            # Sorguyu zenginleştir
            enriched_query = self._enrich_query(query)
            logger.info(f"Zenginleştirilmiş sorgu: {enriched_query}")
            
            # GPT girdi formatı
            input_text = f"<|QUERY|>\n{enriched_query}\n\n<|PLAN|>"
            
            # Tokenize et
            input_ids = self.tokenizer.encode(input_text, return_tensors="pt")
            
            # GPU varsa kullan
            if torch.cuda.is_available():
                input_ids = input_ids.to("cuda")
            
            # Başlangıç zamanı
            start_time = datetime.now()
            
            # Metin üretimi
            output = self.model.generate(
                input_ids,
                max_length=self.max_length,
                num_beams=5,
                temperature=0.7,
                no_repeat_ngram_size=2,
                early_stopping=True,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.encode("<|END|>")[0] if "<|END|>" in self.tokenizer.get_vocab() else None
            )
            
            # Geçen süre
            generation_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Metin üretim süresi: {generation_time:.2f} saniye")
            
            # Çıktıyı decode et
            generated_text = self.tokenizer.decode(output[0], skip_special_tokens=False)
            
            # <|PLAN|> ve <|END|> arasındaki metni çıkar
            plan_text = re.search(r'<\|PLAN\|>(.*?)(<\|END\|>|$)', generated_text, re.DOTALL)
            if plan_text:
                plan_text = plan_text.group(1).strip()
            else:
                plan_text = generated_text.replace("<|QUERY|>", "").replace("<|PLAN|>", "").replace("<|END|>", "").strip()
            
            # Metni düzenle
            cleaned_text = self.clean_generated_text(plan_text)
            
            # GPT imzası ekle
            cleaned_text += f"\n\n[TÜBİTAK GPT AI tarafından oluşturuldu - {generation_time:.2f} saniye]"
            
            return cleaned_text
            
        except Exception as e:
            logger.error(f"Metin üretme hatası: {str(e)}")
            logger.error(traceback.format_exc())
            return f"Metin üretilirken bir hata oluştu: {str(e)}"
    
    def _enrich_query(self, query):
        """Sorguyu zenginleştir"""
        # Sorgudan fon kodu ve süre çıkar
        fon_pattern = r'\b(TÜBİTAK\s+)?(\d{4}(-[A-Z])?)\b'
        fon_match = re.search(fon_pattern, query, re.IGNORECASE)
        fon_code = fon_match.group(2) if fon_match else None
        
        month_pattern = r'(\d+)\s*ayl[ıiİI]k'
        month_match = re.search(month_pattern, query)
        duration = int(month_match.group(1)) if month_match else None
        
        # Eğer fon kodu yoksa, varsayılan olarak 1001 ekle
        if fon_code is None:
            if "TÜBİTAK" not in query:
                query = "TÜBİTAK 1001 " + query
            else:
                query = query.replace("TÜBİTAK", "TÜBİTAK 1001")
        
        # Eğer süre yoksa, varsayılan olarak 12 ay ekle
        if duration is None and not month_match:
            if "aylık" not in query.lower():
                query = "12 aylık " + query
        
        return query
    
    def clean_generated_text(self, text):
        """Üretilen metni düzelt ve iyileştir"""
        if not text:
            return "GPT modelinin ürettiği metin boş."
        
        # Fazla boşlukları temizle
        text = re.sub(r'\s+', ' ', text).strip()
        
        # TÜBİTAK proje başlığını düzelt
        if "tubitak" in text.lower() and not "TÜBİTAK" in text:
            # Fon kodu bul
            fon_pattern = r'tubitak\s+(\d{4}(-[a-z])?)'
            fon_match = re.search(fon_pattern, text, re.IGNORECASE)
            fon_code = fon_match.group(1) if fon_match else "1001"
            
            # Ay süresini bul
            month_pattern = r'(\d+)\s*ayl[ıiİI]k'
            month_match = re.search(month_pattern, text)
            duration = month_match.group(1) if month_match else "12"
            
            # Başlık oluştur
            header = f"TÜBİTAK {fon_code.upper()} PROJESİ - {duration} AYLIK PLAN\n\n"
            
            # Eski başlığı kaldır
            text = re.sub(r'(?i)tubitak\s+\d{4}(-[a-z])?\s+projesi.*?\n', '', text)
            text = header + text
        
        # Ay ifadelerini düzelt
        text = re.sub(r'(?i)ay\s+(\d+)([^:])', r'Ay \1:\2', text)
        text = re.sub(r'(?i)ay\s+(\d+)-(\d+)([^:])', r'Ay \1-\2:\3', text)
        
        # Satırlara böl ve her satırı işle
        lines = text.split('\n')
        result_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                result_lines.append(line)
                continue
                
            # Ay başlığı mı kontrol et
            if re.match(r'(?i)ay\s+\d+', line) and not line.endswith(':'):
                line += ":"
            
            # Görev maddesini kontrol et - ay başlığı değilse ve - ile başlamıyorsa
            if not re.match(r'(?i)ay\s+\d+', line) and not line.startswith('-') and not line.startswith('•') and ":" not in line:
                line = "- " + line
            
            result_lines.append(line)
        
        # Satırları birleştir
        text = '\n'.join(result_lines)
        
        # Fazla boşlukları temizle
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text