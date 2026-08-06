from django.db import models
from django.contrib.auth.models import User

class Project(models.Model):
    """TÜBİTAK fonu için proje planı"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    ai_model_used = models.CharField(max_length=50, default="custom_lstm")

    # Yeni eklenen alanlar
    fon_turu = models.CharField(
        max_length=50,
        verbose_name="Fon Türü",
        blank=True,
        null=True,
        help_text="Örn. TÜBİTAK 1001, 1002 vb."
    )
    duration_months = models.IntegerField(
        default=12,
        verbose_name="Proje Süresi (Ay)",
        help_text="Fon türüne göre önerilen proje süresi"
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='projects'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    chat_session_id = models.CharField(max_length=100, blank=True, null=True)
    ai_response = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Task(models.Model):
    """Proje içindeki görevler"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    completed = models.BooleanField(default=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date']

    def __str__(self):
        return self.name


class FundDuration(models.Model):
    """Fon süreleri için veritabanı modeli"""
    id = models.AutoField(primary_key=True)
    kod = models.CharField(max_length=20, unique=True, verbose_name="Fon Kodu")
    tur = models.CharField(max_length=100, verbose_name="Fon Türü")
    ay_suresi = models.IntegerField(verbose_name="Ay Süresi")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    aktif = models.BooleanField(default=True, verbose_name="Aktif")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturma Tarihi")
    guncelleme_tarihi = models.DateTimeField(auto_now=True, verbose_name="Güncelleme Tarihi")
    
    class Meta:
        managed = False  # Django bu tabloyu yönetmesin
        db_table = 'chat_fon'  # Gerçek tablo adı
        verbose_name = "Fon Süresi"
        verbose_name_plural = "Fon Süreleri"
        ordering = ['kod']
    
    def __str__(self):
        return f"{self.kod} - {self.tur} ({self.ay_suresi} ay)"