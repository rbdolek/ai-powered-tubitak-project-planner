# agent_ai/agent_ai_service.py
import json
import os
import pandas as pd
import pyodbc
import re
import nltk
from nltk.tokenize import sent_tokenize
import threading
import time
import logging
import traceback
from datetime import datetime
import random
from agent_ai.agent_ai_model import AgentAIModel


# NLTK kaynaklarını yükle
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Günlük oluştur
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_ai_service.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("AgentAIService")

class AgentAIService:
    """
    TÜBİTAK Proje Planı Agent AI Servisi
    LSTM modelini kullanarak kullanıcı sorgularını analiz eder ve
    TÜBİTAK proje planları oluşturur.
    """
    
    def __init__(self, db_connection_string=None):
        """Agent AI servisini başlat"""
        # Veritabanı bağlantı bilgileri
        self.db_connection_string = db_connection_string or 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=tubitak_db;Trusted_Connection=yes;'
        
        # Model yükleme
        self.model = AgentAIModel()
        
        # Şablon ve plan verileri için klasörler
        self.memory_dir = 'agent_memory'
        self.templates_dir = os.path.join(self.memory_dir, 'templates')
        self.feedback_dir = os.path.join(self.memory_dir, 'feedback')
        self.data_dir = os.path.join(self.memory_dir, 'data')
        
        # Dizinleri oluştur
        os.makedirs(self.memory_dir, exist_ok=True)
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.feedback_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Şablon yanıtları ve plan şablonlarını yükle
        self.response_templates = self._load_response_templates()
        self.plan_templates = self._load_plan_templates()
        
        # Veritabanından fon verilerini çek
        self.fon_bilgileri = self._load_fon_info_from_db()
        
        # Veritabanından eğitim verilerini yükle ve modeli iyileştir
        self._refresh_training_data()
        
        # Otomatik yeniden eğitim için iş parçacığı başlat
        self.should_stop = False
        self.retraining_thread = threading.Thread(target=self._auto_retrain_job)
        self.retraining_thread.daemon = True
        self.retraining_thread.start()
        
        logger.info("AgentAIService başlatıldı - Versiyon 2.0 (DB Entegrasyonu)")
    
    def connect_to_db(self):
        """Veritabanına bağlanır ve bir bağlantı nesnesi döndürür"""
        try:
            conn = pyodbc.connect(self.db_connection_string)
            logger.info("Veritabanı bağlantısı başarılı")
            return conn
        except Exception as e:
            logger.error(f"Veritabanı bağlantı hatası: {str(e)}")
            raise
    
    def _load_fon_info_from_db(self):
        """Veritabanından fon bilgilerini yükle"""
        try:
            logger.info("Veritabanından fon bilgileri yükleniyor...")
            
            query = """
            SELECT 
                id,
                kod, 
                tur, 
                ay_suresi, 
                aciklama
            FROM 
                dbo.chat_fon
            WHERE
                aktif = 1 OR aktif IS NULL
            ORDER BY 
                kod ASC
            """
            
            conn = self.connect_to_db()
            df = pd.read_sql(query, conn)
            conn.close()
            
            # Fon bilgilerini sözlük olarak dönüştür
            fon_bilgileri = {}
            for _, row in df.iterrows():
                fon_bilgileri[row['kod']] = {
                    'id': row['id'],
                    'tur': row['tur'],
                    'ay_suresi': row['ay_suresi'],
                    'aciklama': row['aciklama']
                }
            
            logger.info(f"{len(fon_bilgileri)} adet fon bilgisi yüklendi")
            return fon_bilgileri
            
        except Exception as e:
            logger.error(f"Fon bilgileri yüklenirken hata: {str(e)}")
            logger.error(traceback.format_exc())
            return {}
    
    def _fetch_training_data(self):
        """Veritabanından eğitim verilerini çek"""
        try:
            logger.info("Veritabanından eğitim verileri çekiliyor...")
            
            query = """
            SELECT 
                cm.id AS message_id,
                cm.content AS message_content,
                cm.is_user,
                cm.timestamp AS message_timestamp,
                cs.id AS session_id,
                cs.ai_model,
                cs.title AS session_title,
                ap.plan_metni AS response_content,
                ap.ay_suresi,
                ap.meta_data,
                f.kod AS fon_kod,
                f.tur AS fon_tur,
                uf.puan AS feedback_score
            FROM 
                dbo.chat_chatmessage cm
            JOIN 
                dbo.chat_chatsession cs ON cm.session_id = cs.id
            LEFT JOIN 
                dbo.chat_aiplan ap ON cm.related_plan_id = ap.id
            LEFT JOIN 
                dbo.chat_fon f ON f.id = ap.fon_id
            LEFT JOIN
                dbo.chat_userfeedback uf ON uf.plan_id = ap.id
            WHERE 
                cm.is_user = 1
            ORDER BY 
                cs.created_at DESC, cm.timestamp ASC
            """
            
            conn = self.connect_to_db()
            df = pd.read_sql(query, conn)
            conn.close()
            
            logger.info(f"{len(df)} adet eğitim verisi çekildi")
            
            # Verileri işle
            processed_data = []
            for _, row in df.iterrows():
                try:
                    # Temel bilgiler
                    data_item = {
                        'query': row['message_content'],
                        'response': row['response_content'] if pd.notna(row['response_content']) else '',
                        'feedback_score': row['feedback_score'] if pd.notna(row['feedback_score']) else 0,
                        'features': {
                            'fon_kodu': row['fon_kod'] if pd.notna(row['fon_kod']) else '',
                            'fon_turu': row['fon_tur'] if pd.notna(row['fon_tur']) else '',
                            'ay_suresi': row['ay_suresi'] if pd.notna(row['ay_suresi']) else 0
                        },
                        'timestamp': row['message_timestamp'].isoformat() if pd.notna(row['message_timestamp']) and hasattr(row['message_timestamp'], 'isoformat') else datetime.now().isoformat()
                    }
                    
                    # Meta verisi varsa ekle
                    if pd.notna(row['meta_data']):
                        try:
                            meta_data = json.loads(row['meta_data'])
                            data_item['meta'] = meta_data
                        except:
                            pass
                    
                    processed_data.append(data_item)
                except Exception as e:
                    logger.error(f"Veri işleme hatası: {str(e)}")
                    continue
            
            # İşlenmiş verileri kaydet
            training_data_path = os.path.join(self.data_dir, 'training_data.json')
            with open(training_data_path, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"{len(processed_data)} adet işlenmiş veri kaydedildi")
            return processed_data
            
        except Exception as e:
            logger.error(f"Eğitim verileri çekilirken hata: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    def _fetch_feedback_data(self):
        """Veritabanından geri bildirim verilerini çek"""
        try:
            logger.info("Veritabanından geri bildirim verileri çekiliyor...")
            
            query = """
            SELECT 
                uf.id AS feedback_id,
                uf.puan AS score,
                uf.yorum AS comment,
                uf.olusturma_tarihi AS timestamp,
                ap.plan_metni AS plan_content,
                ap.ay_suresi AS duration,
                ap.meta_data AS meta_data,
                f.kod AS fon_kod,
                f.tur AS fon_tur
            FROM 
                dbo.chat_userfeedback uf
            JOIN 
                dbo.chat_aiplan ap ON uf.plan_id = ap.id
            LEFT JOIN 
                dbo.chat_fon f ON f.id = ap.fon_id
            WHERE 
                uf.puan IS NOT NULL
            ORDER BY 
                uf.olusturma_tarihi DESC
            """
            
            conn = self.connect_to_db()
            df = pd.read_sql(query, conn)
            conn.close()
            
            logger.info(f"{len(df)} adet geri bildirim verisi çekildi")
            
            # Verileri işle
            feedback_data = []
            for _, row in df.iterrows():
                try:
                    # Temel bilgiler
                    data_item = {
                        'feedback_id': row['feedback_id'],
                        'score': row['score'] if pd.notna(row['score']) else 0,
                        'comment': row['comment'] if pd.notna(row['comment']) else '',
                        'response': row['plan_content'] if pd.notna(row['plan_content']) else '',
                        'features': {
                            'fon_kodu': row['fon_kod'] if pd.notna(row['fon_kod']) else '',
                            'fon_turu': row['fon_tur'] if pd.notna(row['fon_tur']) else '',
                            'ay_suresi': row['duration'] if pd.notna(row['duration']) else 0
                        },
                        'timestamp': row['timestamp'].isoformat() if pd.notna(row['timestamp']) and hasattr(row['timestamp'], 'isoformat') else datetime.now().isoformat()
                    }
                    
                    # Metaveri varsa ekle
                    if pd.notna(row['meta_data']):
                        try:
                            meta_data = json.loads(row['meta_data'])
                            if 'query_info' in meta_data and 'original_query' in meta_data['query_info']:
                                data_item['query'] = meta_data['query_info']['original_query']
                        except:
                            pass
                    
                    feedback_data.append(data_item)
                except Exception as e:
                    logger.error(f"Geri bildirim verisi işleme hatası: {str(e)}")
                    continue
            
            # İşlenmiş geri bildirimleri kaydet
            feedback_data_path = os.path.join(self.feedback_dir, 'feedback_data.json')
            with open(feedback_data_path, 'w', encoding='utf-8') as f:
                json.dump(feedback_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"{len(feedback_data)} adet işlenmiş geri bildirim kaydedildi")
            return feedback_data
            
        except Exception as e:
            logger.error(f"Geri bildirim verileri çekilirken hata: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    def _refresh_training_data(self):
        """Veritabanından eğitim verilerini yeniden yükle ve şablonları güncelle"""
        try:
            # Veritabanından verileri çek
            training_data = self._fetch_training_data()
            feedback_data = self._fetch_feedback_data()
            
            # Fon bilgilerini güncelle
            self.fon_bilgileri = self._load_fon_info_from_db()
            
            # Yanıt şablonlarını güncelle
            for item in feedback_data:
                if item['score'] >= 4:  # Yüksek puanlı yanıtlar
                    response = item['response']
                    features = item['features']
                    ay_suresi = features.get('ay_suresi', 0)
                    
                    # Cevabın sınıfını belirle
                    class_id = 0  # Varsayılan
                    if ay_suresi > 0:
                        if ay_suresi <= 3:
                            class_id = 1  # Kısa
                        elif ay_suresi <= 6:
                            class_id = 2  # Orta
                        elif ay_suresi <= 12:
                            class_id = 3  # Standart
                        else:
                            class_id = 4  # Uzun
                    
                    # Yanıtı daha kompakt hale getir
                    compact_response = response
                    
                    # Uzun yanıtları özet haline getir
                    if len(response) > 500:
                        sentences = sent_tokenize(response)
                        if len(sentences) > 5:
                            important_sentences = sentences[:2] + sentences[-3:]
                            compact_response = " ".join(important_sentences)
                    
                    # Şablonları güncelle
                    self._update_response_templates(class_id, compact_response)
            
            logger.info(f"Eğitim verileri yenilendi: {len(training_data)} eğitim, {len(feedback_data)} geri bildirim")
            return True
            
        except Exception as e:
            logger.error(f"Eğitim verileri yenilenirken hata: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _load_response_templates(self):
        """Yanıt şablonlarını yükle"""
        templates_path = os.path.join(self.templates_dir, 'response_templates.json')
        
        # Varsayılan şablonlar
        default_templates = {
            "0": ["Bu konu hakkında bilgim yok. Lütfen TÜBİTAK fonu ve proje süresi konusunda daha fazla bilgi verir misiniz?"],
            "1": ["3 aylık plan şablonu: {fon_kodu} {fon_turu} fonu için kısa vadeli 3 aylık bir plan oluşturulacak."],
            "2": ["6 aylık plan şablonu: {fon_kodu} {fon_turu} fonu için orta vadeli 6 aylık bir plan oluşturulacak."],
            "3": ["12 aylık plan şablonu: {fon_kodu} {fon_turu} fonu için 1 yıllık program şu adımlardan oluşacak."],
            "4": ["{fon_kodu} {fon_turu} fonu için {ay_suresi} aylık kapsamlı bir proje planı oluşturulacak."]
        }
        
        # Şablon dosyası varsa yükle, yoksa varsayılanları kullan
        if os.path.exists(templates_path):
            try:
                with open(templates_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Şablonlar yüklenirken hata: {e}")
                return default_templates
        else:
            # Varsayılan şablonları kaydet
            with open(templates_path, 'w', encoding='utf-8') as f:
                json.dump(default_templates, f, ensure_ascii=False, indent=2)
            
            return default_templates
    
    def _load_plan_templates(self):
        """Proje planı şablonlarını yükle"""
        templates_path = os.path.join(self.templates_dir, 'plan_templates.json')
        
        # Varsayılan plan şablonları
        default_templates = {
            "short": {  # 1-3 ay
                "structure": [
                    "Hazırlık Aşaması",
                    "Uygulama Aşaması",
                    "Sonuçlandırma Aşaması"
                ],
                "tasks": {
                    "Hazırlık Aşaması": [
                        "Literatür taraması",
                        "Metodoloji geliştirme",
                        "Veri kaynaklarının belirlenmesi",
                        "Etik kurul izinlerinin alınması"
                    ],
                    "Uygulama Aşaması": [
                        "Veri toplama",
                        "Verilerin analizi",
                        "Ara rapor hazırlama",
                        "Metodoloji revizyonu"
                    ],
                    "Sonuçlandırma Aşaması": [
                        "Sonuçların değerlendirilmesi",
                        "Final raporu yazımı",
                        "Sunum hazırlığı",
                        "Yaygınlaştırma faaliyetleri"
                    ]
                }
            },
            "medium": {  # 4-6 ay
                "structure": [
                    "Hazırlık Aşaması",
                    "Geliştirme Aşaması",
                    "Uygulama Aşaması",
                    "Değerlendirme Aşaması",
                    "Sonuçlandırma Aşaması"
                ],
                "tasks": {
                    "Hazırlık Aşaması": [
                        "Detaylı literatür taraması",
                        "Proje ekibinin oluşturulması",
                        "Metodoloji geliştirme",
                        "İş paketlerinin planlanması",
                        "Gerekli izinlerin alınması"
                    ],
                    "Geliştirme Aşaması": [
                        "Araştırma araçlarının geliştirilmesi",
                        "Pilot uygulama",
                        "Metodoloji revizyonu",
                        "Veri toplama protokollerinin oluşturulması"
                    ],
                    "Uygulama Aşaması": [
                        "Veri toplama",
                        "Veri analizi",
                        "Ara raporlama",
                        "Paydaş toplantıları"
                    ],
                    "Değerlendirme Aşaması": [
                        "Bulguların değerlendirilmesi",
                        "Karşılaştırmalı analizler",
                        "Uzman görüşlerinin alınması",
                        "Çıktıların gözden geçirilmesi"
                    ],
                    "Sonuçlandırma Aşaması": [
                        "Final raporu yazımı",
                        "Sonuçların paydaşlarla paylaşılması",
                        "Yaygınlaştırma faaliyetleri",
                        "İleri araştırmalar için öneriler"
                    ]
                }
            },
            "long": {  # 7+ ay
                "structure": [
                    "Planlama Aşaması",
                    "Hazırlık Aşaması",
                    "Geliştirme Aşaması",
                    "Uygulama Aşaması (1. Dönem)",
                    "Ara Değerlendirme",
                    "Uygulama Aşaması (2. Dönem)",
                    "Analiz Aşaması",
                    "Raporlama Aşaması",
                    "Yaygınlaştırma Aşaması"
                ],
                "tasks": {
                    "Planlama Aşaması": [
                        "Proje ekibinin oluşturulması",
                        "Detaylı iş planı hazırlama",
                        "Kaynak planlaması",
                        "Risk analizi"
                    ],
                    "Hazırlık Aşaması": [
                        "Kapsamlı literatür taraması",
                        "Metodoloji geliştirme",
                        "Gerekli izinlerin alınması",
                        "Veri yönetim planının oluşturulması"
                    ],
                    "Geliştirme Aşaması": [
                        "Araştırma araçlarının geliştirilmesi",
                        "Pilot uygulamalar",
                        "Metodoloji revizyonu",
                        "Veri toplama protokollerinin oluşturulması"
                    ],
                    "Uygulama Aşaması (1. Dönem)": [
                        "İlk veri toplama süreci",
                        "Ön analizler",
                        "Metodoloji revizyonu",
                        "Ara rapor hazırlığı"
                    ],
                    "Ara Değerlendirme": [
                        "İlk dönem verilerinin değerlendirilmesi",
                        "Metodoloji revizyonu",
                        "Paydaş geri bildirimleri",
                        "İkinci dönem planının güncellenmesi"
                    ],
                    "Uygulama Aşaması (2. Dönem)": [
                        "İkinci veri toplama süreci",
                        "Detaylı analizler",
                        "Ara bulgular raporu",
                        "Uzman görüşlerinin alınması"
                    ],
                    "Analiz Aşaması": [
                        "Tüm verilerin birleştirilmesi",
                        "Kapsamlı analiz",
                        "Bulguların yorumlanması",
                        "Çıktıların hazırlanması"
                    ],
                    "Raporlama Aşaması": [
                        "Final raporu yazımı",
                        "Bulguların gözden geçirilmesi",
                        "Rapor düzeltmeleri",
                        "Sonuçların dokümantasyonu"
                    ],
                    "Yaygınlaştırma Aşaması": [
                        "Proje çıktılarının paylaşılması",
                        "Konferans/seminer sunumları",
                        "Yayın hazırlıkları",
                        "İleri araştırmalar için öneriler"
                    ]
                }
            }
        }
        
        # Şablon dosyası varsa yükle, yoksa varsayılanları kullan
        if os.path.exists(templates_path):
            try:
                with open(templates_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Plan şablonları yüklenirken hata: {e}")
                return default_templates
        else:
            # Varsayılan şablonları kaydet
            with open(templates_path, 'w', encoding='utf-8') as f:
                json.dump(default_templates, f, ensure_ascii=False, indent=2)
            
            return default_templates
    
    def _update_response_templates(self, class_id, new_template):
        """Yanıt şablonlarını güncelle"""
        class_id = str(class_id)  # JSON anahtarları string olmalı
        
        if class_id not in self.response_templates:
            self.response_templates[class_id] = []
        
        # Aynı şablonu tekrar eklemeyi önle
        if new_template not in self.response_templates[class_id]:
            self.response_templates[class_id].append(new_template)
            
            # Şablonları kaydet
            templates_path = os.path.join(self.templates_dir, 'response_templates.json')
            with open(templates_path, 'w', encoding='utf-8') as f:
                json.dump(self.response_templates, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Yanıt şablonu güncellendi: Sınıf {class_id}")
    
    def _extract_fon_info(self, query):
        """Sorgudan fon bilgilerini çıkar"""
        fon_info = {
            'fon_kodu': '',
            'fon_turu': '',
            'ay_suresi': 0
        }
        
        # Fon kodu tespiti (örnek: 2247-C, 2205, vb.)
        kod_pattern = r'\b(\d{4})(?:-([A-Z]))?\b'
        kod_matches = re.findall(kod_pattern, query)
        if kod_matches:
            fon_info['fon_kodu'] = kod_matches[0][0]
            if kod_matches[0][1]:  # Alt program kodu varsa (örn: 2247-C'deki C)
                fon_info['fon_kodu'] += f"-{kod_matches[0][1]}"
        
        # Fon türü tespiti
        # Genişletilmiş fon türleri listesi
        fon_turleri = {
            'burs': ['burs', 'bursiyer', 'ödül', 'destek bursu'],
            'araştırma': ['araştırma', 'ar-ge', 'bilimsel araştırma', 'temel araştırma'],
            'proje': ['proje', 'proje desteği', 'araştırma projesi'],
            'destek': ['destek', 'destekleme', 'mali destek', 'finans desteği'],
            'akademik': ['akademik', 'bilimsel', 'üniversite', 'akademisyen'],
            'yüksek lisans': ['yüksek lisans', 'master', 'mastır', 'tezli'],
            'doktora': ['doktora', 'phd', 'doktora sonrası', 'postdoc'],
            'sanayi': ['sanayi', 'endüstri', 'endüstriyel', 'ticari', 'teknoloji'],
            'uluslararası': ['uluslararası', 'global', 'yurt dışı', 'ikili']
        }
        
        query_lower = query.lower()
        for tur, keywords in fon_turleri.items():
            for keyword in keywords:
                if keyword in query_lower:
                    fon_info['fon_turu'] = tur
                    break
            if fon_info['fon_turu']:
                break
        
        # Ay süresi tespiti - genişletilmiş
        ay_patterns = [
            r'(\d+)\s*(?:ay|aylık)',  # "6 ay", "6 aylık"
            r'(\d+)\s*(?:hafta|haftalık)',  # "24 hafta", "24 haftalık"
            r'(\d+)\s*(?:yıl|yıllık)'  # "1 yıl", "1 yıllık"
        ]
        
        for pattern in ay_patterns:
            matches = re.findall(pattern, query_lower)
            if matches:
                try:
                    value = int(matches[0])
                    # Hafta -> ay dönüşümü
                    if 'hafta' in pattern:
                        value = max(1, round(value / 4))  # Minimum 1 ay
                    # Yıl -> ay dönüşümü
                    elif 'yıl' in pattern:
                        value *= 12
                    
                    fon_info['ay_suresi'] = value
                    break
                except ValueError:
                    pass
        
        # Fon kodu belirli bir program için özelleştirilmiş süreleri kontrol et
        if fon_info['fon_kodu'] and not fon_info['ay_suresi']:
            # Önce veritabanından çekilen bilgilere bak
            kod = fon_info['fon_kodu']
            kod_esas = kod.split('-')[0]  # Alt program kodunu çıkar
            
            if kod in self.fon_bilgileri:
                fon_info['ay_suresi'] = self.fon_bilgileri[kod]['ay_suresi']
                if not fon_info['fon_turu'] and self.fon_bilgileri[kod]['tur']:
                    fon_info['fon_turu'] = self.fon_bilgileri[kod]['tur']
            elif kod_esas in self.fon_bilgileri:
                fon_info['ay_suresi'] = self.fon_bilgileri[kod_esas]['ay_suresi']
                if not fon_info['fon_turu'] and self.fon_bilgileri[kod_esas]['tur']:
                    fon_info['fon_turu'] = self.fon_bilgileri[kod_esas]['tur']
            # Varsayılan süreleri kullan
            else:
                fon_kod_sureler = {
                    '1001': 36,  # TÜBİTAK 1001 - Bilimsel Araştırma Projeleri
                    '1002': 12,  # TÜBİTAK 1002 - Hızlı Destek
                    '1003': 36,  # TÜBİTAK 1003 - Öncelikli Alanlar
                    '1005': 24,  # TÜBİTAK 1005 - Ulusal Yeni Fikirler
                    '3501': 36,  # TÜBİTAK 3501 - Kariyer
                    '2209': 12,  # TÜBİTAK 2209 - Üniversite Öğrencileri
                    '2232': 36,  # TÜBİTAK 2232 - Uluslararası Lider Araştırmacılar
                    '2247': 36   # TÜBİTAK 2247 - Ulusal Lider Araştırmacılar
                }
                if kod_esas in fon_kod_sureler:
                    fon_info['ay_suresi'] = fon_kod_sureler[kod_esas]
        
        return fon_info
    
    def _generate_response_from_template(self, template, fon_info):
        """Şablonu kullanarak yanıt oluştur"""
        # Varsayılan değerler
        placeholders = {
            'fon_kodu': fon_info.get('fon_kodu', ''),
            'fon_turu': fon_info.get('fon_turu', 'araştırma'),
            'ay_suresi': fon_info.get('ay_suresi', 0)
        }
        
        # Şablonu doldur
        response = template
        for key, value in placeholders.items():
            response = response.replace(f"{{{key}}}", str(value))
        
        return response
    
    def _create_detailed_plan(self, fon_info):
        """Detaylı proje planı oluştur"""
        ay_suresi = fon_info.get('ay_suresi', 0)
        
        if ay_suresi <= 0:
            ay_suresi = 6  # Varsayılan süre
        
        # Plan tipini belirle
        if ay_suresi <= 3:
            plan_type = "short"
        elif ay_suresi <= 6:
            plan_type = "medium"
        else:
            plan_type = "long"
        
        # İlgili şablonu al
        template = self.plan_templates.get(plan_type, self.plan_templates["medium"])
        
        # Aşamaları belirle
        phases = template["structure"]
        
        # Süreye göre aşamaları dağıt
        phase_durations = []
        remaining_months = ay_suresi
        
        for i in range(len(phases)):
            # Son aşama için kalan tüm ayları kullan
            if i == len(phases) - 1:
                phase_durations.append(remaining_months)
            else:
                # Her aşamaya orantılı süre ver
                duration = max(1, round(ay_suresi * (1 / len(phases))))
                duration = min(duration, remaining_months)
                phase_durations.append(duration)
                remaining_months -= duration
        
        # Planı oluştur
        plan_content = []
        current_month = 1
        
        # Başlık ve giriş
        fon_kodu = fon_info.get('fon_kodu', '')
        fon_turu = fon_info.get('fon_turu', 'araştırma')
        
        plan_title = f"TÜBİTAK {fon_kodu} {fon_turu.title()} Programı için {ay_suresi} Aylık Proje Planı"
        
        plan_intro = f"Bu plan, {ay_suresi} aylık süreyle yürütülecek"
        if fon_kodu:
            plan_intro += f" TÜBİTAK {fon_kodu}"
        if fon_turu:
            plan_intro += f" {fon_turu}"
        plan_intro += " projesi için hazırlanmıştır."
        
        plan_content.append(plan_title)
        plan_content.append("")
        plan_content.append(plan_intro)
        plan_content.append("")
        
        # Kapsamlı plan oluştur
        for i, phase in enumerate(phases):
            if phase_durations[i] <= 0:
                continue
                
            # Her aşama için görevleri belirle
            tasks = template["tasks"].get(phase, ["Görev tanımlanmadı"])
            
            # Aşama başlığı
            if phase_durations[i] == 1:
                plan_content.append(f"Ay {current_month}: {phase}")
            else:
                plan_content.append(f"Ay {current_month}-{current_month + phase_durations[i] - 1}: {phase}")
            
            # Görevleri ekle
            for task in tasks:
                plan_content.append(f"- {task}")
            
            plan_content.append("")
            current_month += phase_durations[i]
        
        # Ay bazlı planı da ekle
        plan_content.append("Aylık İş Planı:")
        plan_content.append("")
        
        current_month = 1
        for i, phase in enumerate(phases):
            if phase_durations[i] <= 0:
                continue
                
            for j in range(phase_durations[i]):
                tasks = template["tasks"].get(phase, ["Görev tanımlanmadı"])
                
                # Her ay için 2-3 görev seç
                month_tasks = []
                task_count = min(3, len(tasks))
                selected_tasks = random.sample(tasks, task_count)
                
                plan_content.append(f"Ay {current_month}: {phase}")
                for task in selected_tasks:
                    plan_content.append(f"- {task}")
                
                plan_content.append("")
                current_month += 1
        
        return "\n".join(plan_content)
    
    def _check_similar_plans_in_db(self, fon_kodu, ay_suresi, plan_text):
        """Veritabanında benzer planları kontrol et"""
        try:
            logger.info(f"Benzer planlar kontrol ediliyor: fon={fon_kodu}, süre={ay_suresi} ay")
            
            # Benzer fon ve süreye sahip planları sorgula
            query = """
            SELECT TOP 5
                ap.id,
                ap.plan_metni,
                f.kod,
                f.tur,
                ap.ay_suresi
            FROM 
                dbo.chat_aiplan ap
            JOIN 
                dbo.chat_fon f ON f.id = ap.fon_id
            WHERE 
                f.kod = ? AND
                ap.ay_suresi = ?
            ORDER BY
                ap.olusturma_tarihi DESC
            """
            
            params = (fon_kodu, ay_suresi)
            
            conn = self.connect_to_db()
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # Benzerlik kontrolü
            for row in rows:
                plan_id = row[0]
                db_plan_text = row[1]
                
                if db_plan_text and plan_text:
                    # Basit benzerlik kontrolü
                    from difflib import SequenceMatcher
                    similarity = SequenceMatcher(None, db_plan_text, plan_text).ratio()
                    
                    logger.info(f"Plan benzerlik kontrolü: ID={plan_id}, benzerlik={similarity:.2f}")
                    
                    if similarity > 0.7:  # %70'den fazla benzerlik varsa
                        return plan_id
            
            return None
        
        except Exception as e:
            logger.error(f"Benzer plan kontrolü hatası: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    

    def generate_response(self, query, fon_id=None, fon_data=None):
        """Kullanıcı sorgusuna yanıt oluştur: LSTM Seq2Seq modeli ile metin üretir."""
        logger.info(f"Sorgu ile metin üretiliyor: {query[:50]}...")
        try:
        # Model kaynaklarını yükle
            if self.model.encoder_model is None or self.model.decoder_model is None:
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
        
        # LSTM Seq2Seq modeli ile doğrudan metin üret
            generated_text = self.model.generate_text(enriched_query)
        
        # Geçen süreyi hesapla
            generation_time = time.time() - start_time
        
        # Üretilen metni TÜBİTAK formatına uygun hale getir
            formatted_text = self._format_generated_text(generated_text, fon_info)
        
            # LSTM imzası
            formatted_text += f"\n\n[TÜBİTAK LSTM Seq2Seq AI tarafından oluşturuldu - {generation_time:.2f} saniye]"

        # Meta veri
            response_meta = {
                'fon_info': fon_info,
                'plan_generated': True,
                'model_accuracy': 54.56,  # Eğitim sonucunda elde edilen doğruluk değeri
                'timestamp': datetime.now().isoformat(),
                'generation_time': generation_time,
                'generated_raw': generated_text  # Ham üretilen metni de saklayalım
            }
        
            return formatted_text, response_meta

        except Exception as e:
            error_msg = f"Metin üretme hatası: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return ("Üzgünüm, proje planı oluşturulurken bir hata oluştu.", None)
    
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
    
    def process_feedback(self, query, response, feedback_score, response_meta=None):
        """Kullanıcı geri bildirimini işle"""
        try:
            # Yanıt metedata'sından özellikler çıkar
            features = None
            if response_meta and 'fon_info' in response_meta:
                features = response_meta['fon_info']
            
            # Geri bildirimleri dosyaya kaydet
            feedback_data_path = os.path.join(self.feedback_dir, 'feedback_data.json')
            
            # Mevcut verileri yükle
            feedback_data = []
            if os.path.exists(feedback_data_path):
                try:
                    with open(feedback_data_path, 'r', encoding='utf-8') as f:
                        feedback_data = json.load(f)
                except:
                    pass
            
            # Yeni geri bildirimi ekle
            feedback_item = {
                'query': query,
                'response': response,
                'score': feedback_score,
                'features': features,
                'timestamp': datetime.now().isoformat(),
                'meta': response_meta
            }
            
            feedback_data.append(feedback_item)
            
            # Dosyaya kaydet
            with open(feedback_data_path, 'w', encoding='utf-8') as f:
                json.dump(feedback_data, f, ensure_ascii=False, indent=2)
            
            # Yüksek puanlı yanıtları şablonlara ekle
            if feedback_score >= 4 and response_meta and 'prediction' in response_meta:
                prediction = response_meta['prediction']
                class_id = prediction.get('class', 0)
                
                # Yanıtı daha kompakt hale getir
                compact_response = response
                
                # Uzun yanıtları özet haline getir
                if len(response) > 500:
                    sentences = sent_tokenize(response)
                    if len(sentences) > 5:
                        important_sentences = sentences[:2] + sentences[-3:]
                        compact_response = " ".join(important_sentences)
                
                # Şablonları güncelle
                self._update_response_templates(class_id, compact_response)
            
            logger.info(f"Geri bildirim işlendi: Skor {feedback_score}")
            return True
        
        except Exception as e:
            logger.error(f"Geri bildirim işlenirken hata: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def _auto_retrain_job(self):
        """Otomatik yeniden eğitim iş parçacığı"""
        while not self.should_stop:
            try:
                # Her 12 saatte bir kontrol et
                time.sleep(43200)  # 12 saat
                
                # Veritabanından en son verileri çek
                self._refresh_training_data()
                
                # Geri bildirim veri dosyasını kontrol et
                feedback_file = os.path.join(self.feedback_dir, 'feedback_data.json')
                
                if os.path.exists(feedback_file):
                    with open(feedback_file, 'r', encoding='utf-8') as f:
                        feedback_data = json.load(f)
                    
                    # Yeterince yeni geri bildirim varsa yeniden eğit
                    if len(feedback_data) >= 10:  # En az 10 geri bildirim
                        logger.info("Yeterli geri bildirim var, yeniden eğitim başlatılıyor...")
                        self.model.retrain_with_feedback(feedback_file)
                        
                        # Eğitim sonrası timestamp ekle (eğitimin tekrarını önlemek için)
                        retrain_log_path = os.path.join(self.memory_dir, 'last_retrain.log')
                        with open(retrain_log_path, 'w', encoding='utf-8') as f:
                            f.write(datetime.now().isoformat())
            
            except Exception as e:
                logger.error(f"Otomatik yeniden eğitim sırasında hata: {e}")
                logger.error(traceback.format_exc())
    
    def stop(self):


        """Servisi durdur"""
        self.should_stop = True
        logger.info("AgentAIService durduruluyor...")


if os.environ.get("POPULATE_MODE") != "1":
    # Sadece normal çalıştırmada aktif olsun:
    service = AgentAIService()