from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime 
User = get_user_model()


class ChatSession(models.Model):
    """Kullanıcıya ait sohbet oturumu"""

    AI_MODEL_CHOICES = [
        ("openai", "OpenAI GPT-3.5"),
        ("lstm", "Custom LSTM Model"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_sessions")
    ai_model = models.CharField(max_length=50, choices=AI_MODEL_CHOICES, default="openai")
    title = models.CharField(max_length=255, blank=True, null=True)  # Sohbet başlığı
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    plan = models.ForeignKey(
        'AiPlan',              
        null=True,            
        blank=True,             
        on_delete=models.SET_NULL,
        related_name='chat_sessions'  
    )
    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user.username} -- {self.ai_model} (#{self.pk})"
    
    def get_first_message(self):
        """İlk mesajı başlık olarak kullanmak için"""
        first_message = self.messages.filter(is_user=True).first()
        if first_message:
            return first_message.content[:30] + ("..." if len(first_message.content) > 30 else "")
        return f"Sohbet #{self.pk}"


class ChatMessage(models.Model):
    """Bir sohbet oturumundaki tek bir mesaj"""

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    is_user = models.BooleanField(default=True)  # True: kullanıcı, False: AI
    content = models.TextField()
    timestamp = models.CharField(max_length=30)
    
    # LSTM model yanıtları için ek alanlar
    related_plan = models.ForeignKey('AiPlan', on_delete=models.SET_NULL, null=True, blank=True, related_name="chat_messages")
    metadata = models.JSONField(null=True, blank=True)  # LSTM yanıtının meta verileri
    
    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        sender = "User" if self.is_user else "AI"
        preview = self.content[:30] + ("..." if len(self.content) > 30 else "")
        return f"{sender}: {preview}"
    def save(self, *args, **kwargs):
        if not self.timestamp:
            # Timestamp string olarak kaydet
            self.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        super().save(*args, **kwargs)

class Fon(models.Model):
    """TÜBİTAK Fon Programları"""
    
    kod = models.CharField(max_length=20)
    tur = models.CharField(max_length=100)
    ay_suresi = models.IntegerField()
    aciklama = models.TextField(blank=True, null=True)
    aktif = models.BooleanField(default=True)
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    guncelleme_tarihi = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.kod} - {self.tur}"
    
    class Meta:
        verbose_name = "Fon"
        verbose_name_plural = "Fonlar"
        ordering = ["kod"]


class AiPlan(models.Model):
    """Agent AI tarafından oluşturulan araştırma planları"""
    
    fon = models.ForeignKey(Fon, on_delete=models.CASCADE, related_name='planlar')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_planlar')
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    ay_suresi = models.IntegerField()
    plan_metni = models.TextField()
    meta_data = models.TextField(blank=True, null=True)  # JSON olarak saklanacak metadatalar
    feedback_score = models.IntegerField(null=True, blank=True)  # 1-5 arası kullanıcı puanı
    
    def __str__(self):
        return f"Plan: {self.fon.kod} ({self.ay_suresi} ay)"
    
    class Meta:
        verbose_name = "AI Plan"
        verbose_name_plural = "AI Planlar"
        ordering = ["-olusturma_tarihi"]
    
    def get_preview(self):
        """Plan ön izlemesi"""
        return self.plan_metni[:100] + ("..." if len(self.plan_metni) > 100 else "")
    
    def get_feedback_status(self):
        """Geri bildirim durumu"""
        if self.feedback_score is None:
            return "Değerlendirilmedi"
        elif self.feedback_score >= 4:
            return "Çok İyi"
        elif self.feedback_score >= 3:
            return "İyi"
        elif self.feedback_score >= 2:
            return "Orta"
        else:
            return "Kötü"


class UserFeedback(models.Model):
    """Kullanıcı geri bildirimleri"""
    
    plan = models.ForeignKey(AiPlan, on_delete=models.CASCADE, related_name='feedbacks')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    puan = models.IntegerField()  # 1-5 arası
    yorum = models.TextField(blank=True, null=True)
    olusturma_tarihi = models.CharField(max_length=30)
    
    def __str__(self):
        return f"Geri Bildirim: Plan {self.plan.id} - Puan {self.puan}"
    def save(self, *args, **kwargs):
        if not self.olusturma_tarihi:
            # Timestamp string olarak kaydet
            self.olusturma_tarihi = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        super().save(*args, **kwargs)
    class Meta:
        verbose_name = "Kullanıcı Geri Bildirimi"
        verbose_name_plural = "Kullanıcı Geri Bildirimleri"
        ordering = ["-olusturma_tarihi"]


class AgentLog(models.Model):
    """Agent AI işlemlerini izlemek için log"""
    
    ISLEM_TIPLERI = (
        ('tahmin', 'Tahmin'),
        ('egitim', 'Eğitim'),
        ('geri_bildirim', 'Geri Bildirim'),
        ('pdf', 'PDF Oluşturma'),
        ('hata', 'Hata'),
    )
    
    islem_tipi = models.CharField(max_length=20, choices=ISLEM_TIPLERI)
    detay = models.TextField()
    plan = models.ForeignKey(AiPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name='loglar')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.islem_tipi} - {self.olusturma_tarihi}"
    
    class Meta:
        verbose_name = "Agent Log"
        verbose_name_plural = "Agent Loglar"
        ordering = ["-olusturma_tarihi"]


class AgentPerformance(models.Model):
    """Agent AI performans metrikleri"""
    
    tarih = models.DateField(default=timezone.now)
    tahmin_sayisi = models.IntegerField(default=0)
    ortalama_puan = models.FloatField(default=0.0)
    basarili_tahmin = models.IntegerField(default=0)  # 4 ve üzeri puan alan tahminler
    egitim_sayisi = models.IntegerField(default=0)
    egitim_suresi = models.IntegerField(default=0)  # Saniye cinsinden
    
    def __str__(self):
        return f"Performans: {self.tarih} - Ort. Puan: {self.ortalama_puan:.2f}"
    
    class Meta:
        verbose_name = "Agent Performans"
        verbose_name_plural = "Agent Performans Metrikleri"
        ordering = ["-tarih"]