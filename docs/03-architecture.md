# معماری و الگوها

## انتخاب: مونولیت ماژولار با معماری لایه‌ای سبک
یک برنامه و یک دیتابیس؛ قابلیت‌ها مرز مشخص دارند. هدف این نیست که برای هر تابع interface بسازیم. ابزار خارجی باید قابل تعویض و منطق کاربردی قابل تست باشد.

```text
Web UI → API Router → Application Service → قواعد دامنه
                              ↓
                    Repository / Adapter
                              ↓
               SQLite / Filesystem / Aria2 / Websites
```

## ساختار پیشنهادی؛ نه کد پیاده‌سازی‌شده
```text
app/
  main.py
  bootstrap.py
  core/
    config.py
    database.py
    errors.py
    logging.py
  modules/
    library/
    sources/
    personal/
    metadata/
    integrations/
    downloads/
    playback/
  adapters/
    aria2/
    zarfilm/
    letterboxd/
    metadata_providers/
  jobs/
    runner.py
    handlers.py
tests/
  unit/
  integration/
  architecture/
migrations/
docs/
```

داخل ماژول‌ها، فقط در صورت نیاز `router.py`، `schemas.py`، `service.py`، `models.py` و `repository.py` ایجاد شود. کتابخانه مالک هویت فیلم و نسخه‌های آن، sources مالک منابع و اسکن، personal مالک دادهٔ تماشا، downloads مالک صف و چرخهٔ دانلود است. integrations هماهنگ‌کنندهٔ ورود دادهٔ شخصی است؛ Adapter فقط ارتباط با منبع خارجی را می‌داند.

## الگوها و کاربرد
- **Service Layer:** عملیات کاربر و هماهنگی قواعد؛ افزودن منبع، اصلاح تطبیق، ثبت تماشا و ورود فایل دانلودشده.
- **Repository:** پرس‌وجوهای معنادار و persistence؛ نه GenericRepository بزرگ. به‌عنوان نمونه `find_by_external_id` و `find_by_source_and_path`.
- **Adapter / قرارداد کوچک:** Aria2، مرورگر سایت، metadata، فایل‌سیستم یا پلیر در مرز وابستگی خارجی. قرارداد در سمت مصرف‌کننده تعریف شود؛ اجرای آن در adapters.
- **State Machine سبک:** enum و قواعد انتقال برای Job و Download؛ کتابخانهٔ ویژه لازم نیست.
- **Dependency Injection ساده:** ساخت وابستگی‌ها در bootstrap و اتصال به FastAPI؛ container پیچیده لازم نیست.

## قواعد وابستگی
- Router منطق کسب‌وکار یا SQL ندارد؛ Repository وب، مرورگر یا دانلود را مدیریت نمی‌کند.
- Service به Request/Response فریم‌ورک وابسته نباشد.
- قراردادهای API/Pydantic را با مدل ذخیره‌سازی/SQLAlchemy یکی نکنید؛ ORM object مستقیماً پاسخ عمومی نباشد.
- دسترسی بین ماژول‌ها از سرویس یا قرارداد عمومی؛ نوشتن مستقیم در جدول تحت مالکیت ماژول دیگر ممنوع، مگر همکاری صریح و مستند.
- لایهٔ قواعد خالص به FastAPI، ORM و DrissionPage وابسته نباشد. این به معنی اجبار به ساخت مدل دامنهٔ مجزا برای هر جدول نیست.
- core فقط زیرساخت واقعاً مشترک؛ business logic را آنجا انبار نکنید.
- import نباید مرورگر، thread، daemon یا اتصال شبکه راه بیندازد. startup/shutdown صریح باشند.
- یک چرخهٔ عمر مشخص برای DB session؛ یک session میان threadها به اشتراک گذاشته نشود.

## تراکنش
مرز عملیات کاربردی در Service است؛ Repositoryها نباید هر کدام خودسرانه commit کنند. چند تغییر مرتبط تا حد ممکن یک تراکنش کوتاه باشند. عملیات شبکه و مرورگر بیرون تراکنش؛ نتیجه در تراکنش کوتاه ذخیره شود. SQLAlchemy Session می‌تواند نقش Unit of Work سبک را داشته باشد؛ abstraction اضافه فقط با نیاز واقعی.

## چیزهایی که فعلاً نمی‌سازیم
Microservices، Redis/Celery، CQRS کامل، Event Sourcing، Event Bus عمومی و DDD سنگین. API و job runner هم‌اکنون می‌توانند در یک پردازش باشند؛ مرز منطقی‌شان امکان جداسازی آینده را حفظ کند.
