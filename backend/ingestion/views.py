from django.http import JsonResponse


def base(request):
    """
    Base endpoint for ingestion module.
    
    Returns module status information.
    """
    return JsonResponse({
        "module": "ingestion",
        "status": "active",
    })
