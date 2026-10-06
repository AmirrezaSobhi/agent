# امنیت و عملیات

> وضعیت v0.1.3: **Phase 4D = LIVE CI ACCEPTED / GO**، Pipeline #11.
> [شواهد پذیرش](../evidence/v0.1.3/phase4d-live-ci-acceptance.md) و
> [آمادگی انتشار](../evidence/v0.1.3/release-readiness.md) مرجع نسخه‌دار هستند؛
> انتشار Wiki، promotion و tag/release هنوز نیازمند مجوز جداگانه‌اند.

## Identity و authentication — برنامه‌ریزی‌شده

Installation ID به‌طور تصادفی هنگام provision ساخته می‌شود؛ Server Agent ID و credential را اختصاص می‌دهد. customer، subscription، installation، device fingerprint و credential یکی نیستند. fingerprint سخت‌افزار فقط signal بازیابی با بررسی privacy است، نه هویت اصلی. چرخه: provision → register → authenticate → rotate → revoke → reinstall/recover.

## Security — برنامه‌ریزی‌شده

mTLS و rotation/revocation certificate، ACL deny-by-default، replay resistance، payload/decompression bound، secrets OS-protected و recursive redaction لازم‌اند. secret، password، token، private key یا raw credential نه در source/CI و نه در log/telemetry ثبت نمی‌شود.

remote configuration سه قلمرو دارد: `LOCAL_ONLY` برای trust root و anchor امنیتی، `SERVER_MANAGED` برای operation و `SERVER_MANAGED_WITH_LIMITS` برای مقادیر bounded مانند chunk/retention. candidate باید authenticate/authorize/schema/policy/compatibility validate، durable stage، atomic apply، health-check و در failure rollback به last-known-good شود. config معمولی هرگز مرز local security را بازنویسی نمی‌کند.

## Logging و observability — پیاده‌سازی‌شده (بخش پایه)

v0.1.3 logging lifecycle محدود دارد. هدف production: local structured JSON با timestamp/severity/agent/correlation/command/transfer/state/duration/error category، rotation/retention/max disk و support bundle redacted. server telemetry از local logs جداست.

heartbeat شامل version/uptime/lifecycle، MT5/transport/spool، queue age/bytes، active job، last success و CPU/memory/disk امن است. liveness یعنی process/supervisor alive؛ readiness یعنی پذیرش امن یک class کار.

## Runtime و Session 0 — پذیرفته‌شده در CI زنده

Agent/control در Session 0 و Worker پایدار با MT5 در Session 1 است. cold-boot
در lab و safe readها، identity/session، health و persistence بعد از candidate
cleanup در Phase 4D پذیرفته شده‌اند. direct Session 0 MT5 معماری production
نیست؛ installer/service lifecycle عمومی هنوز پذیرفته نشده است.
اختلاف ساعت حدود 10h30m برای ترتیب رخدادها، freshness و audit ریسک است؛
[Operations](../OPERATIONS.md#clock-skew-and-audit-correlation) برنامهٔ اصلاح
با مجوز جداگانه را شرح می‌دهد. اطلاعات account و credential منتشر نمی‌شود.

## Maintenance/quiesce — پیاده‌سازی‌شده (بخش پایه)

`NORMAL → QUIESCING → QUIESCED → RESYNC → NORMAL` به‌صورت cooperative مدل شده است؛ کنترل مسیر زنده می‌ماند و readiness تا پایان resync false است. rotation واقعی log و telemetry production همچنان برنامه‌ریزی‌شده است.
