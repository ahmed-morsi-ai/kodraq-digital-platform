# CI/CD باستخدام GitHub Actions — من الصفر إلى Production

> **المستوى:** Backend Engineering — Intermediate → Advanced → Production
>
> **Stack:** Python / FastAPI / PostgreSQL / Redis / Celery / RabbitMQ / Docker / GitHub Actions
>
> **الهدف:** فهم CI/CD كنظام هندسي يضمن جودة الكود، أمان الـpipeline، بناء artifacts قابلة للتكرار، نشرًا مضبوطًا، ومراقبة وRollback واضحين.

---

## 1. الفكرة الكبرى

CI/CD ليس مجرد ملف YAML. هو نظام يجيب عن خمسة أسئلة:

1. هل التغيير صحيح؟
2. هل نستطيع بناءه بشكل متكرر؟
3. هل الـartifact الذي اختبرناه هو نفسه الذي سننشره؟
4. هل يمكن نشره بأقل صلاحيات ومخاطر؟
5. ماذا نفعل إذا فشل بعد النشر؟

الـmental model النهائي:

```text
Developer
   ↓
Commit / Pull Request
   ↓
CI
 ├─ lint
 ├─ format
 ├─ type check
 ├─ unit tests
 ├─ integration tests
 ├─ security checks
 └─ build verification
   ↓
Immutable Artifact
   ↓
Staging
   ↓
Smoke / Health Checks
   ↓
Approval / Policy Gates
   ↓
Production
   ↓
Observability
   └─ Rollback / Fix-forward
```

الفكرة الأساسية:

> كل مرحلة تمنع نوعًا مختلفًا من الأخطاء قبل أن يصل تأثير التغيير إلى المستخدم.

---

# 2. CI وCD

## 2.1 Continuous Integration

CI تعني أن تغييرات الفريق تمر باستمرار عبر سلسلة آلية من التحقق قبل الدمج أو بعده.

بدل:

```text
git push
↓
"عندي شغال"
↓
merge
↓
production breaks
```

نريد:

```text
PR
↓
checks
↓
pass/fail
↓
review
↓
merge
```

## 2.2 Continuous Delivery

الكود يبقى دائمًا في حالة قابلة للنشر، لكن production قد تحتاج approval يدوي.

```text
main
↓
build
↓
test
↓
staging
↓
ready for production
↓
approval
↓
production
```

## 2.3 Continuous Deployment

كل تغيير يمر بالـgates يتم نشره تلقائيًا.

```text
main
↓
validation
↓
deploy
```

لا يوجد تعريف واحد يجب أن يناسب كل الشركات؛ القرار يعتمد على المخاطر، الـcompliance، ودرجة الأتمتة المطلوبة.

---

# 3. GitHub Actions Mental Model

GitHub Actions تبني الـautomation على شكل:

```text
Workflow
 ├─ Event
 ├─ Jobs
 │   ├─ Runner
 │   └─ Steps
 │       ├─ run
 │       └─ uses
 └─ Policy / Permissions / Environment
```

ملفات الـworkflow توجد عادة في:

```text
.github/workflows/
```

وفق وثائق GitHub، الـworkflow يتكون من event أو أكثر، وjobs، وكل job يعمل على runner ويحتوي على steps.

---

# 4. أول Workflow

```yaml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v5

      - name: Setup Python
        uses: actions/setup-python@v7
        with:
          python-version: "3.13"
          cache: pip

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements.txt
          python -m pip install -r requirements-dev.txt

      - name: Test
        run: python -m pytest -q
```

اقرأه كالتالي:

```text
on       = متى؟
runs-on  = أين؟
jobs     = ماذا؟
steps    = كيف؟
uses     = Action جاهزة
run      = أمر تنفذه أنت
```

---

# 5. Events

أكثر الـevents استخدامًا:

```yaml
on:
  push:
  pull_request:
  workflow_dispatch:
  schedule:
  release:
  workflow_call:
  repository_dispatch:
```

## Push

```yaml
on:
  push:
    branches: [main]
```

## Pull Request

```yaml
on:
  pull_request:
    branches: [main]
```

## Manual

```yaml
on:
  workflow_dispatch:
```

## Schedule

```yaml
on:
  schedule:
    - cron: "0 2 * * *"
```

الـscheduled workflows مفيدة للـnightly tests أو التقارير أو checks دورية، لكنها ليست بديلًا عن checks التي تقرب من لحظة تغيير الكود.

---

# 6. Jobs وSteps وDAG

إذا كتبت:

```yaml
jobs:
  lint:
    ...

  test:
    ...

  build:
    needs: [lint, test]
```

فأنت بنيت DAG:

```text
lint ─────┐
          ├──> build
test ─────┘
```

`needs` تعني dependency في execution graph، ولا تعني أن filesystem الخاص بـjob السابقة مشترك.

إذا احتجت ملفًا من job أخرى استخدم artifact أو وسيلة نقل صريحة.

---

# 7. Parallelism

إذا كانت المهام مستقلة:

```text
            ┌─ lint
PR ─────────┼─ unit tests
            ├─ typecheck
            └─ security
                    ↓
                  build
```

أفضل غالبًا من:

```text
lint → typecheck → tests → security → build
```

لكن الـparallelism له تكلفة runner time وstorage وnetwork، لذلك لا تطبق التوازي بدون قياس.

---

# 8. `permissions` وLeast Privilege

ابدأ بأقل صلاحيات ممكنة:

```yaml
permissions:
  contents: read
```

ثم زدها فقط عند الحاجة، مثل:

```yaml
permissions:
  contents: read
  packages: write
```

أو:

```yaml
permissions:
  contents: read
  id-token: write
```

الأخير خاص بطلب OIDC token، وليس معناه أن workflow أصبح قادرًا تلقائيًا على تعديل موارد cloud.

القاعدة:

> GitHub permissions + cloud IAM يجب أن يطبقا Least Privilege معًا.

---

# 9. `GITHUB_TOKEN`

تعامل مع `GITHUB_TOKEN` كـcredential حقيقية.

إذا أعطيتها صلاحيات واسعة، فإن compromise لأي step مناسب قد يوسع الـblast radius.

لذلك:

```text
minimum permission
↓
minimum job scope
↓
minimum secret scope
```

ولا تجعل كل jobs تستخدم نفس الصلاحيات بدون داع.

---

# 10. Secrets

لا تضع:

```yaml
run: echo "API_KEY=abc123"
```

استخدم:

```yaml
- name: Deploy
  env:
    API_KEY: ${{ secrets.API_KEY }}
  run: ./scripts/deploy.sh
```

ومع ذلك، لا تعتمد على masking وحده. الأفضل أن تقلل تعرض secret من الأساس:

