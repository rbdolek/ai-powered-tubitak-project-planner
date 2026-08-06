import os
import random
import json
import nltk
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from chat.models import Fon, AiPlan, ChatSession, ChatMessage, UserFeedback

# Ensure Turkish sentence tokenizer is available
def _setup_nltk():
    nltk_data_path = os.path.join(settings.BASE_DIR, "nltk_data")
    if nltk_data_path not in nltk.data.path:
        nltk.data.path.append(nltk_data_path)
    nltk.download('punkt', quiet=True)

_setup_nltk()

User = get_user_model()

def make_turkish_plan(fon_kod, fon_tur, ay_suresi):
    if ay_suresi <= 3:
        phases = ["Hazırlık", "Uygulama", "Sonuçlandırma"]
    elif ay_suresi <= 6:
        phases = ["Hazırlık", "Geliştirme", "Uygulama", "Değerlendirme", "Sonuçlandırma"]
    else:
        phases = [
            "Planlama", "Hazırlık", "Geliştirme",
            "Uygulama (1. Dönem)", "Ara Değerlendirme",
            "Uygulama (2. Dönem)", "Analiz", "Raporlama", "Yaygınlaştırma"
        ]

    lines = [
        f"TÜBİTAK {fon_kod} {fon_tur} Programı için {ay_suresi} Aylık Proje Planı",
        ""
    ]
    for month in range(1, ay_suresi + 1):
        phase = phases[(month - 1) % len(phases)]
        lines.append(f"Ay {month}: {phase} aşaması görevleri yürütülecek.")
    lines.append("")
    lines.append("Her ay gerekli dokümantasyon, raporlama ve ara değerlendirmeler yapılacaktır.")
    return "\n".join(lines)

class Command(BaseCommand):
    help = "Tubitak_db'ye örnek veri ekler (7 fon + 1000 rasgele kayıt)"

    @transaction.atomic
    def handle(self, *args, **options):
        # 0) Önceki 1000 örneğin silinmesi: plan tablosunda ilk 86 kaydı koru, geri kalanı sil
        all_plans = AiPlan.objects.all().order_by('id')
        to_delete = all_plans[86:]
        if to_delete.exists():
            del_ids = list(to_delete.values_list('id', flat=True))
            self.stdout.write(self.style.WARNING(f"🗑️ {len(del_ids)} eski örnek veri siliniyor..."))
            # bağımlı modeller önce
            ChatMessage.objects.filter(related_plan_id__in=del_ids).delete()
            UserFeedback.objects.filter(plan_id__in=del_ids).delete()
            ChatSession.objects.filter(plan_id__in=del_ids).delete()
            AiPlan.objects.filter(id__in=del_ids).delete()
        else:
            self.stdout.write(self.style.NOTICE("ℹ️ Silinecek eski örnek veri bulunamadı."))

        # 1) Fon kayıtları (eğer eksikse ekle)
        fon_turleri = ["Ar-Ge","Yenilik","Eğitim","Sağlık","Enerji","Tarım","Ulaştırma"]
        fons = []
        for idx, tur in enumerate(fon_turleri, start=1):
            kod = f"FON{idx:03d}"
            fon, _ = Fon.objects.get_or_create(
                kod=kod,
                defaults=dict(
                    tur=tur,
                    ay_suresi=random.choice([3,6,12,18,24]),
                    aciklama=f"{tur} alanında destek sağlayan fon.",
                    aktif=True,
                    olusturma_tarihi=timezone.now(),
                    guncelleme_tarihi=timezone.now(),
                )
            )
            fons.append(fon)

        users = list(User.objects.all())
        titles = [
            "Yaşlı Bakımda Yapay Zeka", "Akıllı Tarım Çözümleri",
            "Yeşil Enerji Opt.", "Otonom Lojistik",
            "Dijital Ruh Sağlığı", "Afet Müdahale", "Eğitim Platformu"
        ]
        queries = [
            "Yapay zekâ destekli yaşlı bakım sistemi için fon arıyorum.",
            "Tarımda verimi artırmak için hangi fonlara başvurabilirim?",
            "Yeşil enerji projeleri için destek var mı?",
            "Lojistikte otonom sistemler üzerine çalışıyorum, ne önerirsiniz?",
            "Ruh sağlığı üzerine dijital girişim için destek almak istiyorum.",
            "Afet sonrası destek sistemleri geliştirmek istiyorum, hangi fonlar uygun olur?",
            "Eğitim teknolojileri için Ar-Ge fonu araştırıyorum."
        ]

        # 2) Yeni örnek planlar oluştur
        plans = []
        now = timezone.now()
        for _ in range(1000):
            fon = random.choice(fons)
            user = random.choice(users)
            ts = now - timedelta(days=random.randint(0,365), hours=random.randint(0,23))
            duration = random.choice([3,6,12,18,24])
            query = random.choice(queries)

            turkce_plan = make_turkish_plan(fon.kod, fon.tur, duration)
            plans.append(AiPlan(
                olusturma_tarihi=ts,
                ay_suresi=duration,
                plan_metni=turkce_plan,
                meta_data=json.dumps({"query_info": {"original_query": query}}, ensure_ascii=False),
                user_id=user.id,
                fon_id=fon.id
            ))

        AiPlan.objects.bulk_create(plans, batch_size=1000)

        # 3) ChatSession ekle ve ilişkilendir
        session_objs = []
        for plan in plans:
            session_objs.append(ChatSession(
                ai_model="gpt-4",
                created_at=plan.olusturma_tarihi,
                updated_at=plan.olusturma_tarihi,
                user_id=plan.user_id,
                is_active=True,
                title=random.choice(titles),
                plan_id=plan.id
            ))
        ChatSession.objects.bulk_create(session_objs, batch_size=1000)

        # ID eşlemesi
        plan_ids = [p.id for p in plans]
        sessions_db = ChatSession.objects.filter(plan_id__in=plan_ids)
        session_map = {s.plan_id: s.id for s in sessions_db}

        # 4) Mesaj ve geri bildirim ekle
        messages, feedbacks = [], []
        for plan in plans:
            sess_id = session_map.get(plan.id)
            if not sess_id:
                continue
            msg_time = (plan.olusturma_tarihi + timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
            messages.append(ChatMessage(
                is_user=True,
                content=json.loads(plan.meta_data)["query_info"]["original_query"],
                timestamp=msg_time,
                session_id=sess_id,
                related_plan_id=plan.id
            ))
            uf_time = plan.olusturma_tarihi + timedelta(minutes=2)
            feedbacks.append(UserFeedback(
                plan_id=plan.id,
                puan=random.randint(1,5),
                yorum="Otomatik oluşturulmuş geri bildirim.",
                olusturma_tarihi=uf_time,
                user_id=plan.user_id
            ))

        ChatMessage.objects.bulk_create(messages, batch_size=1000)
        UserFeedback.objects.bulk_create(feedbacks, batch_size=1000)

        self.stdout.write(self.style.SUCCESS("✅ 1000 Türkçe kayıt başarıyla eklendi!"))
