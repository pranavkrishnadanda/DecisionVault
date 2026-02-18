from django.http import JsonResponse


def base(request):
    """
    Base endpoint for verification module.
    
    Returns module status information.
    """
    return JsonResponse({
        "module": "verification",
        "status": "active",
    })