- لا تطبعها.
- لا تخزنها في artifact.
- لا تضعها في cache.
- لا تمررها إلى Actions غير موثوقة.
- أعطها فقط للjob التي تحتاجها.

---

# 11. Repository Secrets vs Environment Secrets

استخدم Repository Secrets عندما تكون القيمة مشتركة على مستوى الـrepo.

واستخدم Environment Secrets عندما تكون مرتبطة ببيئة:

```text
staging
  DATABASE_URL

production
  DATABASE_URL
```

ميزة Environment أنها تربط secrets بالـdeployment policy الخاصة بهذه البيئة.

---

# 12. Environments

مثال:

```yaml
deploy:
  environment:
    name: production
```

يمكن للـEnvironment أن تفرض:

- required reviewers
- branch restrictions
- protection rules
- environment secrets

وبالتالي تصبح حماية production policy جزءًا من المنصة، وليس مجرد `if` في bash.

---

# 13. Cache vs Artifact

هذه من أهم النقاط في الدرس.

## Cache

الغرض الأساسي:

```text
speed
```

مثال:

```text
pip download cache
```

إذا cache اختفت، يجب أن يستطيع الـbuild إعادة إنشاء ما يحتاجه.

## Artifact

الغرض:

```text
preserve output
share output between jobs
```

مثل:

```text
coverage.xml
junit.xml
build.zip
Docker metadata
logs
```

احفظ القاعدة:

> Cache = optimization. Artifact = output/evidence.

---

# 14. Python Dependency Caching

`setup-python` يدعم caching لبعض package managers.

مثال:

```yaml
- uses: actions/setup-python@v7
  with:
    python-version: "3.13"
    cache: pip
```

لكن لا تضع secrets في paths التي يتم caching لها.

GitHub تحذر من أن cache contents ليست trusted ولا موقعة، وأن cache poisoning قد يصبح supply-chain risk في workflow غير محكم.

---

# 15. Matrix

بدل كتابة ثلاث jobs:

```text
Python 3.12
Python 3.13
Python 3.14
```

استخدم:

```yaml
strategy:
  matrix:
    python-version: ["3.12", "3.13", "3.14"]
```

ثم:

```yaml
- uses: actions/setup-python@v7
  with:
    python-version: ${{ matrix.python-version }}
```

يمكن أيضًا الجمع بين OS وPython:

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest]
    python-version: ["3.12", "3.13"]
```

لكن كل combination يستهلك وقتًا وموارد.

---

# 16. `fail-fast`

في matrix:

```yaml
strategy:
  fail-fast: false
```

قد يكون مفيدًا عندما تريد رؤية كل failures بدل توقف باقي combinations عند أول failure.

في PR سريع جدًا قد تختار behavior مختلف.

---

# 17. Tests: Pyramid

لا تجعل كل اختباراتك E2E.

```text
        E2E
       /   \
  Integration
 /           \
Unit Tests
```

عادة:

```text
Unit        = كثيرة + سريعة
Integration = أقل + أبطأ
E2E         = قليلة + أغلى
```

في FastAPI:

```text
service tests
repository integration
API tests
DB tests
e2e
```

كل طبقة تجيب عن سؤال مختلف.

---

# 18. Quality Gates

Quality gate هو شرط يمنع الانتقال.

مثال:

```text
lint = pass
format = pass
typecheck = pass
tests = pass
security = pass
build = pass
```

ثم:

```text
deploy
```

الفكرة:

> CI ليست report فقط؛ هي policy engine صغير يمنع التغيير غير المقبول.

---

# 19. Lint وFormatting

مثال:

```bash
ruff check .
ruff format --check .
```

لا تجعل CI تقوم بتعديل code تلقائيًا إلا لو هذا behavior مقصود. في معظم فرق backend الأفضل أن يكون check واضحًا:

```text
wrong → fail
```

بدل:

```text
wrong → mutate repository
```

---

# 20. Type Checking

مثال:

```bash
mypy app
```

أو أداة type checker أخرى.

الهدف ليس جعل Python “لغة static”، بل كشف assumptions خاطئة قبل runtime.

---

# 21. Coverage

مثال:

```bash
pytest --cov=app --cov-fail-under=80
```

لكن تذكر:

```text
coverage ≠ correctness
```

80% meaningful tests قد تكون أفضل من 98% tests سطحية.

ركز coverage على:

- auth
- authorization
- payments
- state transitions
- data validation
- business rules

---

# 22. Flaky Tests

Flaky test:

```text
run 1 → pass
run 2 → fail
run 3 → pass
```

أسباب شائعة:

- race conditions
- الوقت الحقيقي
- network
- random seed
- ordering
- external APIs
- eventual consistency

لا تستخدم retry لإخفائها.

> Retry قد يكون policy للtransient failure، لكنه ليس علاجًا للـflaky tests.

---

# 23. Service Containers مع PostgreSQL

ممكن تشغيل Postgres أثناء integration tests:

```yaml
services:
  postgres:
    image: postgres:16
    env:
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
      POSTGRES_DB: app_test
    ports:
      - 5432:5432
    options: >-
      --health-cmd="pg_isready -U test -d app_test"
      --health-interval=10s
      --health-timeout=5s
      --health-retries=5
```

ثم:

```yaml
env:
  DATABASE_URL: postgresql+psycopg://test:test@localhost:5432/app_test
```

Health check مهم حتى لا تبدأ الاختبارات قبل جاهزية database.

---

# 24. Redis وRabbitMQ في CI

نفس المبدأ يمكن تطبيقه على:

```text
Redis
RabbitMQ
```

أو استخدام `docker compose` لبيئة integration:

```text
API
Postgres
Redis
RabbitMQ
Worker
```

لكن لا تجعل unit test تعتمد على كل هذه الخدمات. كلما ارتفع scope الاختبار ارتفع الـcost والـfailure surface.

---

# 25. FastAPI CI عملي

بداية جيدة:

```yaml
name: Backend CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v7
        with:
          python-version: "3.13"
          cache: pip
      - run: python -m pip install -r requirements-dev.txt
      - run: ruff check .
      - run: ruff format --check .

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v7
        with:
          python-version: "3.13"
          cache: pip
      - run: python -m pip install -r requirements-dev.txt
      - run: mypy app

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: app_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd="pg_isready -U test -d app_test"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5
    env:
      DATABASE_URL: postgresql+psycopg://test:test@localhost:5432/app_test
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v7
        with:
          python-version: "3.13"
          cache: pip
      - run: python -m pip install -r requirements-dev.txt
      - run: alembic upgrade head
      - run: pytest -q
```

---

# 26. `make check` كـContract

من المفيد توحيد commands محليًا وداخل CI:

```makefile
lint:
	python -m ruff check .

format-check:
	python -m ruff format --check .

test:
	python -m pytest

