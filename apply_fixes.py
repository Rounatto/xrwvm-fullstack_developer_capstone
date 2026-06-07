import os

ROOT = os.path.dirname(os.path.abspath(__file__))

files = {}

# ── main.yml ─────────────────────────────────────────────────────────────────
files[".github/workflows/main.yml"] = """\
name: 'Lint Code'

on:
  push:
    branches: [master, main]
  pull_request:
    branches: [master, main]

jobs:
  lint_python:
    name: Lint Python Files
    runs-on: ubuntu-latest

    steps:
    - name: Checkout Repository
      uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.12

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install flake8

    - name: Run Linter
      run: |
        find . -name "*.py" -not -path "*/migrations/*" -exec flake8 --max-line-length=120 {} +
        echo "Linted all the python files successfully"

  lint_js:
    name: Lint JavaScript Files
    runs-on: ubuntu-latest

    steps:
    - name: Checkout Repository
      uses: actions/checkout@v3

    - name: Install Node.js
      uses: actions/setup-node@v3
      with:
        node-version: 18

    - name: Install JSHint
      run: npm install jshint --global

    - name: Run Linter
      run: |
        find ./server/database -name "*.js" -exec jshint {} +
        echo "Linted all the js files successfully"
"""

# ── admin.py ─────────────────────────────────────────────────────────────────
files["server/djangoapp/admin.py"] = """\
from django.contrib import admin
from .models import CarMake, CarModel


class CarModelInline(admin.TabularInline):
    model = CarModel
    extra = 1


@admin.register(CarModel)
class CarModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'car_make', 'dealer_id', 'type', 'year')
    list_filter = ('car_make', 'type', 'year')
    search_fields = ('name', 'car_make__name')


@admin.register(CarMake)
class CarMakeAdmin(admin.ModelAdmin):
    inlines = [CarModelInline]
    list_display = ('name', 'description')
    search_fields = ('name',)
"""

# ── views.py ──────────────────────────────────────────────────────────────────
files["server/djangoapp/views.py"] = """\
from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.http import JsonResponse
from django.contrib.auth import login, authenticate
import logging
import json
from django.views.decorators.csrf import csrf_exempt
from .models import CarMake, CarModel
from .populate import initiate
from .restapis import get_request, analyze_review_sentiments, post_review


# Get an instance of a logger
logger = logging.getLogger(__name__)


# Create your views here.
def get_cars(request):
    count = CarMake.objects.filter().count()
    print(count)
    if count == 0:
        initiate()
    car_models = CarModel.objects.select_related('car_make')
    cars = []
    for car_model in car_models:
        cars.append({"CarModel": car_model.name, "CarMake": car_model.car_make.name})
    return JsonResponse({"CarModels": cars})


@csrf_exempt
def login_user(request):
    # Get username and password from request.POST dictionary
    data = json.loads(request.body)
    username = data['userName']
    password = data['password']
    # Try to check if provide credential can be authenticated
    user = authenticate(username=username, password=password)
    data = {"userName": username}
    if user is not None:
        # If user is valid, call login method to login current user
        login(request, user)
        data = {"userName": username, "status": "Authenticated"}
    return JsonResponse(data)


def logout_request(request):
    logout(request)
    return JsonResponse({"logged_out": True})


@csrf_exempt
def registration(request):
    if request.method == 'GET':
        return render(request, 'index.html')

    # Load JSON data from the request body
    data = json.loads(request.body)
    username = data['userName']
    password = data['password']
    first_name = data['firstName']
    last_name = data['lastName']
    email = data['email']
    username_exist = False
    try:
        # Check if user already exists
        User.objects.get(username=username)
        username_exist = True
    except Exception:
        # If not, simply log this is a new user
        logger.debug("{} is new user".format(username))

    # If it is a new user
    if not username_exist:
        # Create user in auth_user table
        user = User.objects.create_user(
            username=username, first_name=first_name,
            last_name=last_name, password=password, email=email)
        # Login the user and redirect to list page
        login(request, user)
        data = {"userName": username, "status": "Authenticated"}
        return JsonResponse(data)
    else:
        data = {"userName": username, "error": "Already Registered"}
        return JsonResponse(data)


# Update the `get_dealerships` render list of dealerships all by default, particular state if state is passed
def get_dealerships(request, state="All"):
    if state == "All":
        endpoint = "/fetchDealers"
    else:
        endpoint = "/fetchDealers/" + state
    dealerships = get_request(endpoint)
    return JsonResponse({"status": 200, "dealers": dealerships})


def get_dealer_reviews(request, dealer_id):
    # if dealer id has been provided
    if dealer_id:
        endpoint = "/fetchReviews/dealer/" + str(dealer_id)
        reviews = get_request(endpoint)
        for review_detail in reviews:
            response = analyze_review_sentiments(review_detail['review'])
            print(response)
            review_detail['sentiment'] = response['sentiment']
        return JsonResponse({"status": 200, "reviews": reviews})
    else:
        return JsonResponse({"status": 400, "message": "Bad Request"})


def get_dealer_details(request, dealer_id):
    if dealer_id:
        endpoint = "/fetchDealer/" + str(dealer_id)
        dealership = get_request(endpoint)
        return JsonResponse({"status": 200, "dealer": dealership})
    else:
        return JsonResponse({"status": 400, "message": "Bad Request"})


def add_review(request):
    if not request.user.is_anonymous:
        data = json.loads(request.body)
        try:
            post_review(data)
            return JsonResponse({"status": 200})
        except Exception:
            return JsonResponse({"status": 401, "message": "Error in posting review"})
    else:
        return JsonResponse({"status": 403, "message": "Unauthorized"})
"""

