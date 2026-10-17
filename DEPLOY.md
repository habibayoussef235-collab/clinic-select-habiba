# Deploy Clinic Select to Render (Free)

## الطريقة السريعة (GitHub + Render)

### 1. رفع المشروع على GitHub

```bash
# داخل مجلد clinic-select
git init
git add .
git commit -m "Initial commit: Clinic Select with auth, demo data, reports"
git branch -M main

# أنشئ مستودعاً على GitHub ثم اربطه:
git remote add origin https://github.com/YOUR_USERNAME/clinic-select.git
git push -u origin main
```

### 2. النشر على Render

1. سجل دخولك على [render.com](https://render.com) بحساب GitHub
2. اضغط **New +** ثم اختر **Web Service**
3. اربط مستودع `clinic-select` من GitHub
4. املأ البيانات:
   - **Name:** clinic-select
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn wsgi:app`
5. اضغط **Create Web Service**
6. بعد اكتمال البناء، ستحصل على رابط مثل:
   ```
   https://clinic-select.onrender.com
   ```

## ملفات النشر الموجودة

- `requirements.txt` - متطلبات Python
- `Procfile` - أمر التشغيل
- `wsgi.py` - نقطة الدخول للإنتاج
- `render.yaml` - إعدادات Render (اختياري)
- `runtime.txt` - إصدار Python

## ملاحظات

- قاعدة البيانات SQLite ستُنشأ تلقائياً على Render
- البيانات التجريبية (الأطباء + المرضى + المواعيد) ستُضاف عند أول تشغيل
- لاستخدام قاعدة بيانات دائمة، يمكنك ترقية Render لإضافة PostgreSQL
