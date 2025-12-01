# sistema_analitico/middleware.py
from django.http import HttpResponse


ALLOWED_HEADERS = "Authorization, Content-Type, Api-Key, X-Subdomain"
ALLOWED_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"


class ConsultaInteligenteCorsMiddleware:
    """
    Middleware básico para habilitar CORS en todos los endpoints del backend,
    permitiendo los headers que usa el front (incluido X-Subdomain).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'OPTIONS':
            response = HttpResponse(status=200)
        else:
            response = self.get_response(request)

        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = ALLOWED_HEADERS
        response["Access-Control-Allow-Methods"] = ALLOWED_METHODS
        response["Access-Control-Allow-Credentials"] = "true"

        return response
