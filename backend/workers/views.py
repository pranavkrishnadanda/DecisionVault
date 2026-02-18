from django.http import JsonResponse


def base(request):
    """
    Base endpoint for workers module.
    
    Returns module status information.
    """
    return JsonResponse({
        "module": "workers",
        "status": "active",
    })
