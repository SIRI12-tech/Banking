from django.utils.deprecation import MiddlewareMixin
from django.middleware.csrf import get_token

class EnsureCsrfCookie(MiddlewareMixin):
    def process_response(self, request, response):
        if not request.COOKIES.get('csrftoken'):
            get_token(request)
        return response