check: lint format-check test
```

ثم:

```yaml
- run: make check
```

الفكرة:

> نفس الأمر الذي يستطيع المطور تشغيله محليًا يجب أن يكون قريبًا من الأمر الذي تقرأه CI.

---

# 27. `timeout-minutes`

لا تسمح لjob أن تتعلق بلا نهاية:

```yaml
test:
  timeout-minutes: 15
```

مفيد ضد:

- hung processes
- deadlock
- stuck network calls
- misconfigured services

---

# 28. Concurrency

إذا جاء commit جديد، CI القديمة قد تصبح غير مهمة:

```yaml
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

أما production deployment فقد تريد:

```yaml
concurrency:
  group: production
  cancel-in-progress: false
```

حتى لا يحدث deploy متداخل لنفس البيئة.

الفكرة:

```text
CI = old run may become irrelevant
Production = deployment may need serialization
```

---

# 29. Build Once, Deploy Many

خطأ شائع:

```text
build image for staging
↓
rebuild image for production
```

الأفضل:

```text
source
↓
build once
↓
immutable artifact
↓
staging
↓
production
```

السبب: إعادة البناء قد تغيّر:

- dependency resolution
- base image
- generated files
- timestamps
- network-fetched data

---

# 30. Docker Artifact

وسم image بـcommit SHA:

```yaml
- name: Build image
  uses: docker/build-push-action@v6
  with:
    context: .
    push: false
    tags: |
      ghcr.io/example/backend:${{ github.sha }}
```

`latest` وحده reference متحرك. الـdigest أقوى من ناحية التحديد:

```text
image@sha256:...
```

والهدف النهائي:

> Production يعرف artifact محددًا، وليس مجرد اسم متحرك.

---

# 31. Docker Registry Flow

```text
GitHub Actions
   ↓
docker build
   ↓
scan
   ↓
push registry
   ↓
image digest
   ↓
deploy
```

لو تستخدم GHCR أو registry أخرى، اجعل identity الخاصة بالنشر أقل صلاحيات ممكنة.

---

# 32. Dockerfile Baseline

```dockerfile
FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN useradd --create-home app
USER app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

هذا baseline فقط. في production يمكن تحسينه أكثر عبر multi-stage build، dependency lock، image digest، health checks، وتقليل attack surface.

---

# 33. لا تضع Secrets داخل Docker Image

لا تفعل:

```dockerfile
ENV JWT_SECRET=...
```

ولا:

```dockerfile
COPY .env .
```

الـimage يجب ألا تصبح خزنة أسرار.

في runtime استخدم secret injection المناسبة للمنصة.

---

# 34. Artifacts بين Jobs

لو build ينتج ملفًا:

```text
build
 ↓
artifact
 ↓
deploy
```

استخدم upload/download artifact بدل افتراض مشاركة workspace.

مثال concept:

```yaml
- name: Upload
  uses: actions/upload-artifact@v5
  with:
    name: test-results
    path: |
      junit.xml
      coverage.xml
```

ثم job أخرى تحمل الـartifact.

---

# 35. Failed Run Evidence

عندما تفشل E2E، من المفيد حفظ:

```text
screenshots
logs
traces
coverage
JUnit XML
```

مثال:

```yaml
- name: Upload test evidence
  if: failure()
  uses: actions/upload-artifact@v5
  with:
    name: test-evidence
    path: test-results/
```

هنا artifact ليست optimization؛ إنها evidence للتشخيص.

---

# 36. Environments وStaging/Production

تصميم شائع:

```text
PR
 ↓
CI
 ↓
main
 ↓
Staging
 ↓
Smoke
 ↓
Production approval
 ↓
Production
```

GitHub توثق أن environments تستطيع فرض approvals وتقييد الفروع وتحديد secrets خاصة بالبيئة.

---

# 37. OIDC

بدل credential طويلة العمر:

```text
GitHub secret
= cloud access key
```

يمكن استخدام:

```text
GitHub Actions
↓
OIDC token
↓
Cloud trust policy
↓
Short-lived cloud credential
↓
Deploy
```

GitHub توفر OIDC للتكامل مع cloud providers ودعم claims يمكن استخدامها في trust policy.

---

# 38. OIDC Permissions

عادة يحتاج workflow:

```yaml
permissions:
  contents: read
  id-token: write
```

مهم:

> `id-token: write` تسمح للworkflow بطلب OIDC token؛ لا تعطيها وحدها صلاحية تعديل موارد cloud.

الصلاحية الفعلية تأتي من cloud provider trust/IAM policy.

---

# 39. OIDC Trust Conditions

لا تجعل cloud تقول:

```text
any workflow from this GitHub org may deploy
```

بدون شروط إضافية إذا لم يكن هذا مقصودًا.

قيد trust على context مناسب مثل:

```text
repository
branch/tag
environment
workflow identity
```

والأفضل أن يكون Production identity منفصلًا عن Staging.

---

# 40. Production Environment

مثال:

```yaml
jobs:
  deploy:
    environment:
      name: production
```

ثم داخل GitHub:

```text
Settings
→ Environments
→ production
→ required reviewers / protections
```

لا تعتمد على:

```yaml
if: github.ref == 'refs/heads/main'
```

وحدها كauthorization mechanism.

---

# 41. Production Workflow Skeleton

```yaml
name: Deploy Production

on:
  push:
    tags:
      - "v*"

permissions:
  contents: read
  id-token: write

concurrency:
  group: production
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: production

    steps:
      - name: Checkout
        uses: actions/checkout@v5

      - name: Authenticate
        run: ./scripts/auth-cloud.sh

      - name: Deploy
        run: ./scripts/deploy.sh

      - name: Smoke test
        run: ./scripts/smoke.sh
```

هذه skeleton عامة؛ تفاصيل auth/deploy تعتمد على cloud/platform.

---

# 42. Tag-based Releases

ممكن أن يكون:

```text
main
 ↓
tag v1.8.0
 ↓
release workflow
 ↓
build
 ↓
staging
 ↓
production
```

الميزة أن release boundary واضحة.

لكن يمكن أيضًا اختيار main-based CD، خصوصًا عندما يكون المنتج مصممًا لـcontinuous deployment.

---

# 43. Release vs Deployment

لا تخلط:

```text
Deployment = الكود وصل للـenvironment
Release    = feature أصبحت متاحة للمستخدم
```

باستخدام feature flags يمكن:

```text
deploy = yes
release = no
```

ثم إطلاق feature تدريجيًا.

---

# 44. Smoke Tests

بعد deploy لا تقل:

```text
container started = success
```

اختبر:

```bash
curl --fail --silent --show-error \
  https://api.example.com/health
