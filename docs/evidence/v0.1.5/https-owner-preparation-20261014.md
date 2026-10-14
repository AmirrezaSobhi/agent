# HTTPS و آماده‌سازی Release Owner — ۲۰۲۶-۱۰-۱۴

**انتشار هنوز BLOCKED است: Approval واقعی مالک محصول ثبت نشده است.**

## مجوز و CA

مالک محصول تغییر external_url/Nginx، ایجاد و نگهداری امن کلید خصوصی و Trust
محدود میزبان‌های پروژه را صریحاً مجاز کرد. پس از بررسی فقط‌خواندنی، CA/Server
Certificate اختصاصیِ قابل استفاده در مسیرهای بررسی‌شدهٔ GitLab و Ubuntu پیدا
نشد؛ Root/CA Store دو Windows Runner نیز نامزد مرتبط نداشت.

Root CA جدید با کلید RSA 4096 رمزگذاری‌شده (AES-256) و دسترسی root-only آماده
شد. Certificate Server جداگانه RSA 3072، CA:false و EKU=serverAuth دارد؛
self-signed leaf استفاده نشد. Root دارای pathlen:0 و Name Constraints بحرانی
برای DNS gitlab.local و منع IP است. Root key، passphrase و Server key هرگز
به Git، خروجی ابزار یا Artifact منتقل نشدند.

مالک محصول Fingerprint واقعی زیر را پیش از Trust تأیید کرد:

`1B:B0:2C:33:87:F7:2A:E5:9C:6E:44:AD:FF:E7:18:35:1C:7F:1D:AA:65:01:76:4A:85:67:B8:11:6F:37:B5:7B`

| مشخصه | Root CA | Server |
|---|---|---|
| Subject CN | MT5Agent GitLab Local Root CA 2026 | gitlab.local |
| Issuer CN | MT5Agent GitLab Local Root CA 2026 | MT5Agent GitLab Local Root CA 2026 |
| O | MT5Agent Internal Project | MT5Agent Internal Project |
| Not Before UTC | 2026-10-14 05:36:16 | 2026-10-14 05:36:16 |
| Not After UTC | 2029-10-13 05:36:16 | 2027-11-15 05:36:16 |
| SAN | Root CA؛ SAN لازم نیست | DNS:gitlab.local |
| SHA-256 | Fingerprint تأییدشدهٔ بالا | EF:20:57:C0:4C:9F:6F:06:5D:2F:72:FE:ED:4B:26:53:7F:12:12:D0:BB:38:E1:61:78:59:6D:E6:A6:A4:82:56 |

Public Root: `/etc/gitlab/pki/mt5agent-v015/root/root-ca.crt`

Server Certificate: `/etc/gitlab/pki/mt5agent-v015/server/gitlab.local.crt`

Full chain فعال: `/etc/gitlab/ssl/gitlab.local.fullchain.pem`

تطابق Server key، Chain و hostname پیش از اجرا با OpenSSL بررسی شد؛ این
بررسی جایگزین Trust نیست. Trust فقط پس از تأیید Fingerprint انجام شد.

## تغییر و Rollback

Backup خصوصیِ تنظیم قبلی روی gitlab-master:
`/var/backups/mt5agent-https/20261014T054517Z/`

external_url به `https://gitlab.local` تغییر کرد؛ HTTP به HTTPS هدایت می‌شود؛
Let’s Encrypt غیرفعال، TLS 1.2/1.3 فعال و SSH port 2222 حفظ شد.
`gitlab-ctl reconfigure` Exit 0 داشت، از UTC 05:45:17 تا 05:45:51.
مدت دستور، اندازه‌گیری کامل downtime نیست. Rollback: بازیابی gitlab.rb از
Backup خصوصی و reconfigure؛ داده‌های GitLab/VM یا MT5 تغییر نمی‌کنند.

Trust روی mani-pc، gitlab-master، win10-runner و win10-mt5-runner اعمال شد؛
win10-installer-test نیازی نداشت و تغییر نکرد. روی Ubuntu، دسترسی sudo تعاملی
لازم بود؛ مالک محصول Script آماده را اجرا و APPLIED / curl HTTP 200 / Runner
verify معتبر را گزارش کرد. Probe مستقل Python سپس با Trust پیش‌فرض OS نیز
PASS، TLSv1.3 و API status 401 بدون Token گزارش کرد.

