from rest_framework import generics, serializers
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """Email + password login; rate-limited per IP."""
    throttle_scope = 'login'


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'role', 'is_staff']


class MeView(generics.RetrieveAPIView):
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user
