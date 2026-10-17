# Deploy Clinic Select to Render (Free)

المشروع موجود على GitHub:
```
https://github.com/habibayoussef235-collab/clinic-select-habiba
```

## الطريقة السريعة (Render)

انقر على الزر التالي:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/habibayoussef235-collab/clinic-select-habiba)

ثم:
1. سجل دخولك على Render بحساب GitHub
2. اختر الاسم: `clinic-select-habiba`
3. اضغط **Create Web Service**
4. انتظر حتى اكتمال البناء (٢-٣ دقائق)

**الرابط النهائي سيكون:**
```
https://clinic-select-habiba.onrender.com
```

## الطريقة اليدوية

1. سجل دخولك على [render.com](https://render.com)
2. اضغط **New +** ثم **Web Service**
3. اربط مستودع `clinic-select-habiba` من GitHub
4. املأ البيانات:
   - **Name:** `clinic-select-habiba`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn wsgi:app`
5. اضغط **Create Web Service**

## ملفات النشر الموجودة

- `requirements.txt` - متطلبات Python
- `Procfile` - أمر التشغيل
- `wsgi.py` - نقطة الدخول للإنتاج
- `render.yaml` - إعدادات Render
- `runtime.txt` - إصدار Python

## ملاحظات

- قاعدة البيانات SQLite ستُنشأ تلقائياً على Render
- البيانات التجريبية (الأطباء + المرضى + المواعيد) ستُضاف عند أول تشغيل
- قد يستغرق التطبيق وقتًا أطول في التحميل عند أول زيارة (الخطة المجانية)
