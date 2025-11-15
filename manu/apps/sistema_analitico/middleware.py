# sistema_analitico/middleware.py
class ConsultaInteligenteCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # SOLO para consulta inteligente permitir CORS
        if request.path == '/api/consulta-natural/pregunta_inteligente/':
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Headers"] = "API-Key, Content-Type"
            response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        
        return response