```

ثم يمكن توسيعها إلى critical paths:

```text
health
readiness
login
critical API
DB connectivity
```

---

# 45. Health vs Readiness

`liveness` تقريبًا يسأل:

> هل process ما زالت حية؟

`readiness` يسأل:

> هل هي مستعدة لاستقبال traffic؟

قد تكون:

```text
process = alive
DB = down
```

فالprocess حية، لكنها ليست ready.

---

# 46. Smoke Test مع Retry محدود

الـdeployment قد يحتاج وقتًا قصيرًا:

```bash
for i in 1 2 3 4 5; do
  if curl --fail --silent --show-error https://api.example.com/health; then
    exit 0
  fi
  sleep 5
done

exit 1
```

هذا **bounded retry**، وليس retry بلا نهاية.

---

# 47. Database Migrations

أخطر خطأ شائع:

```text
deploy new code
↓
drop old column immediately
```

والنسخة القديمة قد تكون ما زالت تعمل.

التصميم الأصح غالبًا:

```text
Expand
↓
Deploy compatible code
↓
Backfill
↓
Switch reads/writes
↓
Contract
```

---

# 48. Expand and Contract

مثال تغيير `name` إلى `display_name`:

### Phase 1

أضف `display_name`.

### Phase 2

الكود يدعم الاثنين.

### Phase 3

ابدأ الكتابة للجديد.

### Phase 4

Backfill old rows.

### Phase 5

حوّل القراءة للجديد.

### Phase 6

احذف القديم في release منفصل بعد اختفاء consumers القدامى.

الفكرة:

> لا تجعل deployment يفترض أن النسخة السابقة اختفت فورًا.

---

# 49. Migration Job منفصل

في نظام متعدد replicas، لا تجعل كل instance تتسابق لعمل migration.

قد يكون التصميم:

```text
build
↓
migration job once
↓
app deploy
↓
smoke
```

أو استراتيجية أخرى تناسب platform.

المهم أن الـmigration execution يكون controlled.

---

# 50. Rollback

Rollback جيد يجب أن يعيد deploy artifact معروفًا:

```text
Production D10
↓
incident
↓
rollback D9
↓
smoke
```

لا تفعل:

```text
git checkout old
↓
rebuild
↓
hope
```

إلا إذا كانت rebuild هي الاستراتيجية المقصودة والمضمونة.

---

# 51. Rollback لا يساوي Database Restore

هذه نقطة مهمة جدًا:

```text
application rollback
≠
database rollback
```

قد ترجع code إلى v9 لكن database تحتوي state أنشأه v10.

لذلك migrations يجب أن تكون مصممة مع compatibility.

---

# 52. Rollback vs Fix-forward

ليس كل incident يعالج بالrollback.

قد تختار fix-forward إذا:

- database state تغير
- migration irreversible
- rollback أخطر
- الإصلاح صغير وواضح

القرار يعتمد على أثر البيانات والحالة الحالية.

---

# 53. Deployment Strategies

أهم الاستراتيجيات:

```text
Recreate
Rolling
Blue/Green
Canary
Shadow
```

## Rolling

```text
v1 v1 v1 v1
↓
v1 v1 v1 v2
↓
v1 v1 v2 v2
↓
v1 v2 v2 v2
↓
v2 v2 v2 v2
```

## Blue/Green

```text
Blue = current
Green = new
↓
switch traffic
```

## Canary

```text
99% → v1
1%  → v2
```

ثم توسع traffic تدريجيًا.

---

# 54. Deployment Concurrency

Production deployments لا ينبغي أن تتداخل بلا داع.

```yaml
concurrency:
  group: production
  cancel-in-progress: false
```

GitHub توثق استخدام concurrency للتحكم في workflows/jobs المتزامنة، بما في ذلك جعل environment لا يحتوي أكثر من deployment واحد قيد التنفيذ لنفس group.

---

# 55. Docker Layer Caching

رتّب Dockerfile بحيث الأشياء الثابتة تأتي قبل الأشياء المتغيرة كثيرًا:

```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app
```

إذا تغير `app/` فقط، يمكن إعادة استخدام dependency layer حسب build cache.

لكن تذكر:

> Cache optimization، وليست dependency source of truth.

---

# 56. Dependency Reproducibility

استخدم lockfile أو constraints المناسبين للأداة التي اخترتها، مثل:

```text
uv.lock
poetry.lock
```

أو requirements pinned/controlled.

الهدف:

```text
same declared inputs
→ predictable build
```

وابتعد عن الاعتماد غير المقصود على `latest` في build-critical dependencies.

---

# 57. Action Security

Action هي code.

عندما تكتب:

```yaml
uses: someone/some-action@v1
```

أنت عمليًا تدخل code خارجيًا إلى build environment.

تحقق من:

- صاحب المشروع.
- مصدر الـAction.
- permissions المطلوبة.
- هل تقرأ secrets؟
- ماذا تفعل بالمحتوى؟
- هل tag متحرك؟

GitHub توصي بأن pinning إلى full-length commit SHA هو الخيار الأكثر أمانًا لجعل Action reference immutable.

---

# 58. SHA Pinning

الأكثر صرامة:

```yaml
uses: actions/checkout@<full-commit-sha>
```

بدل:

```yaml
uses: actions/checkout@v5
```

لكن SHA pinning تزيد صعوبة التحديث اليدوي، لذلك من المفيد استخدام Dependabot/Renovate أو عملية تحديث مركزية.

في هذا الدرس نستخدم major tags في الأمثلة لتكون واضحة وقابلة للقراءة، مع التنبيه أن Production security policy قد تفرض SHA pinning.

---

# 59. Forked Pull Requests

تعامل مع كود PR من fork كـuntrusted code.

لا تمنحه production secrets أو صلاحيات حساسة لمجرد أنه يعمل داخل GitHub.

المسار الخطير:

```text
untrusted PR
↓
workflow executes PR code
↓
secret available
↓
exfiltration
```

القاعدة:

> لا تشغل untrusted PR code في context يملك أسرار production أو write permissions غير ضرورية.

---

# 60. `pull_request_target`

`pull_request_target` له trust model مختلف عن `pull_request` ويمكن أن يملك وصولًا أكبر إلى repository context/secrets بحسب إعداداتك.

لذلك لا تتبع نمطًا مثل:

```text
pull_request_target
↓
checkout untrusted PR
↓
run its scripts
```

بلا فهم كامل للعواقب.

GitHub لديها توثيق أمني منفصل لهذا النوع من السيناريوهات.

---

# 61. Command Injection في CI

تخيّل أنك تضع input يتحكم فيه PR author داخل shell command بشكل غير آمن.

قاعدة:

> أي data تأتي من event payload تعامل معها كـuntrusted input.

ومن الأفضل عند الحاجة لتمرير قيمة إلى shell أن تمررها كـenvironment variable مع quoting صحيح بدل تركيب command strings غير آمنة.

---

# 62. Build Scripts نفسها Attack Surface

حتى لو YAML آمن، قد تكون الخطورة في:

```text
Makefile
scripts/
package hooks
Dockerfile
build scripts
```

إذا شغلت:

```yaml
run: make test
```

فأنت تسمح لـrepository code أن يتنفذ.

ولهذا security في CI لا تعني مراجعة YAML فقط.

---

# 63. Self-hosted Runners

ميزة:

- private network
- custom hardware
- internal resources

لكن المخاطرة:

```text
untrusted workflow
↓
long-lived runner
↓
persistent state / credentials
```

إذا استخدمت self-hosted runners:

- patch OS
- حد network access
- قلل secrets
- نظف workspace
- راقب runner
- افصل prod عن non-prod
- فكر في ephemeral runners

---

# 64. OIDC بدل Long-lived Keys

إذا cloud provider يدعم GitHub OIDC، يمكن بناء trust federation بدون تخزين cloud password طويلة العمر كـGitHub secret.

التصميم:

```text
GitHub workflow
↓
OIDC JWT
↓
cloud validates claims
↓
short-lived access token
↓
deploy
```

هذا يقلل credential lifetime ويجعل trust policy أكثر صرامة.

---

# 65. Two-layer Least Privilege

لا يكفي:

```text
GitHub permissions = least privilege
```

إذا cloud IAM تقول:

```text
this identity can delete everything
```

نريد:

```text
GitHub permissions
      +
