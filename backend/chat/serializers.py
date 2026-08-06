from rest_framework import serializers
from .models import ChatSession, ChatMessage

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'session', 'is_user', 'content', 'timestamp']
        read_only_fields = ['id', 'timestamp']

class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatSession
        fields = ['id', 'user', 'ai_model', 'title', 'is_active', 'created_at', 'updated_at', 'messages']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

        extra_kwargs = {
            "title":     {"required": False, "allow_blank": True},
            "ai_model":  {"required": False},
            "is_active": {"required": False},
        }


class ChatSessionListSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()
    first_message = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatSession
        fields = ['id', 'title', 'created_at', 'updated_at', 'ai_model', 'message_count', 'first_message']
    
    def get_message_count(self, obj):
        return obj.messages.count()
    
    def get_first_message(self, obj):
        # İlk kullanıcı mesajını getir
        first_user_message = obj.messages.filter(is_user=True).order_by('timestamp').first()
        if first_user_message:
            return first_user_message.content
        return ""
    