# ── populate.py ───────────────────────────────────────────────────────────────
files["server/djangoapp/populate.py"] = """\
from .models import CarMake, CarModel


def initiate():
    car_make_data = [
        {"name": "NISSAN", "description": "Great cars. Japanese technology"},
        {"name": "Mercedes", "description": "Great cars. German technology"},
        {"name": "Audi", "description": "Great cars. German technology"},
        {"name": "Kia", "description": "Great cars. Korean technology"},
        {"name": "Toyota", "description": "Great cars. Japanese technology"},
    ]

    car_make_instances = []
    for data in car_make_data:
        car_make_instances.append(CarMake.objects.create(name=data['name'], description=data['description']))

    # Create CarModel instances with the corresponding CarMake instances
    car_model_data = [
        {"name": "Pathfinder", "type": "SUV", "year": 2023, "car_make": car_make_instances[0]},
        {"name": "Qashqai", "type": "SUV", "year": 2023, "car_make": car_make_instances[0]},
        {"name": "XTRAIL", "type": "SUV", "year": 2023, "car_make": car_make_instances[0]},
        {"name": "A-Class", "type": "SUV", "year": 2023, "car_make": car_make_instances[1]},
        {"name": "C-Class", "type": "SUV", "year": 2023, "car_make": car_make_instances[1]},
        {"name": "E-Class", "type": "SUV", "year": 2023, "car_make": car_make_instances[1]},
        {"name": "A4", "type": "SUV", "year": 2023, "car_make": car_make_instances[2]},
        {"name": "A5", "type": "SUV", "year": 2023, "car_make": car_make_instances[2]},
        {"name": "A6", "type": "SUV", "year": 2023, "car_make": car_make_instances[2]},
        {"name": "Sorrento", "type": "SUV", "year": 2023, "car_make": car_make_instances[3]},
        {"name": "Carnival", "type": "SUV", "year": 2023, "car_make": car_make_instances[3]},
        {"name": "Cerato", "type": "Sedan", "year": 2023, "car_make": car_make_instances[3]},
        {"name": "Corolla", "type": "Sedan", "year": 2023, "car_make": car_make_instances[4]},
        {"name": "Camry", "type": "Sedan", "year": 2023, "car_make": car_make_instances[4]},
        {"name": "Kluger", "type": "SUV", "year": 2023, "car_make": car_make_instances[4]},
    ]

    for data in car_model_data:
        CarModel.objects.create(name=data['name'], car_make=data['car_make'], type=data['type'], year=data['year'])
"""

