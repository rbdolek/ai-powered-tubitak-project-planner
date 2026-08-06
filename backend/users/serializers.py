# users/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile


# ---------- Profil ---------- #
# users/serializers.py
class ProfileSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model  = Profile
        fields = ["bio", "profile_picture"]

    def get_profile_picture(self, obj):
        request = self.context.get("request")  # None olabilir
        if obj.profile_picture:
            if request is not None:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url      # fallback: relatif yol
        # varsayılan avatar
        default_path = "/static/images/default_avatar.png"
        if request is not None:
            return request.build_absolute_uri(default_path)
        return default_path


# ---------- Genel Kullanıcı Görünümü ---------- #
class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(required=False)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'profile',
            'is_active',
            'date_joined',
        ]
        read_only_fields = ['id', 'date_joined', 'is_active']


# ---------- Kayıt ---------- #
class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.is_active = True
        user.save()
        return user


# ---------- Güncelleme ---------- #
class UserUpdateSerializer(serializers.ModelSerializer):
    # `bio` doğrudan User modelinde olmadığı için ekstra alan
    bio = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'bio']

    def update(self, instance, validated_data):
        bio = validated_data.pop('bio', None)

        # Kullanıcı alanlarını güncelle
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Profil güncelle
        if bio is not None:
            profile, _ = Profile.objects.get_or_create(user=instance)
            profile.bio = bio
            profile.save()

        return instance
