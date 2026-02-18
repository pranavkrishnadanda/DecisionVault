import json
from django.http import JsonResponse


def health(request):
    """
    Health check endpoint for load balancers and monitoring.
    
    Returns:
        JSON response with status and version information.
    """
    return JsonResponse({
        "status": "ok",
        "version": "0.1.0",
    })
