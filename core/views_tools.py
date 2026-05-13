from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def calcolatrice_view(request):
    return render(request, 'core/calcolatrice.html')
