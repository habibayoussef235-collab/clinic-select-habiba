# Deploy Clinic Select

المشروع موجود على GitHub:
```
https://github.com/habibayoussef235-collab/clinic-select-habiba
```

## النشر على Vercel (مجاني - لا يحتاج بطاقة ائتمان)

### الطريقة السريعة

انقر على الزر:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/habibayoussef235-collab/clinic-select-habiba&project-name=clinic-select-habiba&repo-name=clinic-select-habiba)

ثم اتبع الخطوات:
1. سجل دخولك على Vercel بحساب GitHub
2. سيكشف Vercel تلقائياً عن ملف `vercel.json`
3. اضغط **Deploy**
4. انتظر حتى اكتمال البناء (١-٢ دقيقة)

**الرابط النهائي:**
```
https://clinic-select-habiba.vercel.app
```

### ملاحظة مهمة
Vercel يستخدم بيئة serverless. قاعدة البيانات SQLite تُحفظ في `/tmp` وهي مؤقتة (قد تُمسح بين عمليات التشغيل). للاستخدام الحقيقي على Vercel، يُنصح بربط قاعدة بيانات خارجية (مثل PostgreSQL أو Supabase).

## النشر على Render

انقر على الزر:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/habibayoussef235-collab/clinic-select-habiba)

**الرابط النهائي:**
```
https://clinic-select-habiba.onrender.com
```

Render يحافظ على قاعدة البيانات SQLite بشكل أفضل من Vercel.
