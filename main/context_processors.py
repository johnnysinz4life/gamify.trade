from django.conf import settings


def google_fonts(request):
    return {
        'GOOGLE_FONTS': getattr(settings, 'GOOGLE_FONTS', []),
        'PRIMARY_GOOGLE_FONT': getattr(settings, 'GOOGLE_FONTS', ['Inter'])[0],
    }
