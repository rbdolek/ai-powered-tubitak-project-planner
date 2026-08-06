from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Profile

# Profilin inline olarak gösterilmesi
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'

# Kullanıcı admin sayfasını özelleştirme
class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')

# Mevcut User admin kaydını kaldır ve özelleştirilmiş versiyonu kaydet
admin.site.unregister(User)  # Önce varsayılan kaydı kaldır
admin.site.register(User, CustomUserAdmin)  # Sonra özelleştirilmiş versiyonu kaydet

# Profile modelini ayrıca kaydet
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio')
    search_fields = ('user__username', 'user__email')