Cloud IAM permissions
```

كل منهما ضيق.

---

# 66. Immutable Artifact

الهدف:

```text
Commit SHA
↓
Build
↓
Artifact digest
↓
Staging
↓
Production
```

لا ينبغي أن يعني:

```text
deploy production = rebuild
```

بل:

```text
promote exact artifact
```

---

# 67. Provenance

يجب أن تستطيع الإجابة:

> هذه الـimage بُنيت من أي commit؟

و:

> أي workflow أنتجها؟

و:

> أي release نشرها؟

تقريبًا:

```text
Artifact
↓
Commit
↓
Workflow Run
↓
Repository
```

كلما زادت traceability، أصبح incident response أسهل.

---

# 68. Artifact Attestations

GitHub توفر Artifact Attestations لإنشاء claims موثقة حول provenance وintegrity للـbuild artifacts.

الفكرة:

```text
artifact
+
provenance statement
+
cryptographic verification
```

هذا مهم في supply-chain security، خاصة عند زيادة متطلبات الثقة في build pipeline.

---

# 69. SBOM

SBOM = Software Bill of Materials.

يعني معرفة المكونات التي تشكل artifact:

```text
Application
├─ dependency A
├─ dependency B
├─ base image
└─ system packages
```

يمكن دمج SBOM generation والـvulnerability scanning في release workflow أو deep security pipeline.

---

# 70. Security Scanning Layers

قد تضع:

```text
Dependency scan
SAST
Secret scan
Container scan
IaC scan
```

لكن لا تضف أدوات لمجرد كثرتها.

لكل tool اسأل:

```text
ما الإشارة التي يقدمها؟
ما false positive rate؟
من يصلح findings؟
ما severity التي توقف release؟
```

---

# 71. Security Regression Tests

أي security bug مهم يجب أن يتحول إلى regression test.

مثال RBAC/BOLA:

```python
def test_user_cannot_access_other_tenant_invoice(client):
    ...
```

ثم:

```text
security bug
↓
regression test
↓
CI gate
```

بهذه الطريقة الـCI تصبح ذاكرة أمنية للمشروع.

---

# 72. RBAC + CI

اختبر:

```text
admin → allowed
editor → allowed only on permitted action
user → denied
wrong tenant → denied
expired authorization → denied
```

اختبارات negative paths مهمة جدًا.

---

# 73. Redis + CI

من درس Caching، اختبر على مستويات:

```text
Unit
 └─ cache abstraction behavior

Integration
 ├─ cache hit
 ├─ cache miss
 ├─ expiration
 └─ invalidation
```

ولا تجعل كل unit test يحتاج Redis حقيقي.

---

# 74. Celery + CI

اختبر:

```text
unit:
  task logic

integration:
  publish → broker → worker → result
