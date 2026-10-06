# واژه‌نامه، پیکربندی و پشتیبانی

> وضعیت v0.1.3: **Phase 4D = LIVE CI ACCEPTED / GO**، Pipeline #11.
> [شواهد پذیرش](../evidence/v0.1.3/phase4d-live-ci-acceptance.md) و
> [آمادگی انتشار](../evidence/v0.1.3/release-readiness.md) مرجع نسخه‌دار هستند؛
> انتشار Wiki، promotion و tag/release هنوز نیازمند مجوز جداگانه‌اند.

| اصطلاح | معنی |
| --- | --- |
| Control Plane | Server که تصمیم و سیاست را دارد. |
| Agent | worker ویندوزی؛ تصمیم معاملاتی نمی‌گیرد. |
| Command ID | شناسه immutable فرمان و محور audit/idempotency. |
| Correlation ID | اتصال command، result، log و transfer. |
| Idempotency | retry پیام، side effect معامله را تکرار نکند. |
| Outbox | نتیجهٔ durable منتظر ارسال. |
| Liveness / Readiness | alive بودن process / آمادگی امن برای کار. |
| Quiesced | توقف کار عادی با control/heartbeat محدود فعال. |
| EXECUTION_AMBIGUOUS | نتیجهٔ trade نامعلوم است؛ retry خودکار ممنوع و reconciliation لازم است. |
| Capability Manifest | inventory versioned از commandها و capabilityهای مجاز Agent. |

## Configuration فعلی

environment settings شامل HTTP host/port/max bytes و log level/file است؛ سیاست محلی Worker نیز در registry ویندوز نگهداری می‌شود؛ [CONFIGURATION](../CONFIGURATION.md) مرجع است. JSONC، Kafka و credential production configuration فعال نیست.

## Error handling و support

برای incident ابتدا version/diagnostics، state lifecycle، terminal discovery، HTTP binding و logهای redacted را بررسی کنید. secret یا private material را در ticket نگذارید. MT5 نبودن، Session 0، terminal history limit و broker outcome را به‌عنوان category جدا ثبت کنید. [KNOWN_ISSUES](../KNOWN_ISSUES.md) محدودیت‌های فعلی را نگه می‌دارد.

## منابع

- [MQL5 Python integration](https://www.mql5.com/en/docs/python_metatrader5)
- [copy_rates_range و UTC/history limit](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py)
- [معماری هدف](../TARGET_ARCHITECTURE.md)
