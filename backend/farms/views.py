import hashlib
import os

from django.conf import settings
from django.http import FileResponse
from rest_framework import generics, mixins, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Farm, Field, Measurement, Result
from .serializers import (
    FarmSerializer, FieldSerializer, MeasurementSerializer, RegisterSerializer, ResultSerializer,
)


class RegisterView(generics.CreateAPIView):
    """Sign up. The only endpoint open to people who are not logged in."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class FieldViewSet(viewsets.ModelViewSet):
    """List, create, edit and delete the logged-in user's fields."""

    serializer_class = FieldSerializer

    def get_queryset(self):
        # Golden rule: only this user's fields exist as far as they can tell.
        return Field.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class MeasurementViewSet(viewsets.ReadOnlyModelViewSet):
    """Read the weather measurements of the logged-in user's fields."""

    serializer_class = MeasurementSerializer

    def get_queryset(self):
        return Measurement.objects.filter(field__owner=self.request.user)


class ResultViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Save and read back the logged-in user's plans. Saved plans are not edited."""

    serializer_class = ResultSerializer

    def get_queryset(self):
        return Result.objects.filter(field__owner=self.request.user).order_by('-created_at')


class FarmViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Create (with its fields), read and edit (name, soil, crops, place) the logged-in user's farms."""

    serializer_class = FarmSerializer

    def get_queryset(self):
        return Farm.objects.filter(owner=self.request.user).prefetch_related('parcels').order_by('created_at')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


TTS_MODEL, TTS_VOICE, TTS_MAX_CHARS = 'gpt-4o-mini-tts', 'onyx', 4000
TTS_INSTRUCTIONS = {
    'ar': ('Speak Moroccan Darija (Moroccan Arabic), as a farmer from the Saiss region would. Calm, warm and '
           'reassuring, like a trusted local agricultural advisor. Slow, clear and steady; brief pauses at line breaks.'),
    'fr': ('Parle français avec un léger accent marocain naturel. Calme, chaleureux et rassurant, comme un conseiller '
           'agricole qui parle à un agriculteur. Lent, clair, posé ; courtes pauses aux retours à la ligne.'),
    'en': ('Calm, warm and reassuring, like a trusted local agricultural advisor talking to a farmer. '
           'Slow, clear and steady; brief pauses at line breaks.'),
}


def _tts_error(code, status):
    return Response({'error': {'code': code, 'message': 'Text-to-speech is not available.'}}, status=status)


class TTSView(APIView):
    """Reads a text aloud with OpenAI text-to-speech (the key stays on the server).

    Logged-in users only. Each (language, text) is generated once and cached on disk.
    """

    def post(self, request):
        text = str(request.data.get('text', '')).strip()
        lang = request.data.get('lang')
        if lang not in TTS_INSTRUCTIONS or not text or len(text) > TTS_MAX_CHARS:
            return _tts_error('invalid_request', 400)
        key = os.environ.get('OPENAI_API_KEY')
        if not key:
            return _tts_error('tts_unavailable', 503)
        digest = hashlib.sha256(f'{TTS_MODEL}|{TTS_VOICE}|{lang}|{text}'.encode()).hexdigest()
        cache = settings.BASE_DIR / 'tts_cache'
        path = cache / f'{digest}.mp3'
        if not path.exists():
            from openai import OpenAI
            cache.mkdir(exist_ok=True)
            tmp = path.with_suffix('.part')
            try:
                with OpenAI(api_key=key).audio.speech.with_streaming_response.create(
                    model=TTS_MODEL, voice=TTS_VOICE, input=text,
                    instructions=TTS_INSTRUCTIONS[lang], response_format='mp3',
                ) as response:
                    response.stream_to_file(tmp)
                tmp.replace(path)
            except Exception:  # network, quota or key problem: the app falls back to other voices
                tmp.unlink(missing_ok=True)
                return _tts_error('tts_unavailable', 503)
        return FileResponse(open(path, 'rb'), content_type='audio/mpeg')
