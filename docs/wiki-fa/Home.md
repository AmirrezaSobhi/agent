# ویکی مهندسی MT5 Agent

> وضعیت v0.1.3: **Phase 4D = LIVE CI ACCEPTED / GO**، Pipeline #11.
> [شواهد پذیرش](../evidence/v0.1.3/phase4d-live-ci-acceptance.md) و
> [آمادگی انتشار](../evidence/v0.1.3/release-readiness.md) مرجع نسخه‌دار هستند؛
> انتشار Wiki، promotion و tag/release هنوز نیازمند مجوز جداگانه‌اند.

> وضعیت: منبع نسخه‌دار برای انتقال به GitLab Wiki. این صفحات قابلیتِ پیاده‌سازی‌شده را با «پیاده‌سازی‌شده» و طرح‌ها را با «برنامه‌ریزی‌شده/مسدود» جدا می‌کنند.

## معرفی و هدف محصول

MT5 Agent نمایندهٔ فنی Server/Control Plane روی ویندوز است: فرمان مجاز را اجرا می‌کند، دادهٔ MT5 را بازیابی می‌کند، نتیجهٔ دقیق را برمی‌گرداند و در آینده در برابر قطع ارتباط بازیابی می‌شود. **Agent نه AI دارد، نه استراتژی معامله، نه تصمیم BUY/SELL/HOLD، و نه مدیریت ریسک یا سرمایه.** این مسئولیت‌ها منحصراً متعلق به Server هستند.

```text
Server: AI, strategy, risk, capital, scheduling, authorization
                │ command / acknowledgement
                ▼
MT5 Agent: validate, execute, retrieve, persist, report, recover
                ▼
        one MetaTrader 5 terminal
```

## نقشهٔ ویکی

- [معماری و قابلیت‌ها](Architecture.md)
- [قابلیت اطمینان و انتقال داده](Reliability.md)
- [امنیت و عملیات](Operations.md)
- [نقشه‌راه و فرایند انتشار](Roadmap.md)
- [واژه‌نامه و عیب‌یابی](Reference.md)

جزئیات state machineها در [STATE_MACHINES](../STATE_MACHINES.md) و traceability در [TRACEABILITY](../TRACEABILITY.md) نگهداری می‌شود.

## وضعیت فعلی v0.1.3

**پذیرفته‌شده در CI زنده:** Agent در Session 0، Worker پایدار و MT5 در
Session 1، IPC محلی authenticated، safe readهای symbols/version/account،
HTTP/JSON، diagnostics، degraded health و بسته‌بندی مستقل Agent.
اطلاعات account در شواهد ثبت نمی‌شود و هیچ معامله‌ای انجام نشده است.
Kafka/mTLS، durable command runtime و trading مسیر production پذیرفته‌شده
نیستند؛ installer/service و provisioning عمومی هنوز نیازمند کار هستند.
مرجع دقیق: [README](../../README.md)، [معماری](../ARCHITECTURE.md) و
[نقشه‌راه](../ROADMAP.md).