```

واختبر خصائص مثل:

- idempotency
- retries
- duplicate delivery behavior
- timeout

---

# 75. WebSockets + CI

لا تكتفِ بـHTTP tests.

اختبر:

```text
connect
authenticate
authorize
join room
send
receive
disconnect
reconnect
```

وفي multi-instance systems يمكن اختبار:

```text
client A → instance A
client B → instance B
event → both receive
```

---

# 76. Multi-tenant CI

اختبار أمني مهم:

```text
Tenant A
↓
request object ID belonging to Tenant B
↓
must be denied
```

هذه ليست مجرد business test. إنها authorization invariant.

---

# 77. Contract Tests

عند وجود services:

```text
Service A → Service B
```

أنت تحتاج contract protection حتى لا يمر تغيير في B يكسر A.

مثال:

```text
OpenAPI schema
↓
compatibility check
↓
fail on breaking change
```

هذا مفيد جدًا في microservices.

---

# 78. Monorepo

لو عندك:

```text
repo/
├── backend/
├── frontend/
├── worker/
└── shared/
```

يمكن استخدام path filters، لكن لا تعتمد عليها عميانيًا.

لو تغيّر `shared/` قد يتأثر أكثر من service.

لذلك نحتاج dependency graph أو affected-target logic عندما يصبح المشروع كبيرًا.

---

# 79. Fast vs Deep CI

### PR CI

```text
lint
format
unit
focused integration
typecheck
build check
```

### Nightly / Release

```text
full E2E
large matrix
deep security scan
load tests
mutation tests
chaos tests
full AI evaluation
```

هذا يعطي:

```text
fast feedback + deep confidence
```

---

# 80. Performance Tests

لا تجعل full load test لكل PR إلا إذا تحتاج ذلك فعلًا.

يمكن عمل:

```text
small smoke benchmark → PR
full load test → nightly/release
```

راقب:

- p95 latency
- p99 latency
- error rate
- throughput

مع مراعاة أن shared runners قد تكون noisy.

---

# 81. AI/RAG CI

لو backend يحتوي RAG:

```text
ingestion
chunking
embedding
retrieval
metadata filtering
permission filtering
LLM generation
```

اختبر خصوصًا:

```text
Tenant A query
↓
retriever
↓
must never return Tenant B private documents
```

وفي evaluation:

```text
golden dataset
↓
retrieval metrics
↓
generation checks
↓
threshold
```

أما full evals الغالية فقد تكون nightly/release jobs.

---

# 82. Celery/RabbitMQ Deployment Compatibility

عندما تغير task message:

```text
old worker
new message
```

قد ينكسر rollout.

لذلك أثناء release:

```text
new producer + old consumer compatibility
```

قد تكون شرطًا، أو تحتاج coordinated deployment.

---

# 83. WebSocket Deployment Compatibility

عند deploy قد تنقطع connections.

لذلك system يجب أن يملك:

- graceful shutdown
- reconnect logic
- backoff
- shared realtime state إن لزم

CI ينبغي أن تختبر أن disconnect/reconnect behavior متوقع.

---

# 84. Deployment Observability

بعد كل deployment، يجب أن تعرف:

```text
who deployed?
what artifact?
which commit?
which environment?
when?
```

وسجّل metadata مناسبة دون secrets.

---

# 85. Version Endpoint

قد يكون لديك endpoint داخلي/secured مثل:

```json
{
  "version": "1.8.0",
  "git_sha": "abc123",
  "environment": "production"
}
```

هذا يجعل smoke tests وincident investigation أسهل.

---

# 86. Application Health ≠ Business Health

قد يكون:

```text
HTTP 200
DB connected
CPU normal
```

لكن:

```text
payment_success_rate = 60%
```

إذن deployment صحي تقنيًا، لكنه غير صحي business-wise.

في الأنظمة الحرجة، observability يجب أن تشمل technical وbusiness signals.

---

# 87. Failure Classification

عند failure صنّفه:

```text
Code Failure
Infrastructure Failure
Dependency Failure
CI Configuration Failure
Security Policy Failure
External Service Failure
```

هذه التصنيفات تقلل random debugging.

---

# 88. Retry Decision Matrix

| Failure | Retry غالبًا؟ | لماذا |
|---|---:|---|
| Unit assertion | لا | deterministic |
| Lint | لا | deterministic |
| Type check | لا | deterministic |
| Registry transient error | أحيانًا | transient |
| Network timeout | أحيانًا | transient |
| Invalid secret | لا | configuration |
| Migration logic failure | لا | تحتاج investigation |
| Flaky test | ليس كحل دائم | يجب إصلاح السبب |

---

# 89. Pipeline Speed

قس الوقت:

```text
queue
checkout
dependency install
test
docker build
artifact upload
```

ثم حسّن bottleneck الحقيقي.

لا تبدأ بإضافة parallelism لأن “المشكلة شكلها بطء”.

---

# 90. Cache Key

مفهوم عام جيد:

```text
OS
+
Python version
+
lockfile hash
```

إذا dependencies تغيرت، يجب أن تتغير key فعليًا أو logic الخاص بإدارة cache.

---

# 91. Cache Failure

الـworkflow الجيدة تعمل لو cache اختفت:

```text
cache hit
 → fast

cache miss
 → reinstall
 → still correct
```

إذا cache miss تكسر workflow، فأنت جعلت optimization dependency لازمة للتصحيح.

---

# 92. Artifact Retention

ليست كل artifacts يجب أن تعيش للأبد.

حدد retention حسب:

- debugging needs
- release evidence
- compliance
- storage cost

وفي security incidents قد تحتاج preserve evidence بصورة مختلفة.

---

# 93. Release Traceability

يجب أن تستطيع الإجابة:

```text
هذا السيرفر يعمل بأي version؟
هذا image بُني من أي commit؟
من نشره؟
أي workflow أنتجته؟
```

إذا الإجابة غير واضحة، لديك مشكلة deployment observability.

---

# 94. Branch Protection

هدف شائع:

```text
feature
↓
PR
↓
review
↓
required checks
↓
merge main
```

ولا:

```text
developer → push main → production
```

يمكن دمج:

- required reviewers
- required status checks
- منع force push
- restrictions على direct push

بحسب repository policy.

---

# 95. Production Approval

مثال عملي:

```text
PR approved
+
CI green
+
artifact built
+
staging smoke passed
+
production environment approved
=
production deploy
```

هذه سلسلة policy واضحة يمكن تدقيقها.

---

# 96. Break-glass

لو احتجت emergency path:

```text
break-glass
```

هذا لا يعني:

```text
no logging
no audit
no restrictions
```

بل:

```text
limited exceptional path
+
strong audit
+
post-incident review
```

---

# 97. Migration + Zero Downtime

تصميم شائع:

```text
v1 running
 ↓
expand schema
 ↓
v1/v2 compatible code
 ↓
backfill
 ↓
traffic to v2
 ↓
remove old assumptions
 ↓
contract schema
```

هذه طريقة تفكير أكثر أمانًا من “deploy كل شيء في خطوة واحدة”.

---

# 98. Blue/Green

```text
Blue = current production
Green = new version

Deploy Green
↓
Smoke / validate
↓
Switch traffic
```

Rollback:

```text
traffic → Blue
```

إذا المنصة تدعم هذا النموذج بكفاءة، يمكن أن يكون مفيدًا جدًا عندما تكون rollback speed مهمة.

---

# 99. Canary

مثال:

```text
v1 = 99%
v2 = 1%
```

ثم:

```text
1%
→ 10%
→ 25%
→ 50%
→ 100%
```

لكن هذا يتطلب traffic control وmetrics جيدة؛ GitHub Actions وحدها ليست كل نظام الـcanary.

---

# 100. GitOps

في GitOps:

```text
Git repository
= desired state
```

ثم controller مثل:

```text
Argo CD / Flux
```

يطبق الحالة على cluster.

قد يكون flow:

```text
source repo
↓
CI build
↓
image registry
↓
update deployment repo
↓
GitOps controller
↓
cluster
```

فكر في GitHub Actions كـorchestrator ضمن architecture، وليس بالضرورة كل deployment platform بنفسها.

---

# 101. Microservices CI/CD

لو عندك:

```text
users
orders
payments
notifications
```

قد تحتاج لكل service:

```text
independent build
independent tests
independent artifact
independent deployment
```

مع:

```text
contract tests
shared workflows
centralized policy
```

---

# 102. Reusable Workflows

بدل نسخ pipeline نفسها في كل repository:

```yaml
on:
  workflow_call:
```

يمكن مشاركة workflow منظمة.

استخدمها عندما تكون:

```text
policy/common orchestration
```

مش مجرد abstraction لمجرد تقليل 5 أسطر.

---

# 103. Composite Actions

Composite Action تجمع steps متكررة.

فهم الفرق:

```text
Composite Action
= reusable group of steps

