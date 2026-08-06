# project_planning/views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
import logging

from .models import Project, FundDuration
from .serializers import ProjectSerializer, FundDurationSerializer

logger = logging.getLogger(__name__)

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        # AI yanıtını kontrol et
        ai_response = self.request.data.get('ai_response')
        chat_session_id = self.request.data.get('chat_session_id')
        
        # Eğer AI yanıtı frontend'den gönderilmediyse ve chat_session_id varsa
        if not ai_response and chat_session_id:
            try:
                from chat.models import ChatSession, ChatMessage
                session = ChatSession.objects.get(id=chat_session_id, user=self.request.user)
                
                # Son AI mesajlarını getir
                ai_messages = ChatMessage.objects.filter(
                    session=session, 
                    is_user=False
                ).order_by('-timestamp')
                
                # "Ay 1:" içeren mesajı bul
                for message in ai_messages:
                    if "Ay 1:" in message.content:
                        ai_response = message.content
                        break
                
                # Bulunamadıysa son AI mesajını kullan
                if not ai_response and ai_messages.exists():
                    ai_response = ai_messages.first().content
                    
            except Exception as e:
                logger.error(f"ChatSession mesajlarını alırken hata: {str(e)}")
        
        # Projeyi kaydet
        serializer.save(owner=self.request.user, ai_response=ai_response)
@action(detail=True, methods=['get'])
def generate_pdf(self, request, pk=None):
    try:
        # Logla
        logger.info(f"generate_pdf tetiklendi, pk={pk}, user={request.user.username}")

        # Projeyi al
        project = self.get_object()
        
        # AI yanıtını kontrol et
        logger.info(f"Proje AI yanıt var mı: {bool(project.ai_response)}")
        if project.ai_response:
            logger.info(f"AI yanıt içeriği (ilk 100 karakter): {project.ai_response[:100]}")
            logger.info(f"'Ay 1:' içeriyor mu: {'Ay 1:' in project.ai_response}")
            
        # PDF oluşturma işlemleri
        from io import BytesIO
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors

        buffer = BytesIO()

        # Belge oluştur
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # İçerik hazırlama
        styles = getSampleStyleSheet()
        
        # Özel stiller ekle
        styles.add(ParagraphStyle(
            name='MonthTitle',
            parent=styles['Heading2'],
            textColor=colors.darkblue,
            spaceAfter=6
        ))
        
        styles.add(ParagraphStyle(
            name='Task',
            parent=styles['Normal'],
            leftIndent=20,
            bulletIndent=0,
            spaceAfter=3,
            bulletFontName='Symbol',
            bulletFontSize=10
        ))

        # İçerik listesi oluştur - elements burada tanımlanıyor
        elements = []

        # Başlık
        title_style = styles['Heading1']
        elements.append(Paragraph(f"Proje Adı: {project.title}", title_style))
        elements.append(Spacer(1, 12))

        # Oluşturan
        elements.append(Paragraph(f"Oluşturan: {project.owner.username}", styles['Normal']))
        elements.append(Spacer(1, 12))

        # Proje Bilgileri
        elements.append(Paragraph("Proje Detayları", styles['Heading2']))
        elements.append(Spacer(1, 6))

        # Açıklama
        elements.append(Paragraph("Açıklama:", styles['Heading3']))
        elements.append(Paragraph(project.description, styles['Normal']))
        elements.append(Spacer(1, 12))
    
        # Fon türü
        if project.fon_turu:
            elements.append(Paragraph(f"Fon Türü: {project.fon_turu}", styles['Normal']))
            elements.append(Spacer(1, 6))
    
        # Süre
        elements.append(Paragraph(f"Önerilen Süre: {project.duration_months} ay", styles['Normal']))
        elements.append(Spacer(1, 12))
        
        # AI yanıtını işleme - ÖNEMLİ DEĞİŞİKLİK BURADA
        if project.ai_response:
            elements.append(Paragraph("Proje Planı", styles['Heading2']))
            elements.append(Spacer(1, 6))
            
            # AI yanıtını satır satır işle
            ai_response = project.ai_response
            
            # AI yanıtı varsa doğru formatta mı kontrol et
            if "Ay 1:" in ai_response:
                lines = ai_response.split('\n')
                current_month = None
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Ay başlıklarını kontrol et (örn: "Ay 1: Literatür Taraması")
                    if line.startswith("Ay ") and ":" in line:
                        current_month = line
                        elements.append(Paragraph(current_month, styles['MonthTitle']))
                    
                    # Görev maddelerini kontrol et
                    elif line.startswith("- "):
                        task = line[2:]  # "- " kısmını kaldır
                        elements.append(Paragraph(f"• {task}", styles['Task']))
                    else:
                        # Diğer satırlar
                        elements.append(Paragraph(line, styles['Normal']))
            else:
                # AI yanıtı doğru formatta değilse, ham haliyle göster
                elements.append(Paragraph("AI Asistanının Önerisi:", styles['Heading3']))
                elements.append(Paragraph(ai_response, styles['Normal']))
        else:
            elements.append(Paragraph("Bu proje için henüz bir plan oluşturulmamıştır.", styles['Italic']))
        
        # ... geri kalan kod ...
        
    except Exception as e:
        logger.error(f"PDF oluşturma hatası: {str(e)}", exc_info=True)  # Tam hata stacktrace ekledim
        return Response(
            {"error": "PDF oluşturulurken bir hata oluştu", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )         

class FundDurationViewSet(viewsets.ModelViewSet):
    queryset = FundDuration.objects.all()
    serializer_class = FundDurationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return FundDuration.objects.all()