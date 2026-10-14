# 🎬 CinemaShelf

**CinemaShelf** یک کتابخانهٔ شخصی و محلی (Local-First) برای مدیریت آرشیو فیلم‌ها روی چند پوشه و هارد اکسترنال، ثبت وضعیت تماشا و امتیاز شخصی، همگام‌سازی با Letterboxd و مدیریت هوشمند صف دانلود (فوری و شبانه با Aria2) است.

---

## 🚀 راه‌اندازی اولیه و اولین کامیت (Git Init)

پوشهٔ `legacy/` در فایل `.gitignore` قرار گرفته است تا کدهای قدیمی فقط در طول توسعهٔ اولیه به‌عنوان مرجع محلی در دسترس شما و ایجنت‌های برنامه‌نویسی باشند و وارد تاریخچهٔ Git نشوند.

```bash
# ۱. مقداردهی اولیه مخزن گیت
git init

# ۲. بررسی وضعیت (مطمئن شوید پوشه legacy در لیست کامیت نیست)
git status

# ۳. ثبت اولین کامیت (اسکلت معماری، مستندات و راهنمای ایجنت‌ها)
git add .
git commit -m "chore: initial project structure, architecture docs, and agent guidelines"
```

### نصب وابستگی‌ها و اجرای سرور توسعه
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
```

---

## 🤖 کار با ایجنت‌های برنامه‌نویسی (Claude Code / Cursor / OpenCode / Cline)

فایل‌های راهنمای ایجنت در ریشهٔ پروژه قرار دارند:
- `AGENTS.md` (استاندارد عمومی ایجنت‌ها و OpenCode)
- `CLAUDE.md` (مخصوص Claude Code)
- `.cursorrules` (مخصوص Cursor IDE)

برای شروع پیاده‌سازی هر مرحله، کافی است به ایجنت خود بگویید:
> «بر اساس `AGENTS.md` و `docs/09-roadmap-and-acceptance.md`، گام یک (برش انتهابه‌انتهای معرفی Source، اسکن و نمایش MediaFile) را پیاده‌سازی کن.»

---

## 📚 مستندات معماری و طراحی (`docs/`)
1. `docs/01-product-and-scope.md`: اصول محصول و محدوده
2. `docs/02-decisions-and-open-questions.md`: تصمیم‌های فنی و پرسش‌های باز
3. `docs/03-architecture.md`: معماری مونولیت ماژولار و قواعد وابستگی
4. `docs/04-data-model.md`: مدل دادهٔ مفهومی و قواعد هویت فیلم/فایل
5. `docs/05-workflows-and-jobs.md`: جریان‌های اسکن، دانلود و کارهای پس‌زمینه
6. `docs/06-logging-and-errors.md`: استاندارد لاگینگ، کدهای خطا و حریم خصوصی
7. `docs/07-development-rules.md`: قراردادهای کدنویسی و تست
8. `docs/08-adding-a-feature.md`: گام‌های افزودن قابلیت جدید
9. `docs/09-roadmap-and-acceptance.md`: نقشهٔ راه و معیارهای پذیرش
10. `docs/10-legacy-code-map.md`: راهنمای برداشت منطق از کدهای قدیمی داخل `legacy/`
