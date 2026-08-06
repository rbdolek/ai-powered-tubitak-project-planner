from django.contrib import admin
from .models import ChatSession, ChatMessage, Fon, AiPlan, UserFeedback, AgentLog, AgentPerformance

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'ai_model', 'created_at', 'updated_at')
    list_filter = ('ai_model', 'created_at')
    search_fields = ('user__username',)
    date_hierarchy = 'created_at'

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'is_user', 'content_preview', 'timestamp', 'related_plan')
    list_filter = ('is_user', 'session__ai_model')
    search_fields = ('content', 'session__user__username')
    raw_id_fields = ('related_plan',)
    
    def content_preview(self, obj):
        if len(obj.content) > 50:
            return f"{obj.content[:50]}..."
        return obj.content
    content_preview.short_description = 'Content'

@admin.register(Fon)
class FonAdmin(admin.ModelAdmin):
    list_display = ('kod', 'tur', 'ay_suresi', 'aktif', 'olusturma_tarihi')
    list_filter = ('aktif', 'ay_suresi', 'olusturma_tarihi')
    search_fields = ('kod', 'tur', 'aciklama')
    list_editable = ('aktif',)
    date_hierarchy = 'olusturma_tarihi'
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('kod', 'tur', 'ay_suresi')
        }),
        ('Detaylar', {
            'fields': ('aciklama', 'aktif'),
            'classes': ('collapse',)
        }),
    )

@admin.register(AiPlan)
class AiPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'fon', 'user', 'ay_suresi', 'plan_preview', 'feedback_score', 'olusturma_tarihi')
    list_filter = ('fon', 'ay_suresi', 'feedback_score', 'olusturma_tarihi')
    search_fields = ('plan_metni', 'fon__kod', 'fon__tur', 'user__username')
    readonly_fields = ('olusturma_tarihi',)
    date_hierarchy = 'olusturma_tarihi'
    raw_id_fields = ('user', 'fon')
    
    def plan_preview(self, obj):
        if len(obj.plan_metni) > 50:
            return f"{obj.plan_metni[:50]}..."
        return obj.plan_metni
    plan_preview.short_description = 'Plan Önizleme'
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('fon', 'user', 'ay_suresi', 'feedback_score')
        }),
        ('Plan İçeriği', {
            'fields': ('plan_metni',),
            'classes': ('wide',)
        }),
        ('Meta Veriler', {
            'fields': ('meta_data', 'olusturma_tarihi'),
            'classes': ('collapse',)
        }),
    )

@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'plan', 'user', 'puan', 'yorum_preview', 'olusturma_tarihi')
    list_filter = ('puan',)
    search_fields = ('yorum', 'user__username', 'plan__fon__kod')
    raw_id_fields = ('user', 'plan')
    
    def yorum_preview(self, obj):
        if obj.yorum and len(obj.yorum) > 50:
            return f"{obj.yorum[:50]}..."
        return obj.yorum or "-"
    yorum_preview.short_description = 'Yorum'

@admin.register(AgentLog)
class AgentLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'islem_tipi', 'detay_preview', 'user', 'plan', 'olusturma_tarihi')
    list_filter = ('islem_tipi', 'olusturma_tarihi')
    search_fields = ('detay', 'user__username')
    readonly_fields = ('olusturma_tarihi',)
    date_hierarchy = 'olusturma_tarihi'
    raw_id_fields = ('user', 'plan')
    
    def detay_preview(self, obj):
        if len(obj.detay) > 50:
            return f"{obj.detay[:50]}..."
        return obj.detay
    detay_preview.short_description = 'Detay'

@admin.register(AgentPerformance)
class AgentPerformanceAdmin(admin.ModelAdmin):
    list_display = ('tarih', 'tahmin_sayisi', 'ortalama_puan', 'basarili_tahmin', 'egitim_sayisi', 'egitim_suresi_format')
    list_filter = ('tarih',)
    date_hierarchy = 'tarih'
    
    def egitim_suresi_format(self, obj):
        # Saniyeyi saat:dakika:saniye formatına dönüştür
        hours, remainder = divmod(obj.egitim_suresi, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    egitim_suresi_format.short_description = 'Eğitim Süresi'
    
    # Tarih değiştikçe performans metriklerini görmek için grafikler
    def changelist_view(self, request, extra_context=None):
        # Bu fonksiyon, liste görünümünde ek içerik eklemenizi sağlar
        # Burada gerçek bir grafik uygulaması yapmak bu cevabın kapsamı dışında
        # Ancak django-admin-charts gibi bir paket kullanabilirsiniz
        extra_context = extra_context or {}
        extra_context['show_metrics'] = True
        return super().changelist_view(request, extra_context=extra_context)