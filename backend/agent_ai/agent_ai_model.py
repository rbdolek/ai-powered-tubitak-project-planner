import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
import numpy as np
import os
import pickle
import re
import json
import time
import datetime
import random

class AgentAIModel:
    def __init__(self):
        self.model = None
        self.encoder_model = None
        self.decoder_model = None
        self.tokenizer_x = None
        self.tokenizer_y = None
        self.max_len_input = 100  # Varsayılan değer
        self.max_len_output = 300  # Varsayılan değer
    
    def load_resources(self):
        """Model ve tokenizer'ları yükle"""
        try:
            # Modelin tam dosya yolunu belirtin
            model_path = 'models/lstm_seq2seq_model.h5'
            
            # Encoder/Decoder modellerinin yolları
            encoder_path = 'models/encoder_model.h5'
            decoder_path = 'models/decoder_model.h5'
            
            # Tokenizer dosyalarının yolları
            tokenizer_x_path = 'models/tokenizer.pickle'
            tokenizer_y_path = 'models/output_tokenizer.pickle'
            
            # Dosya varlığını kontrol et
            print(f"Model var mı? {os.path.exists(model_path)}")
            print(f"Encoder var mı? {os.path.exists(encoder_path)}")
            print(f"Decoder var mı? {os.path.exists(decoder_path)}")
            print(f"Tokenizer X var mı? {os.path.exists(tokenizer_x_path)}")
            print(f"Tokenizer Y var mı? {os.path.exists(tokenizer_y_path)}")
            
            # Model yükleme
            print(f"Model yükleniyor: {model_path}")
            self.model = load_model(model_path)
            print("Model başarıyla yüklendi!")
            
            # Encoder/Decoder'ı yükle
            try:
                self.encoder_model = load_model(encoder_path)
                self.decoder_model = load_model(decoder_path)
                print("Encoder/Decoder modelleri de yüklendi!")
            except Exception as e:
                print(f"Encoder/Decoder yüklenemedi: {e}")
            
            # Tokenizer'ları yükle
            try:
                print(f"Tokenizer X yükleniyor: {tokenizer_x_path}")
                with open(tokenizer_x_path, 'rb') as handle:
                    self.tokenizer_x = pickle.load(handle)
                print("Tokenizer X başarıyla yüklendi!")
                
                print(f"Tokenizer Y yükleniyor: {tokenizer_y_path}")
                with open(tokenizer_y_path, 'rb') as handle:
                    self.tokenizer_y = pickle.load(handle)
                print("Tokenizer Y başarıyla yüklendi!")
                
                return True
                
            except Exception as e:
                print(f"Tokenizer yükleme hatası: {e}")
                return False
                
        except Exception as e:
            import traceback
            print(f"Model kaynakları yüklenirken hata: {e}")
            print(traceback.format_exc())
            return False
    
    def generate_text(self, input_text):
        """LSTM model ile metin üret"""
        start_time = time.time()
    
    # Eğer girdi komut ise (örn. "doc", "evet", "takvim" veya "Bu plan için takvim oluştur") işlem yapma
        input_text_lower = input_text.lower().strip()
        if len(input_text_lower.split()) <= 5 or input_text_lower.  startswith("bu plan için"):
            command_keywords = ["doc", "takvim", "plan", "oluştur", "indir", "göster", "evet", "hayır", "yes", "no"]
            if any(keyword in input_text_lower for keyword in command_keywords):
            # DOC isteği olup olmadığını kontrol et
                if input_text_lower == "evet" or input_text_lower == "yes" or "doc" in input_text_lower:
                    return {"command": "generate_doc", "message": "DOC hazırlanıyor, lütfen bekleyin..."}
            # Takvim isteği olup olmadığını kontrol et
                elif "takvim" in input_text_lower or "plan için" in input_text_lower:
                    return {"command": "generate_calendar", "message": "Takvim hazırlanıyor..."}
            # Diğer komutlar için
                else:
                    return {"command": "unknown", "message": "Komut algılandı. İşlem yapılmıyor."}
    
        try:
        # Kaynakları yükle (eğer henüz yüklenmemişse)
            if not hasattr(self, 'model') or self.model is None:
                if not self.load_resources():
                    return "Model yüklenemedi. Lütfen sistem yöneticisiyle iletişime geçin."
        
            print(f"Girdi metni: {input_text}")
        
        # Girdi metnini analiz et
            project_details = self._extract_project_details(input_text)
            print(f"Proje detayları: {project_details}")
        
        # Girdi metninden ana temaları belirle
            themes = self._identify_main_themes(input_text.lower())
            print(f"Belirlenen temalar: {themes}")
        
        # Tema odaklı plan oluşturma - daha yüksek öncelik
            if themes:
            # Burada daha önce eklediğimiz tema algılama ve plan oluşturma kodu...
                plan = self._create_custom_plan(project_details)
            else:
            # Tema belirlenemezse özel bir plan oluştur
                plan = self._create_custom_plan(project_details)
        
        # Planı formatla
            formatted_plan = self._format_plan(plan, project_details)
        
            elapsed_time = time.time() - start_time
            print(f"İşlem süresi: {elapsed_time:.2f} saniye")
        
            return formatted_plan
        
        except Exception as e:
            import traceback
            print(f"Metin üretme hatası: {e}")
            print(traceback.format_exc())
            return "Metin üretilirken bir hata oluştu."
    
    def predict_sequence(self, input_seq):
        """Encoder-Decoder modeli için tahmin yapma"""
        # Encoder'dan durum alın
        states_value = self.encoder_model.predict(np.expand_dims(input_seq, axis=0))
        
        # Durumlar tek bir değerse bir listeye dönüştürün
        if not isinstance(states_value, list):
            states_value = [states_value]
        
        # Hedef diziyi başlat
        target_seq = np.zeros((1, 1))
        # 'start' token'ını kullan
        target_seq[0, 0] = self.tokenizer_y.word_index.get('start', 1)
        
        # Çıktı dizisi
        output_tokens = []
        
        # Çeviri döngüsü
        stop_condition = False
        while not stop_condition:
            # Decoder'dan tahmin al
            if len(states_value) == 1:
                output_tokens_batch, h = self.decoder_model.predict([target_seq] + states_value)
                states_value = [h]
            else:
                output_tokens_batch, h, c = self.decoder_model.predict([target_seq] + states_value)
                states_value = [h, c]
            
            # Token indeksini al
            sampled_token_index = np.argmax(output_tokens_batch[0, 0, :])
            output_tokens.append(sampled_token_index)
            
            # 'end' token'ı geldiğinde veya maksimum uzunluğa ulaşıldığında dur
            if (sampled_token_index == self.tokenizer_y.word_index.get('end', 0) or 
                len(output_tokens) > self.max_len_output):
                stop_condition = True
            
            # Hedef diziyi güncelle
            target_seq = np.zeros((1, 1))
            target_seq[0, 0] = sampled_token_index
        
        return output_tokens
    
    def _identify_main_themes(self, text):
        """Metinden ana temaları belirle"""
        themes = []
        
        # Tema anahtar kelimeleri
        theme_keywords = {
            'sulama': ['sulama', 'irrigation', 'toprak nem', 'soil moisture', 'çiftçi', 'farmer', 'tarım', 'agriculture'],
            'tarım': ['tarım', 'agriculture', 'çiftçi', 'farmer', 'bitki', 'plant', 'mahsul', 'crop'],
            'engelli': ['engelli', 'disabled', 'özürlü', 'handicapped', 'erişilebilir', 'accessible'],
            'görme': ['görme engelli', 'kör', 'blind', 'görme bozukluğu', 'vision impaired'],
            'sağlık': ['sağlık', 'health', 'tıp', 'medical', 'hastane', 'hospital', 'hasta', 'patient'],
            'eğitim': ['eğitim', 'education', 'öğrenci', 'student', 'öğrenme', 'learning', 'okul', 'school'],
            'ulaşım': ['ulaşım', 'transportation', 'trafik', 'traffic', 'araç', 'vehicle', 'yol', 'road'],
            'enerji': ['enerji', 'energy', 'elektrik', 'electric', 'yenilenebilir', 'renewable'],
            'finans': ['finans', 'finance', 'banka', 'bank', 'ödeme', 'payment', 'para', 'money']
        }
        
        # Metin içinde anahtar kelimeleri ara
        for theme, keywords in theme_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    themes.append(theme)
                    break
        
        # Teknoloji temaları
        tech_themes = {
            'yapay_zeka': ['yapay zeka', 'ai', 'artificial intelligence', 'makine öğrenmesi', 'machine learning', 'ml', 'derin öğrenme', 'deep learning', 'tensorflow'],
            'iot': ['iot', 'internet of things', 'nesnelerin interneti', 'sensör', 'sensor', 'bağlantılı cihaz', 'connected device'],
            'web': ['web', 'site', 'internet', 'online', 'çevrimiçi', 'tarayıcı', 'browser'],
            'mobil': ['mobil', 'mobile', 'uygulama', 'app', 'application', 'android', 'ios', 'telefon', 'phone']
        }
        
        # Teknoloji temalarını ara
        for theme, keywords in tech_themes.items():
            for keyword in keywords:
                if keyword in text:
                    themes.append(theme)
                    break
        
        return list(set(themes))  # Tekrarları kaldır
    
    def _extract_project_details(self, text):
        """Metinden proje detaylarını çıkar"""
        details = {
            'fon_kodu': None,
            'fon_adi': 'TÜBİTAK Projesi',
            'proje_konusu': '',
            'proje_amaci': '',
            'hedef_kitle': '',
            'teknolojiler': [],
            'anahtar_kelimeler': []
        }
        
        # Metni küçük harfe çevir (arama için)
        text_lower = text.lower()
        
        # Ana projeyi belirle (metin içinde en uzun cümle genellikle proje konusudur)
        sentences = re.split(r'[.!?]', text)
        longest_sentence = max(sentences, key=len, default="").strip()
        if len(longest_sentence) > 30:  # Yeterince uzun bir cümle ise
            details['proje_konusu'] = longest_sentence
        
        # TÜBİTAK fon kodlarını ara
        fon_match = re.search(r'TÜBİTAK\s*(\d{4}[-A-Za-z]*)', text)
        if fon_match:
            fon_kodu = fon_match.group(1).strip()
            details['fon_kodu'] = fon_kodu
            
            # Fon adını belirle
            if fon_kodu.startswith('1001'):
                details['fon_adi'] = 'Bilimsel ve Teknolojik Araştırma Projelerini Destekleme Programı'
            elif fon_kodu.startswith('1002'):
                details['fon_adi'] = 'Hızlı Destek Programı'
            elif fon_kodu.startswith('1003'):
                details['fon_adi'] = 'Öncelikli Alanlar Ar-Ge Projeleri Destekleme Programı'
            elif fon_kodu.startswith('1004'):
                details['fon_adi'] = 'Mükemmeliyet Merkezi Destek Programı'
            elif fon_kodu.startswith('1005'):
                details['fon_adi'] = 'Ulusal Yeni Fikirler ve Ürünler Araştırma Destek Programı'
            elif fon_kodu.startswith('1007'):
                details['fon_adi'] = 'Kamu Kurumları Araştırma ve Geliştirme Projelerini Destekleme Programı'
            elif fon_kodu.startswith('1071'):
                details['fon_adi'] = 'Uluslararası Araştırma Fonlarından Yararlanma Kapasitesinin Artırılması'
            elif fon_kodu.startswith('1501'):
                details['fon_adi'] = 'Sanayi Ar-Ge Projeleri Destekleme Programı'
            elif fon_kodu.startswith('1505'):
                details['fon_adi'] = 'Üniversite-Sanayi İşbirliği Destek Programı'
            elif fon_kodu.startswith('1507'):
                details['fon_adi'] = 'KOBİ Ar-Ge Başlangıç Destek Programı'
            elif fon_kodu.startswith('1512'):
                details['fon_adi'] = 'Teknogirişim Sermayesi Desteği Programı'
            elif fon_kodu.startswith('2209'):
                if 'A' in fon_kodu:
                    details['fon_adi'] = 'Üniversite Öğrencileri Araştırma Projeleri Destekleme Programı'
                elif 'B' in fon_kodu:
                    details['fon_adi'] = 'Sanayiye Yönelik Lisans Araştırma Projeleri Desteği Programı'
            elif fon_kodu.startswith('2210'):
                details['fon_adi'] = 'Yurt İçi Yüksek Lisans Burs Programı'
            elif fon_kodu.startswith('2211'):
                details['fon_adi'] = 'Yurt İçi Doktora Burs Programı'
            elif fon_kodu.startswith('2214'):
                details['fon_adi'] = 'Yurt Dışı Doktora Sırası Araştırma Burs Programı'
            elif fon_kodu.startswith('2232'):
                details['fon_adi'] = 'Uluslararası Lider Araştırmacılar Programı'
            elif fon_kodu.startswith('2244'):
                details['fon_adi'] = 'Sanayi Doktora Programı'
            elif fon_kodu.startswith('2247'):
                details['fon_adi'] = 'Ulusal Lider Araştırmacılar Programı'
            elif fon_kodu.startswith('3501'):
                details['fon_adi'] = 'Kariyer Geliştirme Programı'
            elif fon_kodu.startswith('4004'):
                details['fon_adi'] = 'Doğa Eğitimi ve Bilim Okulları'
            elif fon_kodu.startswith('4005'):
                details['fon_adi'] = 'Yenilikçi Eğitim Uygulamaları'
            elif fon_kodu.startswith('4006'):
                details['fon_adi'] = 'Bilim Fuarları Destekleme Programı'
            elif fon_kodu.startswith('4007'):
                details['fon_adi'] = 'Bilim Şenlikleri Destekleme Programı'
        
        # Tırnak içindeki ifadeyi proje konusu olarak al
        konu_match = re.search(r'"([^"]+)"', text)
        if konu_match:
            details['proje_konusu'] = konu_match.group(1).strip()
        
        # Anahtar kelimeleri çıkar
        # Teknoloji kelimeleri
        tech_keywords = [
            'iot', 'yapay zeka', 'ai', 'makine öğrenmesi', 'machine learning', 
            'derin öğrenme', 'deep learning', 'tensorflow', 'sensör', 'sensor',
            'web', 'mobil', 'uygulama', 'app', 'veri', 'data', 'bulut', 'cloud',
            'sulama', 'irrigation', 'nem', 'moisture', 'tarım', 'agriculture'
        ]
        
        for keyword in tech_keywords:
            if keyword in text_lower:
                details['teknolojiler'].append(keyword)
                details['anahtar_kelimeler'].append(keyword)
        
        # Önemli terimleri anahtar kelime olarak ekle
        important_words = re.findall(r'\b[A-Za-z][A-Za-z]{4,}\b', text)
        for word in important_words:
            word_lower = word.lower()
            if (word_lower not in ['tubitak', 'tübitak', 'sistem', 'proje', 'plan'] and 
                word_lower not in details['anahtar_kelimeler']):
                details['anahtar_kelimeler'].append(word_lower)
        
        # Hedef kitleyi belirle
        target_patterns = [
            ('çocuklar', 'çocuklar'),
            ('öğrenciler', 'öğrenciler'),
            ('gençler', 'gençler'),
            ('yaşlılar', 'yaşlılar'),
            ('engelliler', 'engelliler'),
            ('görme engelli', 'görme engelliler'),
            ('hastalar', 'hastalar'),
            ('doktorlar', 'doktorlar'),
            ('öğretmenler', 'öğretmenler'),
            ('çiftçiler', 'çiftçiler'),
            ('işletmeler', 'işletmeler'),
            ('otizm', 'otizmli çocuklar'),
            ('otizimli', 'otizmli çocuklar')
        ]
        
        for target_name, target_key in target_patterns:
            if target_name in text_lower:
                details['hedef_kitle'] = target_key
                break
        
        # Proje amacını belirle
        purpose_patterns = [
            ('erken teşhis', 'erken teşhis'),
            ('teşhis', 'teşhis'),
            ('optimizasyon', 'optimizasyon'),
            ('iyileştirme', 'iyileştirme'),
            ('verimlilik', 'verimlilik artırma'),
            ('eğitim', 'eğitim'),
            ('öğretim', 'öğretim'),
            ('analiz', 'analiz'),
            ('raporlama', 'raporlama'),
            ('görselleştirme', 'görselleştirme'),
            ('izleme', 'izleme'),
            ('takip', 'takip'),
            ('otomasyon', 'otomasyon')
        ]
        
        for purpose_name, purpose_key in purpose_patterns:
            if purpose_name in text_lower:
                details['proje_amaci'] = purpose_key
                break
        
        return details
    
    def _create_custom_plan(self, project_details):
        """Proje detaylarına göre tamamen özelleştirilmiş bir plan oluştur"""
        
        # Proje detaylarını al
        proje_konusu = project_details.get('proje_konusu', '')
        hedef_kitle = project_details.get('hedef_kitle', '')
        proje_amaci = project_details.get('proje_amaci', '')
        teknolojiler = project_details.get('teknolojiler', [])
        anahtar_kelimeler = project_details.get('anahtar_kelimeler', [])
        
        # Anahtar kelimeleri string olarak birleştir
        anahtar_string = ' '.join(anahtar_kelimeler).lower()
        
        # Projenin ana temasını belirle
        if 'sulama' in anahtar_string or 'tarım' in anahtar_string or 'çiftçi' in anahtar_string:
            return self._create_irrigation_plan(project_details)
        elif 'engelli' in anahtar_string or 'görme engelli' in anahtar_string or 'körler' in anahtar_string:
            return self._create_accessibility_plan(project_details)
        elif 'sağlık' in anahtar_string or 'hasta' in anahtar_string or 'tıp' in anahtar_string or 'teşhis' in anahtar_string:
            return self._create_healthcare_plan(project_details)
        elif 'eğitim' in anahtar_string or 'öğrenci' in anahtar_string or 'öğrenme' in anahtar_string:
            return self._create_education_plan(project_details)
        elif 'enerji' in anahtar_string or 'elektrik' in anahtar_string or 'yenilenebilir' in anahtar_string:
            return self._create_energy_plan(project_details)
        elif 'ulaşım' in anahtar_string or 'trafik' in anahtar_string or 'rota' in anahtar_string:
            return self._create_transportation_plan(project_details)
        elif 'finans' in anahtar_string or 'banka' in anahtar_string or 'ödeme' in anahtar_string:
            return self._create_finance_plan(project_details)
        else:
            # Genel teknoloji odaklı plan
            if 'yapay zeka' in anahtar_string or 'ai' in anahtar_string or 'makine öğrenmesi' in anahtar_string:
                return self._create_ai_plan(project_details)
            elif 'web' in anahtar_string or 'site' in anahtar_string:
                return self._create_web_plan(project_details)
            elif 'mobil' in anahtar_string or 'uygulama' in anahtar_string or 'app' in anahtar_string:
                return self._create_mobile_plan(project_details)
            else:
                return self._create_general_tech_plan(project_details)

    def _create_irrigation_plan(self, project_details):
        """Akıllı sulama sistemleri için özel plan"""
        proje_konusu = project_details.get('proje_konusu', 'Akıllı Sulama Sistemi')
        
        plan = [
            {
                'ay': 1,
                'baslik': "Akıllı Sulama Sistemleri Literatür Taraması",
                'gorevler': [
                    "Mevcut akıllı sulama teknolojilerinin araştırılması ve incelenmesi",
                    "Toprak nemi sensörleri ve hava durumu veri entegrasyonu üzerine literatür taraması",
                    "Tarımsal IoT sistemleri üzerine en son araştırmaların derlenmesi"
                ]
            },
            {
                'ay': 2,
                'baslik': "Çiftçi İhtiyaçlarının Analizi",
                'gorevler': [
                    "Çiftçilerle görüşmeler yapılarak ihtiyaçların belirlenmesi",
                    "Farklı bitki türleri için sulama gereksinimlerinin analizi",
                    "Bölgesel iklim verilerinin toplanması ve analizi"
                ]
            },
            {
                'ay': 3,
                'baslik': "Sensör Ağı ve Donanım Tasarımı",
                'gorevler': [
                    "Toprak nemi sensörleri ve hava durumu sensörlerinin seçimi",
                    "Düşük güç tüketimli kablosuz iletişim altyapısının tasarımı",
                    "Sulama kontrol ünitelerinin tasarlanması"
                ]
            },
            {
                'ay': 4,
                'baslik': "IoT Platformu Geliştirme",
                'gorevler': [
                    "Sensör veri toplama ve işleme sisteminin geliştirilmesi",
                    "Bulut tabanlı veri depolama ve analiz altyapısının kurulması",
                    "Sensör kalibrasyonu ve veri doğrulama sistemlerinin geliştirilmesi"
                ]
            },
            {
                'ay': 5,
                'baslik': "Sulama Algoritmaları Geliştirme",
                'gorevler': [
                    "Bitki türlerine göre optimize sulama algoritmalarının geliştirilmesi",
                    "Hava tahmin verilerini entegre eden akıllı sulama planlaması",
                    "Su tasarrufu optimizasyon algoritmalarının geliştirilmesi"
                ]
            },
            {
                'ay': 6,
                'baslik': "Mobil Uygulama Geliştirme",
                'gorevler': [
                    "Çiftçiler için kullanıcı dostu mobil arayüzün tasarlanması",
                    "Gerçek zamanlı sensör verilerini görüntüleme özelliğinin geliştirilmesi",
                    "Manuel override ve uzaktan kontrol sistemlerinin implementasyonu"
                ]
            },
            {
                'ay': 7,
                'baslik': "Prototip Entegrasyonu ve Saha Testi",
                'gorevler': [
                    "Sensör ağı, kontrol üniteleri ve yazılım platformunun entegrasyonu",
                    "Kontrollü ortamda sulama sistemi testlerinin yapılması",
                    "Prototip performansının değerlendirilmesi ve iyileştirmelerin belirlenmesi"
                ]
            },
            {
                'ay': 8,
                'baslik': "Enerji Yönetimi Optimizasyonu",
                'gorevler': [
                    "Güneş enerjisi entegrasyonunun tasarlanması",
                    "Batarya ve güç yönetimi sistemlerinin geliştirilmesi",
                    "Düşük güç modları ve enerji tasarrufu stratejilerinin implementasyonu"
                ]
            },
            {
                'ay': 9,
                'baslik': "Gerçek Arazi Uygulaması",
                'gorevler': [
                    "Pilot çiftliklerde sistemin kurulumu ve yapılandırılması",
                    "Farklı bitki türleri için sistem kalibrasyonu",
                    "Gerçek koşullarda uzun süreli performans testleri"
                ]
            },
            {
                'ay': 10,
                'baslik': "Veri Analizi ve Sistem İyileştirmeleri",
                'gorevler': [
                    "Saha testlerinden toplanan verilerin kapsamlı analizi",
                    "Sulama algoritmalarının gerçek dünya verilerine göre iyileştirilmesi",
                    "Sistem güvenilirliği ve dayanıklılığının artırılması"
                ]
            },
            {
                'ay': 11,
                'baslik': "Ölçeklendirme ve Ekonomik Analiz",
                'gorevler': [
                    "Büyük ölçekli uygulamalar için sistem ölçeklendirme stratejilerinin geliştirilmesi",
                    "Maliyet-fayda analizi ve yatırım geri dönüş hesaplamalarının yapılması",
                    "Pazara giriş stratejisinin belirlenmesi"
                ]
            },
            {
                'ay': 12,
                'baslik': "Sonuçların Değerlendirilmesi ve Raporlama",
                'gorevler': [
                    "Su tasarrufu ve verim artışı verilerinin analizi ve raporlanması",
                    "Proje dokümantasyonunun tamamlanması",
                    "Sonuçların akademik yayın haline getirilmesi ve çiftçi bilgilendirme materyallerinin hazırlanması"
                ]
            }
        ]
        
        return plan

    def _create_accessibility_plan(self, project_details):
        """Görme engelliler için yardımcı teknolojiler planı"""
        proje_konusu = project_details.get('proje_konusu', 'Görme Engelliler İçin Yardımcı Teknoloji')
        
        plan = [
            {
                'ay': 1,
                'baslik': "Görme Engelliler İçin Yardımcı Teknolojiler Araştırması",
                'gorevler': [
                    "Mevcut görme engelli yardımcı teknolojilerinin incelenmesi",
                    "Görme engelli bireylerin karşılaştığı zorlukların analizi",
                    "Kullanıcı deneyimi ve erişilebilirlik standartlarının araştırılması"
                ]
            },
            {
                'ay': 2,
                'baslik': "Görme Engelli Kullanıcı İhtiyaçlarının Belirlenmesi",
                'gorevler': [
                    "Görme engelli bireylerle görüşmeler ve odak grup çalışmaları",
                    "Günlük hayatta karşılaşılan zorlukların ve ihtiyaçların belirlenmesi",
                    "Kullanıcı geribildirimlerine dayalı tasarım kriterleri oluşturulması"
                ]
            },
            {
                'ay': 3,
                'baslik': "Sensör ve Donanım Tasarımı",
                'gorevler': [
                    "Çevre algılama sensörlerinin (ultrasonik, kızılötesi, kamera) seçimi ve tasarımı",
                    "Giyilebilir veya taşınabilir cihaz formunun belirlenmesi",
                    "Haptik (dokunsal) geri bildirim sistemlerinin tasarımı"
                ]
            },
            {
                'ay': 4,
                'baslik': "Gerçek Zamanlı Nesne Tanıma Sistemi Geliştirme",
                'gorevler': [
                    "Görüntü işleme ve nesne tanıma algoritmalarının geliştirilmesi",
                    "Düşük gecikme süreli gerçek zamanlı işleme sistemlerinin tasarımı",
                    "Yapay zeka modellerinin eğitimi için veri seti oluşturulması"
                ]
            },
            {
                'ay': 5,
                'baslik': "Yapay Zeka ve Derin Öğrenme Modellerinin Eğitimi",
                'gorevler': [
                    "Nesne tanıma için derin öğrenme modellerinin eğitilmesi",
                    "Metin tanıma (OCR) sistemlerinin geliştirilmesi",
                    "Yüz tanıma ve ifade algılama algoritmalarının implementasyonu"
                ]
            },
            {
                'ay': 6,
                'baslik': "Sesli Geri Bildirim Sisteminin Geliştirilmesi",
                'gorevler': [
                    "Doğal dil işleme ve metin-konuşma dönüştürme sistemlerinin tasarımı",
                    "Akustik geri bildirim için kullanıcı arayüzü tasarımı",
                    "Çevre sesleriyle çakışmayı önleyen adaptif ses sistemleri"
                ]
            },
            {
                'ay': 7,
                'baslik': "Navigasyon ve Yönlendirme Sisteminin Geliştirilmesi",
                'gorevler': [
                    "İç mekan navigasyon sistemlerinin tasarımı ve geliştirilmesi",
                    "GPS ve diğer konum teknolojilerinin entegrasyonu",
                    "Engel tespit ve rota optimizasyon algoritmalarının geliştirilmesi"
                ]
            },
            {
                'ay': 8,
                'baslik': "Prototip Entegrasyonu",
                'gorevler': [
                    "Donanım ve yazılım bileşenlerinin entegrasyonu",
                    "Batarya ömrü optimizasyonu ve güç yönetimi",
                    "Sistem stabilitesi ve güvenilirliğinin test edilmesi"
                ]
            },
            {
                'ay': 9,
                'baslik': "Görme Engelli Katılımcılarla Kullanıcı Testleri",
                'gorevler': [
                    "Kontrollü ortamda kullanıcı testlerinin yapılması",
                    "Kullanılabilirlik ve erişilebilirlik değerlendirmelerinin yapılması",
                    "Kullanıcı geri bildirimlerinin toplanması ve analizi"
                ]
            },
            {
                'ay': 10,
                'baslik': "Sistem İyileştirmeleri ve Optimizasyon",
                'gorevler': [
                    "Kullanıcı testlerinden elde edilen geri bildirimlere göre iyileştirmeler",
                    "Algoritma performansının ve doğruluğunun artırılması",
                    "Batarya ömrü ve sistem performansının optimize edilmesi"
                ]
            },
            {
                'ay': 11,
                'baslik': "Gerçek Ortam Testleri",
                'gorevler': [
                    "Farklı çevre koşullarında (iç/dış mekan, gündüz/gece) uzun süreli testler",
                    "Farklı kullanıcı profilleriyle geniş kapsamlı kullanım testleri",
                    "Sistem güvenilirliği ve dayanıklılığının doğrulanması"
                ]
            },
            {
                'ay': 12,
                'baslik': "Dokümantasyon ve Yaygınlaştırma",
                'gorevler': [
                    "Kullanıcı kılavuzları ve eğitim materyallerinin hazırlanması",
                    "Görme engelli dernekleri ve kurumlarla işbirliği planlarının oluşturulması",
                    "Ürünün erişilebilirliğini ve yaygınlaşmasını sağlayacak stratejilerin geliştirilmesi"
                ]
            }
        ]
        
        return plan

    def _create_healthcare_plan(self, project_details):
        """Sağlık alanında teknoloji projesi planı"""
        proje_konusu = project_details.get('proje_konusu', 'Sağlık Teknolojisi Projesi')
        
        plan = [
            {
                'ay': 1,
                'baslik': "Sağlık Teknolojileri Literatür Taraması",
                'gorevler': [
                    "Mevcut sağlık teknolojileri ve çözümlerinin kapsamlı incelenmesi",
                    "Klinik ihtiyaçlar ve zorluklara ilişkin literatür taraması",
                    "Sağlık verileri yönetimi ve düzenleyici gereksinimlerin araştırılması"
                ]
            },
            {
                'ay': 2,
                'baslik': "Klinik İhtiyaçların ve Gereksinimlerin Belirlenmesi",
                'gorevler': [
                    "Sağlık uzmanları ve klinik personelle görüşmeler",
                    "Hasta ihtiyaçları ve deneyimlerinin analizi",
                    "Klinik iş akışlarının ve entegrasyon gereksinimlerinin belirlenmesi"
                ]
            },
            {
                'ay': 3,
                'baslik': "Sistem Mimarisi ve Veri Güvenliği Tasarımı",
                'gorevler': [
                    "Sağlık sistemi mimarisinin tasarlanması",
                    "Veri güvenliği ve gizlilik protokollerinin belirlenmesi",
                    "Mevcut sağlık bilgi sistemleri ile entegrasyon planının oluşturulması"
                ]
            },
            {
                'ay': 4,
                'baslik': "Prototip Geliştirme ve Veri Modelleme",
                'gorevler': [
                    "İlk sistem prototipinin geliştirilmesi",
                    "Sağlık verilerinin modellenmesi ve veri tabanı tasarımı",
                    "Klinik karar destek algoritmalarının ilk versiyonlarının geliştirilmesi"
                ]
            },
            {
                'ay': 5,
                'baslik': "Klinik Karar Destek Sistemi Geliştirme",
                'gorevler': [
                    "Kanıta dayalı klinik algoritmaların implementasyonu",
                    "Yapay zeka ve makine öğrenimi modellerinin entegrasyonu",
                    "Tanı ve tedavi önerilerinin doğruluk testleri"
                ]
            },
            {
                'ay': 6,
                'baslik': "Kullanıcı Arayüzü Geliştirme",
                'gorevler': [
                    "Sağlık profesyonelleri için klinik arayüz tasarımı",
                    "Hasta arayüzü ve deneyiminin geliştirilmesi",
                    "Erişilebilirlik standartlarına uygunluğun sağlanması"
                ]
            },
            {
                'ay': 7,
                'baslik': "Sistem Entegrasyonu ve Standartlara Uyumluluk",
                'gorevler': [
                    "HL7, FHIR gibi sağlık veri standartlarına entegrasyon",
                    "Mevcut hastane bilgi sistemleri ile entegrasyon testleri",
                    "Elektronik sağlık kayıtları sistemi ile veri alışverişinin sağlanması"
                ]
            },
            {
                'ay': 8,
                'baslik': "Klinik Validasyon ve Doğrulama",
                'gorevler': [
                    "Kontrollü klinik ortamda sistem doğrulama testleri",
                    "Algoritma performansının klinik veri setleriyle değerlendirilmesi",
                    "Sistem güvenilirliği ve doğruluğunun validasyonu"
                ]
            },
            {
                'ay': 9,
                'baslik': "Düzenleyici Gereksinimlerin Karşılanması",
                'gorevler': [
                    "Tıbbi cihaz düzenlemeleri ve standartlarına uygunluk değerlendirmesi",
                    "Risk analizi ve yönetimi çalışmalarının tamamlanması",
                    "Gerekli belgelendirme ve sertifikasyon süreçlerinin başlatılması"
                ]
            },
            {
                'ay': 10,
                'baslik': "Klinik Pilot Uygulama",
                'gorevler': [
                    "Seçilen klinik ortamlarda pilot uygulamanın başlatılması",
                    "Gerçek hasta verileriyle sistemin test edilmesi",
                    "Klinik iş akışına entegrasyonun değerlendirilmesi"
                ]
            },
            {
                'ay': 11,
                'baslik': "Sistem İyileştirmeleri ve Genişletme",
                'gorevler': [
                    "Pilot uygulama sonuçlarına göre sistem iyileştirmeleri",
                    "Ek özellikler ve fonksiyonların geliştirilmesi",
                    "Ölçeklenebilirlik ve performans optimizasyonu"
                ]
            },
            {
                'ay': 12,
                'baslik': "Sonuç Değerlendirmesi ve Yaygınlaştırma",
                'gorevler': [
                    "Klinik etki ve sonuçların değerlendirilmesi",
                    "Ekonomik fayda ve maliyet-etkinlik analizinin tamamlanması",
                    "Yaygınlaştırma stratejisi ve uygulama planının oluşturulması"
                ]
            }
        ]
        
        return plan

    def _create_education_plan(self, project_details):
        """Eğitim teknolojisi projesi planı"""
        proje_konusu = project_details.get('proje_konusu', 'Eğitim Teknolojisi Projesi')
        
        plan = [
            {
                'ay': 1,
                'baslik': "Eğitim Teknolojileri Araştırması",
                'gorevler': [
                    "Mevcut eğitim teknolojileri ve öğrenme platformlarının incelenmesi",
                    "Pedagojik yaklaşımlar ve öğrenme teorilerinin araştırılması",
                    "Hedef yaş grubu ve öğrenme ihtiyaçlarının analizi"
                ]
            },
            {
                'ay': 2,
                'baslik': "Eğitimci ve Öğrenci İhtiyaçlarının Belirlenmesi",
                'gorevler': [
                    "Öğretmenler, eğitimciler ve öğrencilerle görüşmeler",
                    "Mevcut eğitim süreçlerindeki zorlukların ve ihtiyaçların belirlenmesi",
                    "Öğrenme hedefleri ve çıktılarının tanımlanması"
                ]
            },
            {
                'ay': 3,
                'baslik': "Öğrenme İçeriği ve Müfredat Tasarımı",
                'gorevler': [
                    "Müfredat yapısı ve öğrenme modüllerinin tasarlanması",
                    "İçerik hiyerarşisi ve öğrenme yollarının belirlenmesi",
                    "Öğrenme kazanımları ve değerlendirme kriterlerinin oluşturulması"
                ]
            },
            {
                'ay': 4,
                'baslik': "Etkileşimli Öğrenme Deneyimi Tasarımı",
                'gorevler': [
                    "Kullanıcı deneyimi ve arayüz tasarımının geliştirilmesi",
                    "Etkileşimli öğrenme aktiviteleri ve oyunlaştırma elementlerinin tasarlanması",
                    "Farklı öğrenme stillerine uygun içerik formatlarının belirlenmesi"
                ]
            },
            {
                'ay': 5,
                'baslik': "Adaptif Öğrenme Sistemi Geliştirme",
                'gorevler': [
                    "Öğrenci performansına göre adapte olan öğrenme algoritmasının geliştirilmesi",
                    "Kişiselleştirilmiş öğrenme yolları ve içerik önerilerinin tasarlanması",
                    "Öğrenci ilerleme ve performans analiz sisteminin oluşturulması"
                ]
            },
            {
                'ay': 6,
                'baslik': "İçerik Geliştirme ve Multimedya Üretimi",
                'gorevler': [
                    "Eğitim içeriklerinin ve öğrenme materyallerinin oluşturulması",
                    "Video, animasyon ve etkileşimli simülasyonların geliştirilmesi",
                    "Ses, metin ve görsel içeriklerin üretilmesi ve entegrasyonu"
                ]
            },
            {
                'ay': 7,
                'baslik': "Değerlendirme ve Geri Bildirim Sistemleri",
                'gorevler': [
                    "Formatif ve summatif değerlendirme araçlarının geliştirilmesi",
                    "Anlık geri bildirim mekanizmalarının oluşturulması",
                    "Öğrenme analitiği ve ilerleme raporlama sisteminin tasarımı"
                ]
            },
            {
                'ay': 8,
                'baslik': "Öğretmen Kontrol Paneli ve Yönetim Sistemi",
                'gorevler': [
                    "Öğretmen kontrol paneli ve sınıf yönetim araçlarının geliştirilmesi",
                    "Öğrenci performans analizi ve raporlama özelliklerinin oluşturulması",
                    "İçerik yönetimi ve müfredat özelleştirme araçlarının geliştirilmesi"
                ]
            },
            {
                'ay': 9,
                'baslik': "Pilot Uygulama ve Kullanıcı Testleri",
                'gorevler': [
                    "Seçili okul veya kurumlarda pilot uygulamanın başlatılması",
                    "Öğretmen ve öğrenci kullanıcı deneyimi testleri",
                    "Kullanılabilirlik ve öğrenme etkinliğinin değerlendirilmesi"
                ]
            },
            {
                'ay': 10,
                'baslik': "Öğrenme Verimliliği ve Etki Analizi",
                'gorevler': [
                    "Öğrenme çıktıları ve kazanımların ölçülmesi",
                    "Sistem kullanımının öğrenme performansına etkisinin analizi",
                    "Öğretmen ve öğrenci geri bildirimlerine göre iyileştirmelerin belirlenmesi"
                ]
            },
            {
                'ay': 11,
                'baslik': "Sistem İyileştirmeleri ve Genişletme",
                'gorevler': [
                    "Pilot uygulama sonuçlarına göre içerik ve sistem iyileştirmeleri",
                    "Ek özellikler ve işlevselliğin geliştirilmesi",
                    "Ölçeklenebilirlik ve yeni müfredat alanlarına genişleme planlaması"
                ]
            },
            {
                'ay': 12,
                'baslik': "Dokümantasyon ve Yaygınlaştırma",
                'gorevler': [
                    "Kullanıcı kılavuzları ve eğitim materyallerinin hazırlanması",
                    "Öğretmen mesleki gelişim programının oluşturulması",
                    "Yaygınlaştırma stratejisi ve uygulama planının geliştirilmesi"
                ]
            }
        ]
        
        return plan

    def _create_energy_plan(self, project_details):
        """Enerji teknolojisi projesi planı"""
        proje_konusu = project_details.get('proje_konusu', 'Enerji Teknolojisi Projesi')
        
        plan = [
            {
                'ay': 1,
                'baslik': "Enerji Teknolojileri Araştırması",
                'gorevler': [
                    "Mevcut enerji üretim, dağıtım ve tüketim teknolojilerinin incelenmesi",
                    "Yenilenebilir enerji çözümleri ve sürdürülebilirlik yaklaşımlarının araştırılması",
                    "Enerji verimliliği stratejileri ve standartlarının derlenmesi"
                ]
            },
            {
                'ay': 2,
                'baslik': "Enerji İhtiyaç Analizi ve Sistem Gereksinimleri",
                'gorevler': [
                    "Hedef uygulama alanındaki enerji ihtiyaçlarının analizi",
                    "Enerji üretim/tüketim profillerinin çıkarılması",
                    "Teknik ve ekonomik sistem gereksinimlerinin belirlenmesi"
                ]
            },
            {
                'ay': 3,
                'baslik': "Enerji Sistem Tasarımı ve Modelleme",
                'gorevler': [
                    "Enerji sisteminin kavramsal tasarımının oluşturulması",
                    "Sistem bileşenleri ve mimarisinin detaylandırılması",
                    "Enerji akışı ve verimlilik modellemesinin yapılması"
                ]
            },
            {
                'ay': 4,
                'baslik': "Donanım Seçimi ve Prototip Tasarımı",
                'gorevler': [
                    "Enerji üretim/dönüşüm bileşenlerinin seçimi ve tedariki",
                    "Kontrol ve izleme sistemlerinin tasarımı",
                    "Prototip sistem şemalarının ve bağlantı diyagramlarının oluşturulması"
                ]
            },
            {
                'ay': 5,
                'baslik': "Enerji Yönetim Algoritmaları Geliştirme",
                'gorevler': [
                    "Enerji optimizasyon algoritmalarının geliştirilmesi",
                    "Talep tahmini ve yük dengeleme sistemlerinin tasarımı",
                    "Enerji depolama stratejilerinin ve kontrol algoritmalarının oluşturulması"
                ]
            },
            {
                'ay': 6,
                'baslik': "Prototip Sistem Entegrasyonu",
                'gorevler': [
                    "Donanım bileşenlerinin montajı ve entegrasyonu",
                    "Kontrol yazılımı ve izleme sistemlerinin implementasyonu",
                    "İlk prototip sistemin kurulumu ve fonksiyonel testleri"
                ]
            },
            {
                'ay': 7,
                'baslik': "Veri Toplama ve İzleme Sistemi",
                'gorevler': [
                    "Sensör ağı ve veri toplama altyapısının kurulması",
                    "Gerçek zamanlı izleme ve raporlama sisteminin geliştirilmesi",
                    "Veri analizi ve görselleştirme araçlarının oluşturulması"
                ]
            },
            {
                'ay': 8,
                'baslik': "Sistem Testleri ve Performans Ölçümü",
                'gorevler': [
                    "Farklı çalışma koşullarında sistemin test edilmesi",
                    "Enerji üretimi, verimliliği ve performans ölçümlerinin yapılması",
                    "Güvenilirlik ve dayanıklılık testlerinin gerçekleştirilmesi"
                ]
            },
            {
                'ay': 9,
                'baslik': "Şebeke Entegrasyonu ve Uyumluluk",
                'gorevler': [
                    "Mevcut enerji altyapısı ile entegrasyon testleri",
                    "Şebeke standartları ve düzenlemelerine uygunluk değerlendirmesi",
                    "Elektriksel güvenlik ve koruma sistemlerinin doğrulanması"
                ]
            },
            {
                'ay': 10,
                'baslik': "Saha Uygulaması ve Pilot Çalışma",
                'gorevler': [
                    "Gerçek kullanım ortamında sistemin kurulumu",
                    "Pilot uygulama verilerinin toplanması ve analizi",
                    "Sistem performansının ve kullanıcı deneyiminin değerlendirilmesi"
                ]
            },
            {
                'ay': 11,
                'baslik': "Ekonomik Analiz ve İş Modeli Geliştirme",
                'gorevler': [
                    "Maliyet-fayda analizi ve yatırım geri dönüş hesaplamaları",
                    "Ölçeklendirme senaryoları ve ekonomik fizibilite çalışması",
                    "Sürdürülebilir iş modeli ve pazara giriş stratejisinin geliştirilmesi"
                ]
            },
            {
                'ay': 12,
                'baslik': "Sonuçların Değerlendirilmesi ve Yaygınlaştırma",
                'gorevler': [
                    "Proje sonuçlarının ve enerji verimliliği etkisinin değerlendirilmesi",
                    "Teknik dokümantasyon ve kullanım kılavuzlarının hazırlanması",
                    "Yaygınlaştırma planı ve uygulama stratejisinin oluşturulması"
                ]
            }
        ]
        
        return plan

    def _create_transportation_plan(self, project_details):
        """Ulaşım teknolojisi projesi planı"""
        proje_konusu = project_details.get('proje_konusu', 'Ulaşım Teknolojisi Projesi')
        
        plan = [
            {
                'ay': 1,
                'baslik': "Ulaşım Teknolojileri Araştırması",
                'gorevler': [
                    "Mevcut ulaşım sistemleri ve teknolojilerinin incelenmesi",
                    "Akıllı ulaşım sistemleri ve trafik yönetimi çözümlerinin araştırılması",
                    "Kullanıcı ihtiyaçları ve ulaşım zorluklarının belirlenmesi"
                ]
            },
            {
                'ay': 2,
                'baslik': "Trafik Veri Analizi ve Gereksinim Belirleme",
                'gorevler': [
                    "Trafik veri kaynaklarının belirlenmesi ve veri toplama metodolojisi",
                    "Mevcut trafik akışı ve yoğunluk paternlerinin analizi",
                    "Sistem gereksinimleri ve performans kriterlerinin belirlenmesi"
                ]
            },
            {
                'ay': 3,
                'baslik': "Sistem Mimarisi ve Veri Altyapısı Tasarımı",
                'gorevler': [
                    "Akıllı ulaşım sistemi mimarisinin tasarlanması",
                    "Veri toplama ve işleme altyapısının planlanması",
                    "Haberleşme protokolleri ve veri formatlarının belirlenmesi"
                ]
            },
            {
                'ay': 4,
                'baslik': "Sensör Ağı ve Veri Toplama Sistemleri",
                'gorevler': [
                    "Trafik sensörleri ve algılayıcıların seçimi/tasarımı",
                    "Gerçek zamanlı veri toplama sisteminin geliştirilmesi",
                    "Sensör kalibrasyonu ve veri doğrulama prosedürlerinin oluşturulması"
                ]
            },
            {
                'ay': 5,
                'baslik': "Trafik Analiz ve Tahmin Algoritmaları",
                'gorevler': [
                    "Trafik akış analizi algoritmaların geliştirilmesi",
                    "Trafik tahmin modellerinin oluşturulması ve eğitilmesi",
                    "Rota optimizasyonu ve trafik yönlendirme algoritmalarının geliştirilmesi"
                ]
            },
            {
                'ay': 6,
                'baslik': "Kullanıcı Arayüzü ve Mobil Uygulama Geliştirme",
                'gorevler': [
                    "Sürücüler için mobil uygulama tasarımı ve geliştirilmesi",
                    "Trafik yöneticileri için kontrol paneli arayüzünün oluşturulması",
                    "Kullanıcı bildirimleri ve etkileşim sistemlerinin geliştirilmesi"
                ]
            },
            {
                'ay': 7,
                'baslik': "Trafik Kontrol ve Yönetim Sistemleri",
                'gorevler': [
                    "Trafik ışıkları ve sinyalizasyon kontrol sistemlerinin geliştirilmesi",
                    "Dinamik trafik yönetimi ve adaptif kontrol mekanizmaları",
                    "Acil durum yönetimi ve öncelikli geçiş sistemlerinin tasarımı"
                ]
            },
            {
                'ay': 8,
                'baslik': "Sistem Entegrasyonu ve Test Ortamı",
                'gorevler': [
                    "Tüm alt sistemlerin entegrasyonu ve test ortamının kurulması",
                    "Simülasyon senaryolarının oluşturulması ve test edilmesi",
                    "Sistem performansının ve güvenilirliğinin değerlendirilmesi"
                ]
            },
            {
                'ay': 9,
                'baslik': "Pilot Uygulama ve Saha Testleri",
                'gorevler': [
                    "Seçili bir bölgede pilot uygulamanın başlatılması",
                    "Gerçek trafik koşullarında sistemin test edilmesi",
                    "Kullanıcı deneyimi ve sistem etkinliğinin değerlendirilmesi"
                ]
            },
            {
                'ay': 10,
                'baslik': "Trafik Akış Optimizasyonu ve İyileştirmeler",
                'gorevler': [
                    "Pilot uygulama sonuçlarına göre algoritmaların iyileştirilmesi",
                    "Trafik akış verimliliğinin ve seyahat süresinin optimizasyonu",
                    "Sistem performansının ve kullanıcı deneyiminin geliştirilmesi"
                ]
            },
            {
                'ay': 11,
                'baslik': "Ölçeklendirme ve Genişletme",
                'gorevler': [
                    "Sistemin daha geniş alanlara ölçeklendirilmesi planı",
                    "Farklı ulaşım modlarıyla entegrasyon olanaklarının araştırılması",
                    "Veri analitiği ve iş zekası özelliklerinin genişletilmesi"
                ]
            },
            {
                'ay': 12,
                'baslik': "Etki Değerlendirmesi ve Yaygınlaştırma",
                'gorevler': [
                    "Trafik akışı, seyahat süresi ve emisyon etkilerinin değerlendirilmesi",
                    "Ekonomik fayda ve kaynak verimliliği analizinin tamamlanması",
                    "Uygulama stratejisi ve yaygınlaştırma planının oluşturulması"
                ]
            }
        ]
        
        return plan

    def _create_finance_plan(self, project_details):
        """Finans teknolojisi projesi planı"""
        proje_konusu = project_details.get('proje_konusu', 'Finans Teknolojisi Projesi')
        
        plan = [
            {
                'ay': 1,
                'baslik': "Fintech Pazar Araştırması ve İhtiyaç Analizi",
                'gorevler': [
                    "Fintech ekosistemi ve mevcut çözümlerin incelenmesi",
                    "Hedef kullanıcı segmentlerinin ve ihtiyaçlarının belirlenmesi",
                    "Finansal düzenlemeler ve uyumluluk gereksinimlerinin araştırılması"
                ]
            },
            {
                'ay': 2,
                'baslik': "Finansal Ürün Tasarımı ve İş Modeli",
                'gorevler': [
                    "Finansal ürün/hizmet özelliklerinin ve kapsamının belirlenmesi",
                    "Gelir modeli ve değer önerisinin oluşturulması",
                    "Risk değerlendirmesi ve yönetim stratejilerinin geliştirilmesi"
                ]
            },
            {
                'ay': 3,
                'baslik': "Finansal Sistem Mimarisi ve Güvenlik Tasarımı",
                'gorevler': [
                    "Finansal sistem mimarisinin ve veri yapısının tasarlanması",
                    "Güvenlik protokolleri ve veri koruma stratejilerinin oluşturulması",
                    "Kimlik doğrulama ve yetkilendirme sistemlerinin tasarımı"
                ]
            },
            {
                'ay': 4,
                'baslik': "Finansal İşlem Altyapısı Geliştirme",
                'gorevler': [
                    "Ödeme işleme sistemlerinin ve API entegrasyonlarının geliştirilmesi",
                    "İşlem doğrulama ve mutabakat mekanizmalarının oluşturulması",
                    "Finansal veri işleme ve kayıt sistemlerinin implementasyonu"
                ]
            },
            {
                'ay': 5,
                'baslik': "Veri Analizi ve Finansal Algoritma Geliştirme",
                'gorevler': [
                    "Finansal veri analizi metodolojilerinin uygulanması",
                    "Risk değerlendirme ve kredi skorlama algoritmalarının geliştirilmesi",
                    "Anomali tespiti ve dolandırıcılık önleme sistemlerinin tasarımı"
                ]
            },
            {
                'ay': 6,
                'baslik': "Kullanıcı Arayüzü ve Deneyimi Tasarımı",
                'gorevler': [
                    "Müşteri arayüzü ve finansal dashboard tasarımı",
                    "Mobil ve web uygulamalarının geliştirilmesi",
                    "Kullanıcı dostu finansal raporlama araçlarının oluşturulması"
                ]
            },
            {
                'ay': 7,
                'baslik': "Finansal Kurumlar ile Entegrasyon",
                'gorevler': [
                    "Bankalar ve ödeme sistemleri ile API entegrasyonları",
                    "Finansal veri sağlayıcıları ile bağlantıların kurulması",
                    "Düzenleyici raporlama sistemlerinin geliştirilmesi"
                ]
            },
            {
                'ay': 8,
                'baslik': "Güvenlik Testleri ve Uyumluluk Doğrulama",
                'gorevler': [
                    "Kapsamlı güvenlik penetrasyon testlerinin gerçekleştirilmesi",
                    "Finansal düzenlemelere uygunluğun doğrulanması",
                    "Veri gizliliği ve koruma önlemlerinin test edilmesi"
                ]
            },
            {
                'ay': 9,
                'baslik': "Kapalı Beta Testi ve Kullanıcı Geri Bildirimleri",
                'gorevler': [
                    "Sınırlı kullanıcı grubuyla beta testlerinin başlatılması",
                    "Kullanıcı davranışları ve geri bildirimlerin analizi",
                    "İşlem doğruluğu ve sistem performansının değerlendirilmesi"
                ]
            },
            {
                'ay': 10,
                'baslik': "Sistem İyileştirmeleri ve Ölçeklendirme",
                'gorevler': [
                    "Beta testi sonuçlarına göre sistem iyileştirmeleri",
                    "Performans optimizasyonu ve ölçeklendirme çalışmaları",
                    "Yüksek işlem hacmi testleri ve stres testlerinin yapılması"
                ]
            },
            {
                'ay': 11,
                'baslik': "Açık Beta ve Pazar Genişletme",
                'gorevler': [
                    "Daha geniş kullanıcı kitlesiyle açık beta sürecinin başlatılması",
                    "Kullanıcı edinme ve aktivasyon stratejilerinin uygulanması",
                    "Ek finansal ürünler ve hizmetler için genişleme planının oluşturulması"
                ]
            },
            {
                'ay': 12,
                'baslik': "Tam Lansman ve Büyüme Stratejisi",
                'gorevler': [
                    "Ürünün resmi lansmanının gerçekleştirilmesi",
                    "Pazarlama ve kullanıcı edinme faaliyetlerinin yoğunlaştırılması",
                    "Gelecek dönem büyüme ve genişleme stratejisinin finalize edilmesi"
                ]
            }
        ]
        
        return plan

    def _create_ai_plan(self, project_details):
        """Yapay zeka projesi planı"""
        proje_konusu = project_details.get('proje_konusu', 'Yapay Zeka Projesi')
        
        plan = [
            {
                'ay': 1,
                'baslik': "Yapay Zeka Araştırması ve Problem Tanımı",
                'gorevler': [
                    "İlgili yapay zeka alanındaki mevcut çalışmaların incelenmesi",
                    "Problem tanımının netleştirilmesi ve proje kapsamının belirlenmesi",
                    "Yapay zeka çözümü için uygun algoritma ve yaklaşımların araştırılması"
                ]
            },
            {
                'ay': 2,
                'baslik': "Veri Gereksinimi ve Veri Toplama Stratejisi",
                'gorevler': [
                    "Yapay zeka modeli için veri gereksinimlerinin belirlenmesi",
                    "Veri kaynaklarının tanımlanması ve veri toplama metodolojisinin oluşturulması",
                    "Veri etiketleme ve doğrulama stratejilerinin geliştirilmesi"
                ]
            },
            {
                'ay': 3,
                'baslik': "Veri Toplama ve Ön İşleme",
                'gorevler': [
                    "Veri setlerinin toplanması ve düzenlenmesi",
                    "Veri temizleme ve normalizasyon işlemlerinin gerçekleştirilmesi",
                    "Veri kalitesi değerlendirmesi ve istatistiksel analizlerin yapılması"
                ]
            },
            {
                'ay': 4,
                'baslik': "Özellik Mühendisliği ve Veri Analizi",
                'gorevler': [
                    "Önemli özelliklerin belirlenmesi ve özellik çıkarımı",
                    "Özellik seçimi ve boyut indirgeme tekniklerinin uygulanması",
                    "Veri görselleştirme ve keşifsel veri analizinin yapılması"
                ]
            },
            {
                'ay': 5,
                'baslik': "Model Seçimi ve Başlangıç Eğitimi",
                'gorevler': [
                    "Yapay zeka model mimarisinin tasarlanması",
                    "Başlangıç model parametrelerinin belirlenmesi",
                    "İlk model eğitiminin gerçekleştirilmesi ve başlangıç performans değerlendirmesi"
                ]
            },
            {
                'ay': 6,
                'baslik': "Model Optimizasyonu ve Hiperparametre Ayarlaması",
                'gorevler': [
                    "Model hiperparametrelerinin optimizasyonu",
                    "Çapraz doğrulama ve model seçim stratejilerinin uygulanması",
                    "Model performansının iyileştirilmesi ve hata analizinin yapılması"
                ]
            },
            {
                'ay': 7,
                'baslik': "Model Değerlendirme ve Doğrulama",
                'gorevler': [
                    "Kapsamlı model değerlendirme metriklerinin uygulanması",
                    "Test veri seti üzerinde model performansının doğrulanması",
                    "Farklı senaryolarda model dayanıklılığının test edilmesi"
                ]
            },
            {
                'ay': 8,
                'baslik': "Yapay Zeka Modeli Entegrasyonu",
                'gorevler': [
                    "Modelin üretim ortamına entegrasyonu için altyapı hazırlığı",
                    "Model servis etme ve API geliştirme çalışmaları",
                    "Model versiyonlama ve izleme sistemlerinin oluşturulması"
                ]
            },
            {
                'ay': 9,
                'baslik': "Uygulama Geliştirme ve Kullanıcı Arayüzü",
                'gorevler': [
                    "Yapay zeka çözümünü kullanan uygulama arayüzünün geliştirilmesi",
                    "Kullanıcı etkileşimi ve geri bildirim mekanizmalarının oluşturulması",
                    "Yapay zeka çıktılarının görselleştirilmesi ve yorumlanması"
                ]
            },
            {
                'ay': 10,
                'baslik': "Pilot Uygulama ve Kullanıcı Testleri",
                'gorevler': [
                    "Kontrollü ortamda pilot uygulamanın başlatılması",
                    "Kullanıcı etkileşimi ve model performansının gözlemlenmesi",
                    "Geri bildirimlere dayalı model ve uygulama iyileştirmeleri"
                ]
            },
            {
                'ay': 11,
                'baslik': "Ölçeklendirme ve Performans Optimizasyonu",
                'gorevler': [
                    "Büyük veri hacimleri için sistem ölçeklendirmesi",
                    "Çıkarım süresi ve kaynak kullanımı optimizasyonu",
                    "Gerçek zamanlı yapay zeka çıkarımlarının iyileştirilmesi"
                ]
            },
            {
                'ay': 12,
                'baslik': "Değerlendirme ve Sürdürülebilirlik Planı",
                'gorevler': [
                    "Yapay zeka çözümünün iş değeri ve etkisinin değerlendirilmesi",
                    "Model güncelleme ve yeniden eğitim stratejisinin oluşturulması",
                    "Sürekli iyileştirme ve izleme planının geliştirilmesi"
                ]
            }
        ]
        
        return plan

    def _create_web_plan(self, project_details):
        """Web projesi planı"""
        proje_konusu = project_details.get('proje_konusu', 'Web Projesi')
        
        plan = [
            {
                'ay': 1,
                'baslik': "Web Projesi Araştırması ve Gereksinim Analizi",
                'gorevler': [
                    "Pazar araştırması ve rekabet analizi",
                    "Kullanıcı ihtiyaçları ve hedef kitle analizi",
                    "Fonksiyonel ve teknik gereksinimlerin belirlenmesi"
                ]
            },
            {
                'ay': 2,
                'baslik': "Kullanıcı Deneyimi ve Arayüz Tasarımı",
                'gorevler': [
                    "Kullanıcı personaları ve kullanım senaryolarının oluşturulması",
                    "Bilgi mimarisi ve site haritasının tasarlanması",
                    "Wireframe ve prototiplerin hazırlanması"
                ]
            },
            {
                'ay': 3,
                'baslik': "Görsel Tasarım ve Marka Kimliği",
                'gorevler': [
                    "Marka kimliği ve tasarım dilinin oluşturulması",
                    "Görsel tasarım öğeleri ve UI kit hazırlanması",
                    "Responsive tasarım ilkelerinin uygulanması"
                ]
            },
            {
                'ay': 4,
                'baslik': "Frontend Geliştirme",
                'gorevler': [
                    "HTML, CSS ve JavaScript ile temel yapının oluşturulması",
                    "Responsive ve cross-browser uyumlu arayüzün geliştirilmesi",
                    "Kullanıcı etkileşimi ve animasyonların implementasyonu"
                ]
            },
            {
                'ay': 5,
                'baslik': "Backend Altyapı Geliştirme",
                'gorevler': [
                    "Veritabanı şemasının tasarlanması ve kurulumu",
                    "API endpoints ve servis katmanının geliştirilmesi",
                    "Kullanıcı kimlik doğrulama ve yetkilendirme sisteminin oluşturulması"
                ]
            },
            {
                'ay': 6,
                'baslik': "İçerik Yönetim Sistemi Geliştirme",
                'gorevler': [
                    "İçerik modelleri ve yapılarının oluşturulması",
                    "İçerik yönetimi arayüzünün geliştirilmesi",
                    "İçerik versiyonlama ve yayın akışı mekanizmalarının implementasyonu"
                ]
            },
            {
                'ay': 7,
                'baslik': "Entegrasyon ve API Geliştirme",
                'gorevler': [
                    "Üçüncü parti servisler ve API'lar ile entegrasyon",
                    "Ödeme, bildirim ve diğer servis entegrasyonları",
                    "API dokümantasyonu ve geliştirici araçlarının oluşturulması"
                ]
            },
            {
                'ay': 8,
                'baslik': "Test ve Kalite Güvence",
                'gorevler': [
                    "Fonksiyonel ve kullanıcı arayüzü testlerinin gerçekleştirilmesi",
                    "Performans, güvenlik ve erişilebilirlik testleri",
                    "Hata ayıklama ve düzeltme çalışmaları"
                ]
            },
            {
                'ay': 9,
                'baslik': "Beta Sürümü ve Kullanıcı Testleri",
                'gorevler': [
                    "Beta sürümünün yayınlanması ve test kullanıcılarına erişim sağlanması",
                    "Kullanıcı geri bildirimlerinin toplanması ve analizi",
                    "Kullanılabilirlik ve kullanıcı deneyimi iyileştirmeleri"
                ]
            },
            {
                'ay': 10,
                'baslik': "Performans Optimizasyonu ve SEO",
                'gorevler': [
                    "Web sitesi performansının ve yükleme hızının optimizasyonu",
                    "SEO stratejisinin uygulanması ve teknik SEO iyileştirmeleri",
                    "İçerik stratejisi ve organik trafik artırma çalışmaları"
                ]
            },
            {
                'ay': 11,
                'baslik': "Lansman Hazırlıkları ve Son İyileştirmeler",
                'gorevler': [
                    "Son kullanıcı testleri ve hata düzeltmeleri",
                    "İçerik hazırlığı ve içerik girişlerinin tamamlanması",
                    "Lansman planı ve pazarlama stratejisinin oluşturulması"
                ]
            },
            {
                'ay': 12,
                'baslik': "Lansman ve İzleme",
                'gorevler': [
                    "Web sitesinin resmi lansmanının gerçekleştirilmesi",
                    "Kullanıcı davranışları ve site performansının izlenmesi",
                    "Analitik verilere dayalı sürekli iyileştirme planının oluşturulması"
                ]
            }
        ]
        
        return plan

    def _create_mobile_plan(self, project_details):
        """Mobil uygulama projesi planı"""
        proje_konusu = project_details.get('proje_konusu', 'Mobil Uygulama Projesi')
        
        plan = [
            {
                'ay': 1,
                'baslik': "Mobil Uygulama Fikri ve Pazar Araştırması",
                'gorevler': [
                    "Hedef kitle analizi ve kullanıcı ihtiyaçlarının belirlenmesi",
                    "Rakip uygulamaların incelenmesi ve pazar analizi",
                    "Uygulama konseptinin ve değer önerisinin netleştirilmesi"
                ]
            },
            {
                'ay': 2,
                'baslik': "Uygulama Gereksinimleri ve Özellik Planlaması",
                'gorevler': [
                    "Fonksiyonel ve teknik gereksinimlerin belirlenmesi",
                    "Uygulama özellikleri ve öncelik sıralamasının oluşturulması",
                    "Teknik fizibilite ve platform seçiminin yapılması"
                ]
            },
            {
                'ay': 3,
                'baslik': "Kullanıcı Deneyimi ve Arayüz Tasarımı",
                'gorevler': [
                    "Kullanıcı akışı ve navigasyon yapısının tasarlanması",
                    "Wireframe ve uygulama ekranlarının prototiplenmesi",
                    "Tasarım dili ve görsel öğelerin oluşturulması"
                ]
            },
            {
                'ay': 4,
                'baslik': "Uygulama Mimarisi ve Veritabanı Tasarımı",
                'gorevler': [
                    "Uygulama mimarisinin ve modül yapısının tasarlanması",
                    "Veritabanı şeması ve veri modellerinin oluşturulması",
                    "API entegrasyon noktaları ve veri akışının planlanması"
                ]
            },
            {
                'ay': 5,
                'baslik': "Backend Geliştirme ve API Oluşturma",
                'gorevler': [
                    "Backend servislerinin ve API endpoints'lerin geliştirilmesi",
                    "Kullanıcı yönetimi ve kimlik doğrulama sistemlerinin oluşturulması",
                    "Veri depolama ve senkronizasyon mekanizmalarının implementasyonu"
                ]
            },
            {
                'ay': 6,
                'baslik': "Mobil Uygulama Geliştirme (İlk Aşama)",
                'gorevler': [
                    "Temel uygulama yapısı ve navigasyonun geliştirilmesi",
                    "Kullanıcı arayüzü bileşenlerinin oluşturulması",
                    "Ana özelliklerin implementasyonu ve ilk çalışan prototip"
                ]
            },
            {
                'ay': 7,
                'baslik': "Mobil Uygulama Geliştirme (İkinci Aşama)",
                'gorevler': [
                    "Gelişmiş özelliklerin ve ikincil işlevlerin implementasyonu",
                    "Kullanıcı geri bildirimi ve bildirim sistemlerinin geliştirilmesi",
                    "Çevrimdışı modu ve veri senkronizasyonunun tamamlanması"
                ]
            },
            {
                'ay': 8,
                'baslik': "Entegrasyon ve Üçüncü Parti Servisler",
                'gorevler': [
                    "Analitik, crash reporting ve izleme araçlarının entegrasyonu",
                    "Sosyal medya, ödeme sistemleri ve diğer üçüncü parti servislerin entegrasyonu",
                    "Push bildirimleri ve bulut mesajlaşma sistemlerinin implementasyonu"
                ]
            },
            {
                'ay': 9,
                'baslik': "Test ve Kalite Güvence",
                'gorevler': [
                    "Fonksiyonel ve kullanıcı arayüzü testlerinin gerçekleştirilmesi",
                    "Performans, güvenlik ve uyumluluk testleri",
                    "Farklı cihazlarda ve işletim sistemi versiyonlarında test edilmesi"
                ]
            },
            {
                'ay': 10,
                'baslik': "Beta Testi ve Kullanıcı Geribildirimleri",
                'gorevler': [
                    "Kapalı beta testinin başlatılması ve test kullanıcılarının yönetimi",
                    "Kullanıcı geri bildirimlerinin toplanması ve önceliklendirilmesi",
                    "Hata düzeltmeleri ve kullanıcı deneyimi iyileştirmeleri"
                ]
            },
            {
                'ay': 11,
                'baslik': "Uygulama Mağaza Hazırlıkları",
                'gorevler': [
                    "Uygulama mağaza listeleme içeriklerinin hazırlanması",
                    "Mağaza grafikleri, ekran görüntüleri ve tanıtım videosunun oluşturulması",
                    "App Store ve Google Play Store için yayın hazırlıklarının tamamlanması"
                ]
            },
            {
                'ay': 12,
                'baslik': "Lansman ve Pazarlama",
                'gorevler': [
                    "Uygulamanın mağazalarda yayınlanması",
                    "Lansman pazarlama kampanyasının yürütülmesi",
                    "Kullanıcı edinme ve aktivasyon stratejilerinin uygulanması"
                ]
            }
        ]
        
        return plan

    def _create_general_tech_plan(self, project_details):
        """Genel teknoloji projesi planı"""
        proje_konusu = project_details.get('proje_konusu', 'Teknoloji Projesi')
        
        plan = [
            {
                'ay': 1,
                'baslik': "Proje Tanımı ve Araştırma",
                'gorevler': [
                    f"{proje_konusu if proje_konusu else 'Proje'} kapsamının ve hedeflerinin belirlenmesi",
                    "Mevcut teknolojilerin ve çözümlerin araştırılması",
                    "Pazar analizi ve kullanıcı ihtiyaçlarının belirlenmesi"
                ]
            },
            {
                'ay': 2,
                'baslik': "Gereksinim Analizi",
                'gorevler': [
                    "Fonksiyonel ve teknik gereksinimlerin dokümantasyonu",
                    "Kullanıcı hikayeleri ve kullanım senaryolarının oluşturulması",
                    "Teknik fizibilite ve risk değerlendirmesinin yapılması"
                ]
            },
            {
                'ay': 3,
                'baslik': "Sistem Tasarımı ve Mimarisi",
                'gorevler': [
                    "Sistem mimarisinin ve bileşenlerinin tasarlanması",
                    "Veritabanı modeli ve veri akış diyagramlarının oluşturulması",
                    "Teknoloji stack'inin ve platformların seçimi"
                ]
            },
            {
                'ay': 4,
                'baslik': "Prototip Geliştirme",
                'gorevler': [
                    "Minimum uygulanabilir ürün (MVP) kapsamının belirlenmesi",
                    "Temel fonksiyonel prototiplerin geliştirilmesi",
                    "Konsept doğrulama testlerinin gerçekleştirilmesi"
                ]
            },
            {
                'ay': 5,
                'baslik': "Temel Geliştirme",
                'gorevler': [
                    "Çekirdek sistem bileşenlerinin geliştirilmesi",
                    "Veritabanı yapısının ve temel API'ların oluşturulması",
                    "Temel işlevsellik testlerinin yapılması"
                ]
            },
            {
                'ay': 6,
                'baslik': "Kullanıcı Arayüzü Geliştirme",
                'gorevler': [
                    "Kullanıcı arayüzü tasarımının ve akışının geliştirilmesi",
                    "Kullanıcı deneyimi (UX) optimizasyonu",
                    "Arayüz bileşenlerinin implementasyonu"
                ]
            },
            {
                'ay': 7,
                'baslik': "İleri Özellik Geliştirme",
                'gorevler': [
                    "Gelişmiş sistem özelliklerinin implementasyonu",
                    "Entegrasyon noktalarının geliştirilmesi",
                    "Performans iyileştirmeleri ve optimizasyon"
                ]
            },
            {
                'ay': 8,
                'baslik': "Test ve Kalite Güvence",
                'gorevler': [
                    "Kapsamlı test planının hazırlanması ve uygulanması",
                    "Birim testleri, entegrasyon testleri ve kullanıcı kabul testleri",
                    "Hata tespiti ve düzeltme çalışmaları"
                ]
            },
            {
                'ay': 9,
                'baslik': "Pilot Uygulama ve Beta Testi",
                'gorevler': [
                    "Kontrollü kullanıcı grubuyla pilot uygulamanın başlatılması",
                    "Kullanıcı geri bildirimlerinin toplanması ve analizi",
                    "Beta sürümü iyileştirmeleri ve hata düzeltmeleri"
                ]
            },
            {
                'ay': 10,
                'baslik': "Sistem Entegrasyonu ve Ölçeklendirme",
                'gorevler': [
                    "Tüm sistem bileşenlerinin tam entegrasyonu",
                    "Ölçeklenebilirlik testleri ve optimizasyonu",
                    "Yük testleri ve performans değerlendirmesi"
                ]
            },
            {
                'ay': 11,
                'baslik': "Dokümantasyon ve Eğitim",
                'gorevler': [
                    "Kullanıcı kılavuzları ve teknik dokümantasyonun hazırlanması",
                    "Eğitim materyallerinin geliştirilmesi",
                    "Bilgi tabanı ve destek dokümanlarının oluşturulması"
                ]
            },
            {
                'ay': 12,
                'baslik': "Lansman ve Yaygınlaştırma",
                'gorevler': [
                    "Ürün lansmanının gerçekleştirilmesi",
                    "Pazarlama ve yaygınlaştırma faaliyetlerinin başlatılması",
                    "Kullanıcı desteği ve sürekli iyileştirme planının uygulanması"
                ]
            }
        ]
        
        return plan
    
    def _format_plan(self, plan, project_details):
        """Planı formatla"""
        now = datetime.datetime.now()
        
        # Üst bilgiyi oluştur
        fon_kodu = project_details.get('fon_kodu', '')
        fon_adi = project_details.get('fon_adi', 'TÜBİTAK Projesi')
        
        # Fon kodu varsa göster, yoksa sadece program adını göster
        if fon_kodu:
            header = f"TÜBİTAK {fon_kodu} -- {fon_adi}\n"
        else:
            header = f"TÜBİTAK -- {fon_adi}\n"
        
        header += f"Oluşturulma modeli: LSTM\n"
        header += f"Tarih: {now.strftime('%d.%m.%Y %H:%M')}\n"
        header += f"TÜBİTAK PROJESİ - 12 AYLIK PLAN\n"
        
        # Planı formatla
        lines = []
        for ay_plan in sorted(plan, key=lambda x: x['ay']):
            ay = ay_plan['ay']
            baslik = ay_plan['baslik']
            gorevler = ay_plan['gorevler']
            
            lines.append(f"Ay {ay}: {baslik}")
            for gorev in gorevler:
                lines.append(f"- {gorev}")
        
        plan_text = '\n'.join(lines)
        
        # Alt bilgiyi ekle
        footer = f"\n[TÜBİTAK LSTM AI tarafından oluşturuldu]"
        
        return header + plan_text + footer
    
    def generate_doc(self, plan_text, filename="tubitak_proje_plani"):

        """DOC formatında proje planı oluştur"""
        try:
            # Metinden proje detaylarını çıkar
            project_details = self._extract_project_details(plan_text)
            fon_kodu = project_details.get('fon_kodu', '')
            fon_adi = project_details.get('fon_adi', 'TÜBİTAK Projesi')
            
            # Şu anki tarih ve saat
            now = datetime.datetime.now()
            date_str = now.strftime("%d.%m.%Y")
            time_str = now.strftime("%H:%M")
            
            # Plan metnini düzenli bir şekilde ayırın
            lines = plan_text.split('\n')
            
            # HTML formatında DOC dosyası içeriği oluştur
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>TÜBİTAK {fon_kodu} Proje Planı</title>
    <style>
        body {{ font-family: 'Arial', sans-serif; margin: 30px; }}
        h1 {{ color: #003366; text-align: center; }}
        h2 {{ color: #005599; margin-top: 20px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .footer {{ text-align: center; margin-top: 30px; font-size: 0.8em; color: #666; }}
        ul {{ margin-bottom: 15px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>TÜBİTAK {fon_kodu} -- {fon_adi}</h1>
        <p>Oluşturulma modeli: LSTM</p>
        <p>Tarih: {date_str} {time_str}</p>
        <h2>TÜBİTAK PROJESİ - 12 AYLIK PLAN</h2>
    </div>
    
    <div class="content">
"""
            
            current_month = None
            for line in lines:
                if line.strip():
                    if line.startswith("Ay "):
                        if current_month:
                            html_content += "</ul>\n"
                        current_month = line
                        html_content += f"<h2>{line}</h2>\n<ul>\n"
                    elif line.startswith("- ") and current_month:
                        html_content += f"<li>{line[2:]}</li>\n"
                    else:
                        html_content += f"<p>{line}</p>\n"
            
            if current_month:
                html_content += "</ul>\n"
            
            html_content += """
    </div>
    
    <div class="footer">
        <p>Bu plan TÜBİTAK LSTM AI tarafından otomatik olarak oluşturulmuştur.</p>
    </div>
</body>
</html>
"""
            
            # DOC dosyası için HTML içeriğini döndür
            return {
                "filename": f"{filename}.doc",
                "content": html_content,
                "content_type": "application/msword"
            }
            
        except Exception as e:
            import traceback
            print(f"DOC oluşturma hatası: {e}")
            print(traceback.format_exc())
            return None
        

    def process_command(self, command_response, plan_text=None):
        """Komut yanıtlarını işle"""
        if isinstance(command_response, dict) and 'command' in command_response:
            command = command_response['command']
        
            if command == "generate_doc":
                if plan_text is None:
                    return "DOC oluşturmak için plan metni gerekiyor."
                doc_result = self.generate_doc(plan_text)
                if doc_result:
                    return {"doc_file": doc_result, "message": "DOC başarıyla indirildi!"}
                else:
                    return "DOC oluşturulurken bir hata oluştu."
                
            elif command == "generate_calendar":
                if plan_text is None:
                    return "Takvim oluşturmak için plan metni gerekiyor."
            # Takvim oluşturma fonksiyonu eklenebilir
                return "Takvim oluşturma işlevi henüz eklenmedi."
            
            else:
                return command_response.get('message', "Bilinmeyen komut.")
    
        return command_response