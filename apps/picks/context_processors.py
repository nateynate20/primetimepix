from .models import League

def user_leagues(request):
    if request.user.is_authenticated:
        leagues = League.objects.filter(is_approved=True, members=request.user)
        return {'user_leagues': leagues}
    return {'user_leagues': []}