Reusable Workflow
= reusable workflow orchestration
```

---

# 104. Internal Golden Path

في شركة صغيرة/متوسطة قد تضع template:

```text
FastAPI Service
↓
standard repo
↓
CI
↓
security
↓
Docker
↓
staging
↓
production
```

الهدف تقليل toil وليس إخفاء النظام عن المطورين.

---

# 105. مشروع تطبيقي كامل

ابنِ مشروع:

```text
Kodraq Backend Platform
```

المكونات:

```text
FastAPI
PostgreSQL
Redis
RabbitMQ
Celery
WebSockets
RBAC
Docker
GitHub Actions
```

---

# 106. Repository Structure

```text
kodraq-backend/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── security.yml
│       ├── deploy-staging.yml
│       ├── deploy-production.yml
│       └── rollback.yml
├── app/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── migrations/
├── scripts/
│   ├── smoke.sh
│   ├── deploy.sh
│   └── rollback.sh
├── Dockerfile
├── docker-compose.ci.yml
├── pyproject.toml
└── README.md
```

---

# 107. CI Requirements

على PR:

```text
[ ] lint
[ ] format
[ ] type check
[ ] unit tests
[ ] integration tests
[ ] coverage
[ ] security checks المناسبة
[ ] Docker build validation
```

ولا يوجد أي deploy production من PR غير موثوقة.

---

# 108. Staging Requirements

على `main` أو release trigger حسب الاستراتيجية:

```text
build
↓
push registry
↓
deploy staging
↓
migrate safely
↓
smoke
↓
observe
```

---

# 109. Production Requirements

```text
[ ] immutable artifact
[ ] environment protection
[ ] least privilege
[ ] OIDC or equivalent short-lived identity
[ ] serialized deployment
[ ] smoke test
[ ] observability
[ ] rollback path
```

---

# 110. Rollback Workflow

فكرة:

```yaml
on:
  workflow_dispatch:
    inputs:
      image_digest:
        description: "Exact image digest"
        required: true
```

لكن لا تجعل input حرًا بدون validation.

يجب التحقق من:

```text
registry allowlist
valid digest
artifact exists
environment authorization
```

---

# 111. Failure Simulations

افهم CI بالنار الآمنة.

## Test failure

```python
assert 1 == 2
```

النتيجة:

```text
CI fails
↓
merge blocked
```

## Lint failure

أضف rule violation.

## Type failure

```python
def value() -> str:
    return 123
```

مع type configuration مناسبة سيظهر failure.

## Docker failure

تعمد missing file في branch تدريبية.

## Smoke failure

وجّه smoke إلى URL خاطئ وتأكد أن promotion تتوقف.

## Deployment race

شغل deploy مرتين وتحقق من concurrency policy.

---

# 112. Security Exercises

1. قلل `GITHUB_TOKEN` من write إلى read.
2. أضف environment approval.
3. افصل staging identity عن production identity.
4. اختبر أن secret غير موجود في PR workflow.
5. جرب workflow على fork في repository تجريبي.
6. راجع كل third-party Action.
7. جرّب SHA pinning في branch تدريبية.

---

# 113. Advanced Challenge: BOLA Regression

اختبر:

```text
User A
↓
GET /documents/<document-owned-by-B>
↓
403/404 according to your policy
```

ثم اجعل test blocking في CI.

---

# 114. Advanced Challenge: Multi-tenant RAG

اختبر:

```text
Tenant A query
↓
retriever
↓
documents from A only
```

ولا تسمح بأن تمر filters إلى retrieval من client كـtrusted authorization.

الـbackend هو الذي يحدد authorization scope.

---

# 115. Advanced Challenge: Artifact Promotion

نفّذ:

```text
build image
↓
record digest D1
↓
staging D1
↓
approval
↓
production D1
```

ثم أثبت في logs أن staging وproduction استخدما D1 نفسه.

---

# 116. Advanced Challenge: Production Rollback

نفّذ:

```text
D10 production
↓
incident
↓
rollback D9
↓
smoke
```

بدون rebuild.

---

# 117. Advanced Challenge: Migration Compatibility

صمّم migration تغيّر:

```text
users.name
→
users.display_name
```

مع الحفاظ على تشغيل الإصدار السابق فترة transition.

وثّق:

```text
expand
backfill
switch
contract
```

---

# 118. Advanced Challenge: Monorepo

لديك:

```text
backend/
worker/
shared/
frontend/
```

صمّم workflow بحيث:

```text
backend change → backend CI
worker change → worker CI
shared change → affected backend + worker
frontend change → frontend CI
```

ولا تعتمد على path filters وحدها إذا كانت dependency graph أعقد.

---

# 119. Advanced Challenge: Canary

صمّم release بحيث:

```text
1%
↓
metrics
↓
10%
↓
metrics
↓
25%
↓
metrics
↓
100%
```

حدد guardrails مثل:

```text
error rate
p95 latency
business failure rate
```

---

# 120. Advanced Challenge: AI Evaluation

في RAG/AI backend:

```text
PR
↓
small golden dataset
↓
retrieval evaluation
↓
generation checks
↓
cost guard
```

واجعل full expensive evaluation في release/nightly pipeline.

---

# 121. Interview — Basic

### ما هو CI؟
آلية آلية متكررة للتحقق من التغييرات قبل/حول الدمج.

### ما هو CD؟
إيصال التغييرات إلى environments بطريقة آلية أو شبه آلية.

### ما هو Runner؟
الجهاز الذي ينفذ job.

### ما هو Workflow؟
ملف automation يعرّف events وjobs وsteps.

### ما الفرق بين cache وartifact؟
Cache لتسريع، artifact لحفظ/نقل output.

---

# 122. Interview — Intermediate

### لماذا `needs`؟
لبناء dependency graph بين jobs.

### لماذا `permissions`؟
للتقليل من blast radius للworkflow token.

### لماذا build once deploy many؟
لضمان أن artifact المختبر هو نفسه الذي يترقى إلى production.

### لماذا smoke tests بعد deploy؟
لأن successful process startup لا يثبت أن الخدمة تعمل بشكل صحيح.

### لماذا environments؟
لفصل deployment policy وsecrets والموافقات حسب البيئة.

---

# 123. Interview — Security

### لماذا SHA pinning؟
لأن full commit SHA أكثر ثباتًا كمرجع immutable من tag متحرك.

### لماذا OIDC؟
لتقليل الاعتماد على cloud credentials طويلة العمر المخزنة كـsecrets.

### لماذا cache قد تكون خطرًا؟
لأن workflow غير موثوق قد يحاول إدخال ملفات أو محتوى يستفيد منه workflow موثوق لاحقًا.

### لماذا Fork PR خطرة؟
لأن PR author قد يتحكم في الكود الذي ستشغله CI.

### لماذا لا نضع production secrets في PR workflow؟
لأن execution context قد يشغل code غير موثوق.

---

# 124. Interview — Advanced

### صمّم zero-downtime deployment مع DB migration.
ناقش:

```text
backward compatibility
expand/contract
migration ordering
rolling deploy
read/write compatibility
rollback/fix-forward
```

### صمّم CI لـ20 microservices.
ناقش:

```text
affected services
contract tests
shared workflows
artifact boundaries
parallelism
release orchestration
```

### صمّم Production deployment باستخدام OIDC.
ناقش:

```text
GitHub permissions
OIDC claims
cloud trust policy
IAM least privilege
environment protection
```

---

# 125. Pipeline Failure Matrix

| المرحلة | ماذا تثبت؟ | ماذا تفعل عند failure؟ |
|---|---|---|
| lint | style/rules | أصلح الكود |
| format | formatting | عدل code |
| typecheck | static assumptions | أصلح types |
| unit | local logic | أصلح business logic/test |
| integration | boundaries | أصلح integration |
| security | risk signals | investigate/remediate |
| build | artifact creation | أصلح build |
| staging | deployment path | investigate deployment |
| smoke | service behavior | stop promotion |
| production post-check | real service health | rollback/fix-forward |

---

# 126. Golden Rules

## Rule 1

> CI ليست pytest فقط؛ CI هي نظام ثقة.

## Rule 2

> CD ليست `docker restart`؛ CD هي controlled delivery.

## Rule 3

> Build once, promote the same artifact.

## Rule 4

> Least privilege في GitHub والـcloud معًا.

## Rule 5

> Workflow code نفسه security-sensitive code.

## Rule 6

> لا تمنح untrusted PR code production secrets.

## Rule 7

> Cache للسرعة، Artifact للoutput/evidence.

## Rule 8

> Database migrations جزء من deployment architecture.

## Rule 9

> Rollback يجب أن يكون مخططًا قبل أول deployment.

## Rule 10

> كل security regression مهم يجب أن يتحول إلى test.

## Rule 11

> Fast PR feedback، Deep release validation.

## Rule 12

> ما لا يمكنك trace له لا يمكنك تشخيصه بسهولة.

---

# 127. الـMental Model النهائي

```text
                    SOURCE
                      │
                      ▼
                Pull Request
                      │
                      ▼
             ┌─────────────────┐
             │       CI        │
             ├─────────────────┤
             │ lint            │
             │ format          │
             │ typecheck       │
             │ unit            │
             │ integration     │
             │ security        │
             │ contract        │
             └────────┬────────┘
                      │
                  PASS ONLY
                      │
                      ▼
                     BUILD
                      │
                      ▼
             IMMUTABLE ARTIFACT
                      │
                      ▼
                   STAGING
                      │
                      ▼
               SMOKE / HEALTH
                      │
                      ▼
              APPROVAL / POLICY
                      │
                      ▼
                 PRODUCTION
                      │
            ┌─────────┴─────────┐
            ▼                   ▼
       OBSERVABILITY        ROLLBACK