# ── restapis.py ───────────────────────────────────────────────────────────────
files["server/djangoapp/restapis.py"] = """\
import requests
import os
from dotenv import load_dotenv

load_dotenv()

backend_url = os.getenv(
    'backend_url', default="http://localhost:3030")
sentiment_analyzer_url = os.getenv(
    'sentiment_analyzer_url',
    default="http://localhost:5050/")


def get_request(endpoint, **kwargs):
    params = ""
    if kwargs:
        for key, value in kwargs.items():
            params = params + key + "=" + value + "&"

    request_url = backend_url + endpoint + "?" + params

    print("GET from {} ".format(request_url))
    try:
        # Call get method of requests library with URL and parameters
        response = requests.get(request_url)
        return response.json()
    except Exception:
        # If any error occurs
        print("Network exception occurred")


def analyze_review_sentiments(text):
    request_url = sentiment_analyzer_url + "analyze/" + text
    try:
        # Call get method of requests library with URL and parameters
        response = requests.get(request_url)
        return response.json()
    except Exception as err:
        print(f"Unexpected {err=}, {type(err)=}")
        print("Network exception occurred")


def post_review(data_dict):
    request_url = backend_url + "/insert_review"
    try:
        response = requests.post(request_url, json=data_dict)
        print(response.json())
        return response.json()
    except Exception:
        print("Network exception occurred")
"""

# ── settings.py (patch only the DIRS block + strip trailing newline) ──────────
settings_path = os.path.join(ROOT, "server/djangoproj/settings.py")
if os.path.exists(settings_path):
    with open(settings_path, "r", encoding="utf-8") as f:
        s = f.read()
    old = (
        "        'DIRS': [os.path.join(BASE_DIR, 'frontend/static'),\n"
        "                os.path.join(BASE_DIR, 'frontend/build'),\n"
        "                os.path.join(BASE_DIR, 'frontend/build/static')],"
    )
    new = (
        "        'DIRS': [\n"
        "            os.path.join(BASE_DIR, 'frontend/static'),\n"
        "            os.path.join(BASE_DIR, 'frontend/build'),\n"
        "            os.path.join(BASE_DIR, 'frontend/build/static'),\n"
        "        ],"
    )
    s = s.replace(old, new).rstrip("\n") + "\n"
    with open(settings_path, "w", encoding="utf-8") as f:
        f.write(s)
    print("  fixed: server/djangoproj/settings.py")

# ── djangoproj/urls.py (spaces after commas) ──────────────────────────────────
urls_path = os.path.join(ROOT, "server/djangoproj/urls.py")
if os.path.exists(urls_path):
    with open(urls_path, "r", encoding="utf-8") as f:
        u = f.read()
    u = u.replace(
        "path('dealer/<int:dealer_id>',TemplateView",
        "path('dealer/<int:dealer_id>', TemplateView"
    ).replace(
        "path('postreview/<int:dealer_id>',TemplateView",
        "path('postreview/<int:dealer_id>', TemplateView"
    )
    with open(urls_path, "w", encoding="utf-8") as f:
        f.write(u)
    print("  fixed: server/djangoproj/urls.py")

# ── Write all full-replacement files ─────────────────────────────────────────
for rel_path, content in files.items():
    full_path = os.path.join(ROOT, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print(f"  fixed: {rel_path}")

# ── models.py / models_updated.py — ensure single trailing newline ─────────────
for rel in ["server/djangoapp/models.py", "server/djangoapp/models_updated.py"]:
    p = os.path.join(ROOT, rel)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            txt = f.read()
        txt = txt.rstrip("\n") + "\n"
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt)
        print(f"  fixed: {rel}")

print("\n✅ Tous les fichiers corrigés !")
print("\n👉 Maintenant tape ces 3 commandes :")
print('   git add -A')
print('   git commit -m "fix: resolve flake8 errors and update CI workflow"')
print('   git push')
