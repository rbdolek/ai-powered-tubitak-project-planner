# users/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from rest_framework.authentication import TokenAuthentication
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    ProfileSerializer,
)
from .models import Profile

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import HttpResponse
import logging
logger = logging.getLogger(__name__)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    # logger.info yerine logger.debug kullan
    logger.debug(f"Profil sorgulandı: user={request.user.username}")
    # veya tamamen yorum satırı yap
    # logger.info(f"Profil sorgulandı: user={request.user.username}")
    return Response({...})
@ensure_csrf_cookie
def get_csrf(request):
    """Tarayıcıya csrftoken cookie’si gönderir; 204 No Content döner."""
    return HttpResponse(status=204)
# ---------- Basit oturum işlemleri ---------- #
# users/views.py
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import SessionAuthentication

@csrf_exempt
@api_view(["POST"])
@authentication_classes([])          #  ←  SIFIR authentication → CSRF aranmaz
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(username=username, password=password)
    if user is None:
        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    login(request, user)
    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        "token": token.key,
        "user": UserSerializer(user, context={"request": request}).data,
    })



@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    # Token tabanlı kimlik doğrulama kullanıyorsanız token’ı silin
    try:
        request.user.auth_token.delete()
    except (AttributeError, Token.DoesNotExist):
        pass
    logout(request)
    return Response({'success': 'Successfully logged out.'})


# ---------- ViewSet ---------- #
@method_decorator(csrf_exempt, name='dispatch')
class UserViewSet(viewsets.ModelViewSet):
    """
    /api/users/ -> CRUD + ek action’lar
    /api/users/profile/ -> GET, PATCH, PUT   (giriş yapan kullanıcının profili)
    /api/users/upload_profile_picture/ -> POST (profil resmi)
    """
    queryset = User.objects.all()

    authentication_classes = [TokenAuthentication]

    # --- Serializer seçimi --- #
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    # --- İzinler --- #
    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]          # Kayıt herkese açık
        return [IsAuthenticated()]       # Diğer işlemler giriş ister

     # ---------- KAYIT (CREATE) ----------
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=user)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {"user": UserSerializer(user, context={"request": request}).data, "token": token.key},
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    # ---------- PROFİL (GET / PATCH / PUT) ---------- #
    @action(detail=False, methods=['get', 'patch', 'put'], url_path='profile')
    def profile(self, request):
        """
        GET  -> Profil verilerini getir
        PATCH/PUT -> first_name / last_name / email / bio alanlarını güncelle
        """
        user = request.user

        # ----- Sadece görüntüleme ----- #
        if request.method == 'GET':
            return Response(UserSerializer(user).data)

        # ----- Güncelleme ----- #
        user_data = {}
        profile_data = {}

        for key, value in request.data.items():
            if key in ['first_name', 'last_name', 'email']:
                user_data[key] = value
            elif key == 'bio':
                profile_data[key] = value

        # Kullanıcı alanları
        if user_data:
            user_serializer = UserUpdateSerializer(
                user, data=user_data, partial=True
            )
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()

        # Profil alanları
        if profile_data:
            profile, _ = Profile.objects.get_or_create(user=user)
            profile_serializer = ProfileSerializer(
                profile, data=profile_data, partial=True
            )
            profile_serializer.is_valid(raise_exception=True)
            profile_serializer.save()

        # -------------- BURASI YENİ --------------
        return Response(
            UserSerializer(user, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    # ---------- PROFİL RESMİ ---------- #
    @action(detail=False, methods=['post'], url_path='upload_profile_picture')
    def upload_profile_picture(self, request):
        """Profil resmi yükle"""
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.profile_picture = request.FILES['file']
        profile.save()

        return Response({'url': request.build_absolute_uri(profile.profile_picture.url)})