```

هنا يصبح CI/CD جزءًا من هندسة النظام نفسها، وليس مجرد tooling.

---

# 128. ماذا يجب أن تتقنه بعد الدرس؟

يجب أن تكون قادرًا على شرح وتنفيذ:

```text
Workflow
Event
Job
Step
Runner
Action
needs
matrix
permissions
GITHUB_TOKEN
secrets
environments
cache
artifacts
service containers
Docker build
registry
OIDC
concurrency
smoke tests
migrations
rollback
blue/green
canary
GitOps
security hardening
```

والأهم أن تستطيع أخذ Backend مبني بـFastAPI وتحويله من:

```text
"works on my machine"
```

إلى:

```text
repeatable
validated
secure
observable
deployable
recoverable
```

---

# 129. Definition of Done

لا تقل إنك أتقنت CI/CD لأنك كتبت:

```yaml
name: CI
```

اعتبر الدرس مكتملًا عندما تستطيع التعامل مع:

```text
Test failure
Dependency failure
Cache miss
Docker failure
Registry failure
Migration failure
Staging failure
Smoke failure
Production approval
Concurrent deploys
Artifact mismatch
OIDC failure
Secret exposure risk
Rollback
```

وتستطيع الإجابة عن:

```text
what failed?
why?
where?
should we retry?
should we stop?
should we rollback?
what evidence do we preserve?
```

---

# 130. مشروع التخرج في هذا الدرس

ابنِ backend حقيقي يحتوي على:

```text
FastAPI
PostgreSQL
Redis
RabbitMQ
Celery
WebSockets
RBAC
Docker
GitHub Actions
```

## Pull Request

```text
lint
format
mypy
unit
integration
security
Docker build
```

## Merge to main

```text
build
push
staging deploy
smoke
```

## Release tag

```text
promote exact artifact
production approval
deploy
smoke
post-deploy checks
```

## Emergency

```text
rollback exact previous artifact
```

هذه المنظومة هي أفضل طريقة لتحويل المفاهيم إلى engineering skill حقيقية.

---

# 131. المراجع الرسمية

## GitHub Actions

- Reference: https://docs.github.com/en/actions/reference
- Workflows: https://docs.github.com/en/actions/concepts/workflows-and-actions/workflows
- Continuous Deployment: https://docs.github.com/en/actions/get-started/continuous-deployment
- Deployments and Environments: https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
- Deployment Environments: https://docs.github.com/en/actions/concepts/workflows-and-actions/deployment-environments
- Dependency Caching: https://docs.github.com/en/actions/concepts/workflows-and-actions/dependency-caching
- Dependency Caching Reference: https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching
- Workflow Artifacts: https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts
- Secure Use Reference: https://docs.github.com/en/actions/reference/security/secure-use
- OIDC Reference: https://docs.github.com/en/actions/reference/security/oidc
- OIDC with Cloud Providers: https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-cloud-providers

## Official Action Repositories

- checkout: https://github.com/actions/checkout
- setup-python: https://github.com/actions/setup-python
- setup-python releases: https://github.com/actions/setup-python/releases
- upload-artifact releases: https://github.com/actions/upload-artifact/releases
- build-push-action releases: https://github.com/docker/build-push-action/releases

---

# 132. ملاحظة عن الإصدارات

إصدارات GitHub Actions تتغير مع الوقت. أمثلة هذا الدرس تستخدم major versions حديثة تم التحقق منها وقت كتابة الملف، لكن في Production:

1. راجع release notes.
2. تحقق من breaking changes.
3. استخدم policy للتحديثات.
4. فضّل full-length SHA pinning في البيئات عالية الحساسية.
5. استخدم Dependabot/Renovate أو عملية تحديث موثقة.

---

# 133. اختصار الدرس في 12 سطرًا

```text
1. Commit code.
2. Open PR.
3. CI validates.
4. Bad change stops.
5. Good change merges.
6. Build immutable artifact.
7. Store/protect artifact.
8. Deploy staging.
9. Run smoke tests.
10. Promote the same artifact.
11. Deploy production with controlled identity/policy.
12. Observe and rollback when needed.
```

هذا هو CI/CD الذي تحتاجه كـBackend Engineer.
