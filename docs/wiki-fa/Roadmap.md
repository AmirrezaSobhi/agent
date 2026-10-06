# نقشه‌راه، CI/CD و Testing

> وضعیت v0.1.3: **Phase 4D = LIVE CI ACCEPTED / GO**، Pipeline #11.
> [شواهد پذیرش](../evidence/v0.1.3/phase4d-live-ci-acceptance.md) و
> [آمادگی انتشار](../evidence/v0.1.3/release-readiness.md) مرجع نسخه‌دار هستند؛
> انتشار Wiki، promotion و tag/release هنوز نیازمند مجوز جداگانه‌اند.

## Roadmap gateها

1. **v0.1.3:** live CI پذیرفته شده؛ بررسی مستندات، promotion و انتشار جداگانه باقی است.
2. **Architecture approved:** threat model، identity و schemaها.
3. **Runtime proven:** cold-boot در lab و مسیر Session 0 Agent / Session 1 Worker+MT5 در CI زنده پذیرفته شده؛ provisioning عمومی هنوز پذیرفته نیست.
4. **Durable/read/transfer:** SQLite state، read capability و bounded chunking.
5. **Transport/observability:** Kafka، HTTPS/mTLS و support controls.
6. **Execution/hardening:** execution sandbox، service/quiesce/recovery و v1.0.0 gate.

تاریخ تقویمی داده نمی‌شود؛ عبور از هر gate به acceptance evidence وابسته است. جزئیات dependency و issueهای پیشنهادی در [ROADMAP](../ROADMAP.md) و [GITLAB_PLAN](../GITLAB_PLAN.md) است.

## CI/CD فعلی

GitLab source of truth و GitHub mirror است. سه نقش صریح Runner عبارت‌اند از
`linux-source-unit`، `windows-self-hosted-no-mt5` و `windows-self-hosted-mt5`.
Pipeline #11 هر هشت gate را پذیرفته است؛ یک artifact با hash یکسان از build
تا runtime و package مصرف شده و پس از smoke rebuild نشده است. Pipeline #16
در اسناد قدیمی شواهد تاریخی است و مرجع v0.1.3 فعلی نیست.
اختلاف ساعت حدود 10h30m ریسک audit است؛ پیش از انتشار نهایی باید remediation
مجاز یا پذیرش صریح ریسک انجام شود. [فرایند انتشار](../RELEASE_PROCESS.md).

## Testing strategy و release

لایه‌ها: unit، contract/schema، property/edge، persistence، transport، security، integration، controlled Real-MT5، Windows hosting، crash/restart، large transfer، idempotency، priority/failure injection و release acceptance. تست معامله فقط با approval صریح و محیط demo/safe؛ هرگز معاملهٔ مالی واقعی نه. مسیر release: GitLab `develop → staging → main` پس از review است؛ GitHub مستقیم تغییر نمی‌کند.