دو Windows Runner Root تأییدشده را در LocalMachine/Root دریافت کردند؛
Fingerprint در هر مقصد مطابق بود. URL Runnerها HTTPS و tls-ca-file اختصاصی
شد. Backup config حاوی Token فقط در Directory محدود SYSTEM/Administrators
نگهداری شد. مسیر TOML ابتدا escape نامعتبر داشت و Runnerها موقتاً شروع
نشدند؛ مسیر به `C:/GitLab-Runner/certs/gitlab.local.crt` اصلاح شد. هر دو Runner
Running و verify Exit 0 / is valid شدند. هیچ Token چاپ یا Rotate نشد.

HTTPS/API از Windows با Chain/Hostname Verification معمولی و پاسخ 401
بدون Token PASS شد؛ Git SSH ls-remote پس از تغییر موفق بود. نتیجهٔ Pipeline
واقعی پس از HTTPS، در GitLab و آرشیو شواهد ثبت می‌شود؛ نتیجهٔ آن پیشاپیش
PASS اعلام نمی‌شود. هیچ --insecure، verify=false یا Certificate callback
استفاده نشد.

## هویت و نگهداری Approval

فقط root/ID 1 و GitLabDuo bot/ID 2 قبلاً وجود داشتند. با مجوز مشخص و ایمیل
واقعیِ ارائه‌شده توسط مالک محصول، `release-owner` با **ID 3** ساخته شد:
Human، non-admin، External، عضویت **Developer 30** فقط در پروژه، Projects
limit 0 و الزام تغییر رمز در ورود اول. Bootstrap تا ورود و تغییر رمز مالک
محصول، به معنی تحویل نهایی کنترل حساب نیست. خطای دسترسی مسیر اولیهٔ
Bootstrap بعد از ایجاد حساب اصلاح شد؛ فقط همان حساب جدیدِ هرگز استفاده‌نشده
تکمیل شد و حساب تکراری ساخته نشد.

رمز موقت در فایل خصوصیِ مالک mani با permission 0600 قرار دارد:
`/home/mani/.local/share/MT5Agent/release-owner/activation.json`

این فایل Secret است؛ نباید در Chat، Git یا Artifact کپی شود. حساب Codex/CI
به‌جای Owner Login یا Approve نکرده است.

Reader مستقل: Project token / Bot ID 4، **Reporter 20، فقط read_api**، انقضا
۲۰۲۶-۱۱-۱۳؛ نه Owner است و نه مجاز به Approval. Token فقط در متغیر Protected /
Masked / Hidden ذخیره شد. `MT5_RELEASE_OWNER_USER_ID=3` نیز Protected است.
Authorization/Windows acceptance files تا وجود شواهد واقعیِ دقیقِ Tag ساخته
نمی‌شوند؛ record صوری یا Placeholder معتبر تولید نشد.

### Owner تنها صادرکنندهٔ محتوای تأیید

Developer به تغییر CI variables نیاز ندارد. Owner در مسیر مجاز GitLab MR،
Approval واقعی و یک **Note JSON ویرایش‌نشده** با record دقیق Tag/Commit و
تصمیم ریسک‌ها ثبت می‌کند. Maintainer فقط همان متن را به Protected File حمل
می‌کند و `approval_note_id` تخصیص‌یافته توسط GitLab را به Metadata اضافه می‌کند.
این ID در body نیست، تا self-reference ناممکن ایجاد نشود.

Publisher قبل از هر نوشتن Package/Release:

1. عضویت فعال و مستقل Owner، Approval واقعی و Merge Commit دقیق Main را بررسی می‌کند.
2. Note را با Reader فقط‌خواندنی می‌خواند؛ Author باید ID 3، system=false و
   created_at=updated_at باشد؛ Note ویرایش‌شده رد می‌شود.
3. JSON Note باید با کل Protected record، به‌جز Metadata note ID، عیناً مطابق باشد.
4. Risk KI-009 و همهٔ risk dispositions باید در همان متن واقعاً تأییدشده باشند.

بنابراین نویسندهٔ Protected Variable نمی‌تواند به‌تنهایی محتوای ریسک‌ها را
به نام Owner جعل کند. این کنترل در برابر compromise کامل Admin/DB وعدهٔ
رمزنگاری نمی‌دهد؛ Native audit، هویت انسانی و جداسازی مسیر در محدودهٔ مجاز
حفظ شده‌اند. [Notes API](https://docs.gitlab.com/api/notes/) و
[scopeهای Token](https://docs.gitlab.com/security/tokens/access_token_scopes/).

Regression منفی برای Note مفقود، Author غلط، edit، system note، تغییر محتوا و
JSON نامعتبر افزوده شد. تست‌های مصنوعی Parser/Publisher، Approval واقعی
محسوب نمی‌شوند. آزمون مثبت عملی فقط پس از اقدام مستقل Owner انجام می‌شود.

**تا آن زمان هیچ Merge به protected branches، Tag یا Release مجاز به اجرا نیست.**
