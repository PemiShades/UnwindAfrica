from django.shortcuts import render

# Create your views here.
def home(request):
	return render(request, 'Web/home.html', context={})

def about(request):
	return render(request, 'Web/about.html', context={})

def packages(request):
	return render(request, 'Web/packages.html', context={})

def custom_404(request, exception):
    return render(request, '404.html', status=404)
