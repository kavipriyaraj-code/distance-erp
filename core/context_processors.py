def global_context(request):
    context = {}
    if request.user.is_authenticated:
        context['current_user'] = request.user
        context['user_role'] = request.user.get_role_display()
    return context
