## Development Notes


### Developing Vue.js Frontend


Add the following lines **before** `MIDDLEWARE` section in `settings.py`:

```python
if DEBUG:
    INSTALLED_APPS.append('corsheaders')
```

Add the following lines **after** `MIDDLEWARE` section in `settings.py`:

```python
if DEBUG:
    MIDDLEWARE.insert(2, 'corsheaders.middleware.CorsMiddleware')
    MIDDLEWARE.insert(2, 'corsheaders.middleware.CorsMiddleware')

    CORS_ALLOWED_ORIGINS = [
        "http://localhost:5173",
    ]
    CORS_ALLOW_ALL_ORIGINS = True
    CSRF_TRUSTED_ORIGINS = [
    ]
    CORS_ALLOW_CREDENTIALS = True
```

Add the following line to `requirements.txt`:

```
django-cors-headers==3.11.0
```

Or you can apply the following patch:

```
diff --git a/kelvin/settings.py b/kelvin/settings.py
index 7febe5f..388aba5 100644
--- a/kelvin/settings.py
+++ b/kelvin/settings.py
@@ -48,6 +48,9 @@ INSTALLED_APPS = [
     'webpush',
 ]
 
+if DEBUG:
+    INSTALLED_APPS.append('corsheaders')
+
 MIDDLEWARE = [
     'django.middleware.security.SecurityMiddleware',
     'django.contrib.sessions.middleware.SessionMiddleware',
@@ -60,6 +63,19 @@ MIDDLEWARE = [
     'django_cas_ng.middleware.CASMiddleware',
 ]
 
+if DEBUG:
+    MIDDLEWARE.insert(2, 'corsheaders.middleware.CorsMiddleware')
+
+    CORS_ALLOWED_ORIGINS = [
+        "http://localhost:5173",
+    ]
+    CORS_ALLOW_ALL_ORIGINS = True
+    CSRF_TRUSTED_ORIGINS = [
+        'www.safesite.com',
+    ]
+    CORS_ALLOW_CREDENTIALS = True
+
+
 ROOT_URLCONF = 'kelvin.urls'
 
 TEMPLATES = [
diff --git a/requirements.txt b/requirements.txt
index 073b20c..6022af2 100644
--- a/requirements.txt
+++ b/requirements.txt
@@ -30,3 +30,4 @@ rq-scheduler==0.11.0
 six==1.16.0
 typing_extensions==4.11.0
 Unidecode==1.3.6
+django-cors-headers==3.11.0
```
