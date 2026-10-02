# Backend Engineering Mastery
# بناء نظام صلاحيات متقدم (RBAC) وتأمين الـAPIs باستخدام FastAPI

> **الهدف من هذا الدرس:** الانتقال من فكرة "المستخدم مسجل دخول" إلى نظام Authorization قابل للتوسع، واضح، قابل للاختبار، ومناسب للأنظمة متعددة المستخدمين والـtenants، مع فهم عميق لـAuthentication، RBAC، Permissions، OAuth2 Scopes، JWT، Object-Level Authorization، Function-Level Authorization، Multi-Tenancy، Policy Enforcement، Security Testing، وDefense-in-Depth.

---

## 1. أول قاعدة: Authentication ليست Authorization

من أكبر الأخطاء في تصميم الـAPIs أن يتم التعامل مع Authentication وAuthorization كأنهما نفس الشيء.

### Authentication

السؤال:

> **من أنت؟**

مثلًا السيرفر يثبت أن:

```text
user_id = 42
```

### Authorization

السؤال:

> **ماذا يسمح لك user 42 أن تفعل؟ وعلى أي resource؟**

مثال:

```text
user_id = 42
role = editor

can:
    read:article
    update:article

cannot:
    delete:user
    manage:billing
```

إذن:

```text
Authentication
    ↓
Who are you?
    ↓
Authorization
    ↓
What can you do?
```

الـOWASP API Security Top 10 يميز بين مشاكل Authentication ومشاكل Authorization على مستوى object/function/property، لأن نجاح المصادقة لا يعني أن المستخدم مخوّل بتنفيذ كل شيء. citeturn203318search1turn203318search2

---

# 2. لماذا RBAC؟

RBAC = **Role-Based Access Control**.

بدل أن تكتب صلاحيات لكل مستخدم بشكل مباشر:

```text
Ahmed -> can_create_user
Ahmed -> can_delete_user
Ahmed -> can_view_reports

Ali -> can_create_user
Ali -> can_view_reports
```

ننشئ Roles:

```text
admin
editor
support
viewer
```

ثم نربط:

```text
admin
    ↓
permissions

editor
    ↓
permissions

support
    ↓
permissions
```

ثم:

```text
Ahmed -> admin
Ali   -> editor
Sara  -> support
```

بهذا أصبح الوصول أسهل في الإدارة والمراجعة.

---

# 3. أهم Mental Model

لا تفكر في RBAC بهذا الشكل فقط:

```text
User -> Role
```

بل فكر:

```text
User
  ↓
Role(s)
  ↓
Permission(s)
  ↓
Action
  ↓
Resource
  ↓
Context
```

مثال:

```text
User 42
  ↓
editor
  ↓
article:update
  ↓
Article 100
  ↓
tenant_id = 7
```

لكن وجود permission `article:update` لا يكفي وحده.

قد يكون المستخدم مسموحًا له بتعديل **مقالاته أو مقالات tenant الخاص به فقط**.

وهنا ننتقل من RBAC البسيط إلى:

# Resource-Level Authorization

و:

# Context-Aware Authorization

---

# 4. RBAC الأساسي

لنبدأ بالنموذج الكلاسيكي:

```text
User
  |
  +--> Role
           |
           +--> Permission
```

مثال:

```text
User: Ahmed
Role: editor

editor:
    article:read
    article:create
    article:update
```

لو حاول Ahmed:

```http
DELETE /articles/123
```

وكانت permission المطلوبة:

```text
article:delete
```

فيجب رفض العملية.

---

# 5. Permission هي الوحدة الأهم

Role مفيدة للإدارة، لكن القرار النهائي الأفضل أن يكون مبنيًا على permission واضحة.

مثال:

```text
users:read
users:create
users:update
users:delete

articles:read
articles:create
articles:update
articles:delete

billing:read
billing:refund

reports:read
reports:export
```

هذا أفضل من:

```text
if user.role == "admin":
    ...
```

في كل endpoint.

---

# 6. لا تجعل الـRole هي الـAuthorization Logic كلها

سيئ:

```python
if user.role == "admin":
    return data
```

ثم في مكان آخر:

```python
if user.role in {"admin", "editor"}:
    ...
```

ثم:

```python
if user.role == "owner":
    ...
```

بعد فترة تصبح الشروط موزعة في كل مكان.

الأفضل:

```text
Role
  ↓
Permission set
  ↓
Central authorization policy
```

وهذا يجعل النظام أسهل للتحليل والمراجعة.

OWASP توصي بآلية Authorization متسقة وواضحة تُستدعى من جميع الوظائف الحساسة، مع سياسة **deny by default**. citeturn203318search5turn203318search10

---

# 7. Deny by Default

قاعدة ذهبية:

> **إذا لم نعرف أن المستخدم مسموح له، نرفض.**

سيئ:

```python
if permission:
    allow()
else:
    maybe_allow()
```

الأفضل:

```python
if permission:
    allow()
else:
    deny()
```

أو حتى أفضل، صمّم النظام بحيث تكون القاعدة الافتراضية نفسها:

```text
NO explicit permission
        ↓
      DENY
```

OWASP Authorization Cheat Sheet توصي صراحةً بمنهجية deny-by-default بدل افتراض السماح عند عدم وجود rule مطابقة. citeturn203318search10

---

# 8. 401 مقابل 403

هذه نقطة يجب أن تثبت.

## 401 Unauthorized

في سياق HTTP APIs تعني عادة أن العميل يحتاج إلى Authentication صحيحة أو أن credentials غير صالحة.

مثال:

```text
No token
Expired token
Invalid token
```

## 403 Forbidden

المستخدم معروف/authenticated، لكن لا يملك الصلاحية المطلوبة.

مثال:

```text
Authenticated user
but missing users:delete
```

إذن:

```text
401 -> identity/authentication problem
403 -> authorization problem
```

---

# 9. لا تجعل frontend هو المسؤول عن الأمن

يمكن للـfrontend أن يخفي زرًا:

```text
Delete User
```

لكن هذا ليس Authorization.

المهاجم يستطيع إرسال:

```http
DELETE /users/42
```

مباشرة.

لذلك:

```text
Frontend UI
    ↓
UX restriction

Backend Authorization
    ↓
Security enforcement
```

كل access control يجب أن يتم على السيرفر. citeturn467134search3

---

# 10. المشكلة الأخطر: BOLA / IDOR

تخيل endpoint:

```http
GET /orders/1001
```

المستخدم مسموح له عمومًا قراءة orders.

السيرفر يقرأ:

```python
order = await repo.get(order_id)
return order
```

المستخدم يغيّر:

```http
GET /orders/1002
```

وقد تكون order 1002 تخص مستخدمًا آخر.

لو رجعت البيانات، لديك:

# Broken Object Level Authorization

وتُعرف أحيانًا في أمثلة أقدم باسم IDOR.

OWASP تصنف BOLA كـAPI1:2023 وتحذر من أن كل endpoint يستخدم object ID من العميل ويصل إلى object يجب أن ينفذ authorization على مستوى الـobject نفسه. citeturn203318search4turn203318search2

---

# 11. لماذا UUID لا يحل BOLA؟

البعض يقول:

> "سأستخدم UUID بدل integer."

هذا قد يقلل سهولة التخمين، لكنه ليس Authorization.

إذا كان المستخدم حصل على UUID بطريقة ما:

```text
GET /documents/<uuid>
```

والسيرفر لا يتحقق من الملكية، ما زالت المشكلة موجودة.

OWASP توضح أن نوع الـidentifier نفسه لا يلغي ضرورة object-level authorization؛ المهم هو التحقق من أن المستخدم يملك الحق في الوصول للـobject المطلوب. citeturn203318search4

---

# 12. الحل الصحيح لـBOLA

بدل:

```python
order = await repository.get(order_id)
```

اجعل الاستعلام نفسه يعبّر عن نطاق الوصول إن أمكن:

```python
order = await repository.get_for_user(
    order_id=order_id,
    user_id=current_user.id,
)
```

أو:

```sql
SELECT *
FROM orders
WHERE id = :order_id
  AND owner_id = :user_id;
```

وبهذا:

```text
Object lookup
+
Authorization scope
```

في نفس العملية.

هذا يقلل خطر أن تنسى فحص authorization بعد جلب object.

---

# 13. لماذا Authorization قبل إظهار object؟

سيئ:

```python
order = await repo.get(order_id)

if not user_can_access(order):
    raise HTTPException(403)

return order
```

هذا يمكن أن يكون صحيحًا إذا نُفذ بعناية.

لكن في أنظمة كبيرة من الأفضل أحيانًا أن يكون repository query نفسه محددًا بالنطاق:

```python
order = await repo.get_accessible_order(
    order_id,
    actor=current_user,
)
```

حتى لا يصبح من السهل نسيان authorization في مسار آخر.

---

# 14. Broken Function Level Authorization

نوع آخر:

المستخدم العادي يستطيع الوصول إلى:

```http
GET /admin/users
```

فقط لأنه عرف endpoint.

هذا:

# Broken Function Level Authorization

OWASP تصنفه API5:2023، وتوصي بآلية متسقة للـauthorization مع deny-by-default وحماية الوظائف الإدارية تحديدًا. citeturn203318search5

---

# 15. RBAC لا يعني Function-Level فقط

قد يكون لديك:

```text
admin
editor
support
viewer
```

لكن authorization يجب أن يغطي على الأقل:

```text
Function
Object
Property
Tenant
Context
```

لدينا:

```text
Function Level Authorization
Object Level Authorization
Property Level Authorization
```

وكلها مهمة.

---

# 16. Broken Object Property Level Authorization

تخيل endpoint:

```http
PATCH /users/me
```

والـrequest:

```json
{
  "name": "Ahmed",
  "role": "admin"
}
```

لو استخدمت generic model binding وأنتجت:

```python
user.role = payload.role
```

فالمستخدم قد يرفع نفسه إلى admin.

هذه مشكلة Property-Level Authorization / Mass Assignment.

OWASP توصي بأن تسمح فقط بالخصائص التي يسمح الـbusiness contract بتعديلها، وأن تستخدم response/input schemas صريحة بدل ربط input العميل مباشرةً بكائن داخلي. citeturn203318search8

---

# 17. لا تستخدم نفس Schema لكل شيء

سيئ:

```python
class User(BaseModel):
    id: int
    email: str
    password_hash: str
    role: str
    is_active: bool
```

ثم:

```python
@app.patch("/users/{id}")
async def update_user(payload: User):
    ...
```

هذا يفتح الباب لتعديل fields داخلية.

الأفضل:

```python
class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
```

والـadmin update قد يكون له contract منفصل:

```python
class AdminUserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    role: str | None = None
    is_active: bool | None = None
```

---

# 18. RBAC Database Model

النموذج التقليدي:

```text
users
roles
permissions
user_roles
role_permissions
```

العلاقات:

```text
User N <----> N Role
Role N <----> N Permission
```

مثلًا:

```text
users
-----
id | email
1  | ahmed@example.com
2  | ali@example.com
```

```text
roles
-----
id | name
1  | admin
2  | editor
3  | viewer
```

```text
permissions
-----------
id | name
1  | users:read
2  | users:update
3  | users:delete
4  | articles:read
5  | articles:update
```

```text
user_roles
----------
user_id | role_id
1       | 1
2       | 2
```

```text
role_permissions
-----------------
role_id | permission_id
1       | 1
1       | 2
1       | 3
2       | 1
2       | 4
2       | 5
```

---

# 19. لماذا Many-to-Many؟

لأن المستخدم قد يكون لديه أكثر من Role:

```text
Ahmed
  |
  +--> editor
  +--> reviewer
```

والـrole يمكن أن تخص عدة users.

وكذلك permission قد تنتمي لعدة roles.

هذا يعطي مرونة أكبر من:

```text
users.role = "admin"
```

في المشاريع الكبيرة.

---

# 20. هل نحتاج Multiple Roles دائمًا؟

لا.

ابدأ:

```text
User -> Role
```

إذا كان domain بسيطًا.

ثم:

```text
User -> N Roles
```

عندما تحتاج ذلك.

لا تضف complexity غير ضرورية.

---

# 21. Role Hierarchy

أحيانًا:

```text
admin
  > manager
      > editor
          > viewer
```

لكن انتبه.

لو قررت أن:

```text
admin inherits all manager permissions
```

فيجب أن يكون هذا واضحًا ومختبرًا.

وإلا تصبح hierarchy نفسها مصدر أخطاء.

---

# 22. أفضل منطق: Permissions Explicitly

بدل:

```python
if role == "admin":
    allow
```

الأفضل:

```python
permissions = {
    "users:read",
    "users:update",
    "users:delete",
}
```

ثم:

```python
if "users:delete" in permissions:
    allow
```

وهذا يجعل role مجرد grouping mechanism.

---

# 23. Permission Naming

اجعل permission names predictable:

```text
resource:action
```

مثل:

```text
users:read
users:create
users:update
users:delete

articles:read
articles:create
articles:update
articles:delete

reports:read
reports:export

billing:read
billing:refund
```

أحيانًا تحتاج:

```text
articles:publish
articles:moderate
```

حسب domain.

---

# 24. Granularity

Permission واسعة جدًا:

```text
admin:all
```

قد تكون غير مفيدة كآلية دقيقة.

Permission ضيقة جدًا:

```text
article:123:field:title:write
```

قد تصبح إدارية بشكل مبالغ فيه.

التصميم الجيد يختار granularity التي تعكس business boundaries.

---

# 25. Least Privilege

مبدأ:

> أعط أقل صلاحيات لازمة لإنجاز المهمة.

مثال:

```text
report_reader
```

لا يحتاج:

```text
users:delete
billing:refund
system:admin
```

OWASP توصي بتطبيق مبدأ أقل صلاحية مع deny-by-default والمراجعة الدورية للصلاحيات. citeturn203318search10

---

# 26. Permission Explosion

خطأ:

```text
1000 permission
```

والفريق لا يفهمها.

الحل ليس تقليل الأمن، بل تصميم permission taxonomy واضح:

```text
users:* 
articles:* 
reports:* 
```

مع permissions محددة فعلًا عند enforcement.

---

# 27. Roles ليست Business Logic

لا تكتب business logic مثل:

```python
if user.role == "editor":
    publish_article()
```

اسأل:

```text
Does the user have articles:publish?
```

ثم اترك role mapping خارج الـbusiness operation.

---

# 28. Authorization Layer

يمكن بناء abstraction:

```python
class AuthorizationService:
    async def check(
        self,
        actor,
        permission: str,
        resource=None,
    ) -> bool:
        ...
```

ثم:

```python
await authorization.check(
    actor=current_user,
    permission="articles:update",
    resource=article,
)
```

هذا أفضل من شروط متفرقة في كل route.

---

# 29. Permission Checker بسيط

```python
from typing import Iterable


def has_permission(
    user_permissions: Iterable[str],
    required: str,
) -> bool:
    return required in set(user_permissions)
```

ثم:

```python
if not has_permission(
    current_user.permissions,
    "users:delete",
):
    raise HTTPException(status_code=403)
```

لكن production RBAC عادةً يحتاج التعامل مع object/context وليس permission string فقط.

---

# 30. FastAPI Dependencies للـAuthorization

FastAPI تجعل Dependency Injection مناسبة لوضع authentication/authorization كطبقة مشتركة.

مثال:

```python
from fastapi import Depends, HTTPException


def require_permission(permission: str):
    async def dependency(current_user = Depends(get_current_user)):
        if permission not in current_user.permissions:
            raise HTTPException(
                status_code=403,
                detail="Forbidden",
            )
        return current_user

    return dependency
```

ثم:

```python
@app.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user = Depends(
        require_permission("users:delete")
    ),
):
    ...
```

---

# 31. مشكلة هذا الأسلوب

هو ممتاز للـfunction-level authorization.

لكن:

```text
users:delete
```

لا يجيب عن السؤال:

> هل يستطيع حذف **هذا المستخدم تحديدًا**؟

هنا نحتاج object-level policy.

---

# 32. Object-Level Authorization

مثال:

```python
async def can_delete_user(
    actor,
    target_user,
) -> bool:
    if "users:delete" not in actor.permissions:
        return False

    if actor.tenant_id != target_user.tenant_id:
        return False

    if target_user.id == actor.id:
        return False

    return True
```

لاحظ أن القرار أصبح:

```text
permission
+
tenant
+
resource relationship
```

---

# 33. Authorization Decision = Policy Evaluation

يمكن التفكير في القرار كدالة:

```text
Allow?
=
Policy(
    subject,
    action,
    resource,
    context,
)
```

مثال:

```text
subject = user 42
action = update
resource = article 100
context = tenant 7
```

ثم:

```text
Allow if:
    user has articles:update
    AND article.tenant_id == user.tenant_id
    AND user can edit this article
```

هذه العقلية أقرب إلى systems مثل Policy Engines وABAC.

---

# 34. RBAC مقابل ABAC

## RBAC

```text
User -> Role -> Permission
```

## ABAC

```text
Subject attributes
Resource attributes
Action
Environment/context
```

مثال:

```text
allow if:
    user.department == resource.department
    AND action == "read"
    AND request.ip in corporate_network
```

RBAC بسيط وواضح.

ABAC أكثر مرونة لكنه أكثر تعقيدًا.

---

# 35. RBAC + Context

في الأنظمة الحقيقية غالبًا لا تختار:

```text
RBAC OR ABAC
```

بل:

```text
RBAC
+
Object ownership
+
Tenant isolation
+
Context checks
```

مثال:

```text
Role = editor
Permission = articles:update
Tenant = 7
Owner/editorial scope = category:sports
```

ثم decision يجمع كل ذلك.

---

# 36. Multi-Tenancy

في SaaS لديك:

```text
tenant A
  users
  projects
  invoices

tenant B
  users
  projects
  invoices
```

الخطر:

```text
user from tenant A
        ↓
GET /projects/200
        ↓
project belongs to tenant B
```

إذا رجعت المشروع، لديك cross-tenant data breach.

---

# 37. Tenant Isolation Rule

أي query تخص tenant يجب أن تكون scoped:

```python
project = await repository.get(
    project_id=project_id,
    tenant_id=current_user.tenant_id,
)
```

وليس:

```python
project = await repository.get(project_id)
```

ثم الاعتماد على الذاكرة لتذكر authorization.

---

# 38. Stronger Repository Contract

بدل:

```python
get(project_id)
```

اجعل:

```python
get_for_tenant(
    project_id,
    tenant_id,
)
```

أو:

```python
query_accessible_projects(actor)
```

هذا يجعل tenant isolation جزءًا من contract نفسه.

---

# 39. Authorization على Query Set

ليس دائمًا من الأفضل جلب كل objects ثم filter في Python.

سيئ:

```python
projects = await repo.get_all()

allowed = [
    p for p in projects
    if can_read(actor, p)
]
```

هذا قد يسبب:

```text
Data exposure inside process
Memory cost
Performance cost
Security bugs
```

الأفضل أن يكون النطاق جزءًا من query قدر الإمكان:

```sql
SELECT *
FROM projects
WHERE tenant_id = :tenant_id
```

ثم تضيف شروط policy الأخرى.

---

# 40. Permission Matrix

قبل كتابة code، اصنع matrix:

| Role | users:read | users:update | users:delete | articles:publish | billing:refund |
|---|---:|---:|---:|---:|---:|
| viewer | ✓ | - | - | - | - |
| editor | ✓ | - | - | ✓ | - |
| manager | ✓ | ✓ | - | ✓ | - |
| admin | ✓ | ✓ | ✓ | ✓ | ✓ |

هذه ليست security enforcement وحدها؛ هي documentation وdesign artifact.

---

# 41. Authorization Matrix للـObjects

قد تحتاج جدولًا آخر:

| Action | Self | Same tenant | Any tenant | Admin |
|---|---:|---:|---:|---:|
| Read profile | ✓ | حسب policy | - | ✓ |
| Update profile | ✓ | حسب policy | - | ✓ |
| Delete user | - | manager+ | - | ✓ |
| View billing | - | billing role | - | ✓ |

هذا يمنع خلط role permission مع resource scope.

---

# 42. JWT: ما الذي يفعله؟

JWT هو token format يمكن أن يحمل claims موقعة.

مثال payload مفاهيمي:

```json
{
  "sub": "42",
  "iss": "https://auth.example.com",
  "aud": "api.example.com",
  "exp": 1790937600,
  "scope": "users:read articles:read",
  "jti": "token-123"
}
```

لكن توقيع JWT وحده لا يعني أن كل claim مناسب أو أن token صالح لهذا API.

OWASP توصي بالتحقق من claims مثل `iss`, `aud`, `exp`, و`nbf` بحسب تصميم الثقة، وتحذر من issuer/audience confusion. citeturn467134search5turn467134search8

---

# 43. لا تثق في JWT لمجرد أنه decoded

هذه خطيرة:

```python
payload = jwt.decode(..., options={"verify_signature": False})
```

أو قراءة:

```text
role = payload["role"]
```

بدون تحقق كامل من token authenticity وclaims المناسبة.

قاعدة:

```text
Decode != Verify
```

---

# 44. JWT Authorization Claims

يمكن أن يحمل JWT:

```text
sub
scope
roles
tenant_id
jti
iss
aud
exp
nbf
```

لكن لا تضع في token كل business state.

JWT يتحرك مع كل request، لذلك حجمه مهم، كما أن claim قد يصبح stale إذا تغيرت صلاحيات المستخدم بعد إصدار token.

---

# 45. JWT وRevocation

ميزة JWT أن السيرفر يمكنه التحقق منه محليًا.

المشكلة:

```text
User role changed from admin -> viewer
```

لكن token القديم قد يظل صالحًا حتى `exp` إذا لم توجد آلية إضافية.

الحلول الممكنة حسب التصميم:

```text
short-lived access tokens
refresh token rotation
jti denylist
session/version checks
central introspection
```

OWASP تذكر استخدام `jti` مع denylist عند الحاجة إلى invalidation قبل انتهاء JWT. citeturn467134search5

---

# 46. FastAPI وOAuth2 Scopes

FastAPI تدعم OAuth2 scopes مباشرة باستخدام `Security` و`SecurityScopes`.

الـscope هو string تمثل permission أو capability، مثل:

```text
users:read
users:write
articles:publish
```

FastAPI تدمج scopes مع OpenAPI، لكن enforce الحقيقي يجب أن يتم في كود authorization نفسه؛ توثيق FastAPI يوضح ذلك صراحة. citeturn467134search1

---

# 47. Scope ليس Role

لا تخلط:

```text
role = admin
```

مع:

```text
scope = users:read
```

Role:

```text
grouping of permissions
```

Scope:

```text
specific permission/capability granted to a token/client
```

يمكنك تصميم:

```text
admin role
    ↓
users:read
users:write
users:delete
```

ثم إصدار token يحتوي subset حسب حاجة العميل.

---

# 48. FastAPI Security Scopes

المفهوم:

```python
from fastapi import Security

@app.get("/users/me")
async def read_user(
    current_user = Security(
        get_current_user,
        scopes=["users:read"],
    )
):
    ...
```

FastAPI تجمع scopes المطلوبة داخل dependency tree عبر `SecurityScopes`. citeturn467134search1

---

# 49. مثال `SecurityScopes`

الفكرة المبسطة:

```python
async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
):
    token_data = verify_token(token)

    for required in security_scopes.scopes:
        if required not in token_data.scopes:
            raise HTTPException(
                status_code=403,
                detail="Not enough permissions",
            )

    return user
```

FastAPI توضح أن نفس dependency تستطيع معرفة الـscopes المطلوبة حسب الـendpoint الذي استُخدمت فيه. citeturn467134search1

---

# 50. Password Storage

كلمات المرور لا يجب حفظها plaintext.

ولا تستخدم:

```text
SHA-256(password)
MD5(password)
```

لمجرد أنها hashes.

OWASP توصي بخوارزميات password hashing adaptive مثل Argon2id أو bcrypt أو PBKDF2، مع salt فريد لكل password، وتوصي حاليًا بـArgon2id كخيار مفضل عندما يكون متاحًا. citeturn467134search2

FastAPI تعرض في أمثلة OAuth2 الحالية استخدام `pwdlib` مع Argon2-based hashes. citeturn467134search7

---

# 51. Authentication Flow

التدفق الأساسي:

```text
Client
  |
  | username + password
  v
Auth endpoint
  |
  +--> verify password hash
  |
  +--> load user
  |
  +--> determine roles/permissions
  |
  `--> issue token/session
```

بعد ذلك:

```text
Client
  |
  | Bearer token
  v
FastAPI
  |
  +--> Verify token
  |
  +--> Identify actor
  |
  +--> Authorize action
  `--> Execute business logic
```

---

# 52. Cookie مقابل Bearer Token

اختيار authentication transport يعتمد على نوع client والهندسة الكاملة.

في browser-based applications، OWASP تحذر من تخزين access tokens/session IDs/refresh tokens في `localStorage` أو `sessionStorage` لأنها تصبح متاحة لأي JavaScript يعمل على origin نفسه في حال XSS؛ وتوصي في سيناريوهات المتصفح باستخدام `HttpOnly`, `Secure`, و`SameSite` cookies أو BFF pattern حسب التصميم. citeturn467134search0

لا تجعل هذه المعلومة قاعدة عمياء لكل mobile/native client؛ storage model يختلف حسب نوع التطبيق.

---

# 53. JWT Claims التي يجب التفكير فيها

لـaccess token، قد تحتاج:

```text
sub
iss
aud
exp
nbf
jti
scope
```

ولا تضع secrets داخل JWT.

ولا تضع بيانات حساسة بلا داعٍ لمجرد أن الـpayload encoded.

JWT payload ليس encryption تلقائيًا.

---

# 54. `sub` هو هوية الـSubject

مثلاً:

```json
{
  "sub": "user:42"
}
```

استخدم identity مستقرة وواضحة.

لا تجعل client يحدد `sub` ثم تثق به.

المصدر هو token الموقّع من الجهة الموثوقة.

---

# 55. `aud` مهم جدًا في الأنظمة متعددة الخدمات

تخيل:

```text
Auth Server
  |
  +--> API A
  +--> API B
```

إذا استخدمت نفس key في كل مكان ولم تتحقق من audience، قد يقبل service token صادرًا لخدمة أخرى.

OWASP تشرح مخاطر audience/issuer confusion لهذا السبب. citeturn467134search8

---

# 56. `iss`

تعني من أصدر التوكن.

مثال:

```text
iss = https://auth.example.com
```

يجب أن يعرف الـAPI issuer الموثوق الذي يتوقعه.

---

# 57. `exp`

وقت انتهاء صلاحية token.

لا تستخدم access token بلا expiration في تصميم يستدعي ذلك.

كلما طال عمر token:

```text
compromise window ↑
```

وكلما قصر جدًا:

```text
refresh complexity ↑
```

إذن القرار جزء من threat model.

---

# 58. Token لا يجب أن يحمل Authorization من دون سياسة تحديث

لو token يحتوي:

```json
{
  "role": "admin"
}
```

ثم غيرت دور المستخدم إلى viewer في DB، التوكن القديم قد لا يعرف ذلك.

الحلول:

```text
short expiry
session/version check
revocation
introspection
role lookup on sensitive operations
```

لا يوجد حل واحد يصلح لكل systems.

---

# 59. Hybrid Authorization

في الأنظمة الحساسة قد يكون التصميم:

```text
JWT
  ↓
identity + coarse permissions
  ↓
DB/policy check
  ↓
resource-level authorization
```

هذا يعطيك:

```text
fast identity verification
+
fresh resource authorization
```

بتكلفة query إضافية عند بعض العمليات.

---

# 60. لا تعمل DB Query للصلاحيات بلا داعٍ لكل طلب

لو كل request يقوم بـ:

```text
JWT verification
+
load 10 roles
+
load 100 permissions
```

يمكن أن تصبح authorization نفسها bottleneck.

استراتيجيات مثل:

```text
permission caching
short-lived tokens
policy snapshots
```

قد تقلل ذلك، لكن يجب أن تراعي invalidation/staleness.

وهنا يظهر اتصال مباشر بدرس Redis Caching.

---

# 61. Authorization Cache

يمكن تخزين permission set مثل:

```text
authz:user:42
```

لكن عند تعديل role:

```text
User 42
  editor -> viewer
```

يجب invalidate cache.

إذن:

```text
RBAC
+
Redis
=
authorization caching problem
```

وهذا يحتاج consistency strategy.

---

# 62. لا تخزن Authorization Decision بلا مدة أو invalidation

خطأ:

```text
authorization:user:42:articles:update = true
```

ثم تغيّر صلاحياته ولا تمسح الكاش.

سيظل النظام يسمح بالوصول القديم.

---

# 63. Route-Level Authorization

مثال:

```python
@app.get("/admin/users")
async def list_users(
    current_user = Depends(
        require_permission("users:read")
    )
):
    ...
```

هذا مفيد للـfunction-level.

لكن لا يغني عن object-level checks داخل الخدمة.

---

# 64. Service-Level Authorization

الأفضل أن يكون هناك check أيضًا في service/use-case boundary:

```python
class UserService:
    async def delete_user(self, actor, target_id):
        target = await self.repo.get_for_tenant(
            target_id,
            actor.tenant_id,
        )

        if not target:
            raise UserNotFoundError()

        await self.authorization.require(
            actor,
            "users:delete",
            target,
        )

        await self.repo.delete(target.id)
```

لماذا؟

لأن business logic قد تُستدعى من:

```text
HTTP route
Celery task
CLI command
Admin tool
GraphQL resolver
internal API
```

ولا تريد authorization أن تعتمد فقط على route decorator.

---

# 65. دفاع مزدوج بدون فوضى

هناك فرق بين:

```text
duplicating rules everywhere
```

وبين:

```text
central policy enforcement
at multiple security boundaries
```

نريد:

```text
HTTP layer
  ↓
coarse permission check
  ↓
Service/use-case
  ↓
object/context authorization
```

لكن القرار الأساسي يجب أن يكون centralized ومفهومًا، لا شروطًا عشوائية.

---

# 66. Policy Object

بدل:

```python
if role == "manager" and user.tenant_id == project.tenant_id:
    ...
```

موزعة في كل مكان، أنشئ policy:

```python
class ProjectPolicy:
    def can_view(self, actor, project) -> bool:
        return (
            "projects:read" in actor.permissions
            and actor.tenant_id == project.tenant_id
        )

    def can_delete(self, actor, project) -> bool:
        return (
            "projects:delete" in actor.permissions
            and actor.tenant_id == project.tenant_id
            and not project.is_protected
        )
```

---

# 67. Policy Decision Object

لو authorization معقدة جدًا، قد يفيدك decision object:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str
    policy: str
```

مثال:

```text
allowed = False
reason = "tenant_mismatch"
policy = "project.delete"
```

هذا مفيد في debugging والتدقيق والـtesting، لكن لا تُرجع تفاصيل داخلية حساسة للمهاجم.

---

# 68. Security Logs

سجل authorization failures بطريقة مفيدة:

```text
AUTHZ_DENIED
user_id=42
permission=users:delete
resource_type=user
resource_id=100
reason=tenant_mismatch
request_id=req_123
```

لكن لا تسجل:

```text
password
access_token
refresh_token
raw secrets
```

---

# 69. لا تجعل Error يكشف أكثر مما يجب

قد يكون:

```text
403 Forbidden
```

أكثر أمانًا من:

```text
User 100 belongs to tenant 7 and you are tenant 3
```

في بعض domains من الأفضل تقليل information leakage.

مثلاً endpoint قد يعيد:

```text
404 Not Found
```

بدل 403، إذا كان وجود object نفسه حساسًا.

لكن هذا قرار domain/security policy وليس قاعدة مطلقة.

---

# 70. Authentication Dependency

نريد dependency مثل:

```python
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
):
    payload = verify_access_token(token)
    user = await user_repository.get_by_id(
        int(payload["sub"])
    )

    if not user:
        raise invalid_credentials()

    return user
```

لكن الـimplementation الحقيقي يجب أن يتحقق من signature والـclaims المطلوبة ومصدر الثقة، وليس فقط `sub`.

---

# 71. Permission Dependency Factory

```python
from fastapi import Depends, HTTPException


def require_permission(permission: str):
    async def dependency(
        current_user = Depends(get_current_user),
    ):
        if permission not in current_user.permissions:
            raise HTTPException(
                status_code=403,
                detail="Forbidden",
            )
        return current_user

    return dependency
```

استخدام:

```python
@app.post("/articles")
async def create_article(
    current_user = Depends(
        require_permission("articles:create")
    ),
):
    ...
```

---

# 72. OAuth2 Scopes في FastAPI

لو كنت تستخدم OAuth2 scopes:

```python
from fastapi import Security


@app.get("/articles")
async def read_articles(
    current_user = Security(
        get_current_user,
        scopes=["articles:read"],
    ),
):
    ...
```

FastAPI توفر `SecurityScopes` حتى تستطيع dependency المركزية معرفة الـscopes المطلوبة لكل endpoint في شجرة dependencies. citeturn467134search1

---

# 73. RBAC + Scopes

يمكن أن يكون النظام:

```text
Role:
editor

Permissions:
articles:read
articles:update
articles:publish
```

وعند login/token issuance:

```text
scope:
articles:read articles:update
```

لكن لا تفترض أن scope الموجودة في token تغني عن object-level authorization.

هي غالبًا:

```text
coarse capability
```

بينما object policy تضيف:

```text
which article?
which tenant?
which state?
```

---

# 74. State-Based Authorization

أحيانًا permission نفسها لا تكفي.

مثال:

```text
articles:publish
```

لكن المقالة:

```text
status = archived
```

ولا يجوز نشرها دون workflow خاص.

إذن:

```text
permission
+
resource state
```

مثال:

```python
if article.status != "draft":
    raise PolicyDenied("article_not_publishable")
```

---

# 75. Separation of Duties

في أنظمة مالية حساسة قد تكون القاعدة:

```text
User A can create refund
User B must approve refund
```

أي أن امتلاك permission واحدة لا يعني القدرة على إكمال العملية كلها.

هذا مثال على business authorization أعمق من RBAC البسيط.

---

# 76. Role Assignment نفسها تحتاج Authorization

خطأ كبير:

```http
PATCH /users/42
{
  "role": "admin"
}
```

إذا كان المستخدم يستطيع تعديل role بنفسه، انتهى نظام RBAC.

تغيير roles يجب أن يخضع لـpermission منفصلة مثل:

```text
roles:assign
```

وغالبًا يجب أن توجد قيود إضافية:

```text
Cannot grant permissions you don't possess
Cannot assign cross-tenant roles
Cannot modify protected admin account
```

---

# 77. Privilege Escalation

أي مسار يجعل user يحصل على صلاحيات أعلى من المسموح هو:

# Privilege Escalation

أمثلة:

```text
modify own role
modify own tenant_id
set is_admin=true
assign role=admin
modify another user's permissions
```

لذلك fields مثل:

```text
role
permissions
tenant_id
is_superuser
```

ليست ordinary user-editable fields.

---

# 78. Mass Assignment Defense

لا تستخدم:

```python
user.__dict__.update(payload.model_dump())
```

ولا:

```python
for key, value in payload.items():
    setattr(user, key, value)
```

دون allowlist.

الأفضل:

```python
allowed_fields = {
    "name",
    "email",
}
```

أو، أفضل، Pydantic schema صريح لكل use case.

OWASP تنصح بأن يُسمح بتعديل الخصائص التي يسمح بها الـbusiness contract فقط، وألا يتم bind input العميل مباشرةً إلى internal objects. citeturn203318search8

---

# 79. Secure Response Schemas

لا ترجع:

```python
return db_user
```

بشكل أعمى إذا كان model يحتوي:

```text
password_hash
internal_notes
security_flags
permission_metadata
```

استخدم response model:

```python
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
```

الـOWASP توصي أيضًا بتقليل properties التي تُرجعها الـAPI للحد الأدنى المطلوب وتجنب التسريب العرضي للحقول الداخلية. citeturn203318search8

---

# 80. Superuser

قد تحتاج:

```text
is_superuser
```

لكن لا تستخدمه في كل مكان:

```python
if user.is_superuser:
    return True
```

لأنك بذلك تصنع bypass عالمي.

أفضل أن يكون واضحًا جدًا متى يسمح superuser bypass، وتكون العمليات الحساسة audited.

---

# 81. Service Account / Machine Identity

ليس كل actor إنسانًا.

قد يكون:

```text
Celery worker
CI/CD pipeline
Internal service
Webhook processor
Scheduled job
```

إذن Authorization model يجب أن يستطيع التعامل مع:

```text
Human user
Service account
Application client
```

بحسب architecture.

---

# 82. OAuth2 Scope للمستخدم وللتطبيق

في integrations قد يكون لديك:

```text
client A
```

مسموح له:

```text
reports:read
```

لكن ليس:

```text
users:delete
```

ويمكن أن يكون الـscope جزءًا من contract بين client وauthorization server.

FastAPI تدعم تعريف scopes في OpenAPI لكي تظهر كجزء من security scheme في docs. citeturn467134search1

---

# 83. API Keys

قد تحتاج service clients مثل:

```text
partner API
internal service
webhook integration
```

يمكن استخدام API keys، لكن key authentication لا تحل وحدها:

```text
who can access which tenant?
which endpoint?
what rate limit?
what scope?
```

يجب دمجها مع authorization policy.

---

# 84. API Security لا تساوي RBAC

الـOWASP API Top 10 الحالي يشمل مخاطر مثل:

```text
BOLA
Broken Authentication
Broken Object Property Level Authorization
Unrestricted Resource Consumption
Broken Function Level Authorization
Sensitive Business Flows
SSRF
Security Misconfiguration
Improper Inventory Management
Unsafe Consumption of APIs
```

إذن RBAC يغطي جزءًا مهمًا، لكنه ليس كامل API security. citeturn203318search2turn203318search7

---

# 85. Authorization Testing

لا تختبر فقط:

```text
admin can do X
```

اختبر matrix كاملة:

```text
viewer -> denied
editor -> allowed
manager -> allowed
admin -> allowed
anonymous -> denied
cross-tenant -> denied
wrong object owner -> denied
```

---

# 86. Object-Level Test Matrix

لكل endpoint يستخدم ID:

```text
Actor owns object
Actor same tenant
Actor different tenant
Actor no relation
Admin
Suspended user
Deleted user
```

ثم اختبر:

```text
GET
PATCH
DELETE
```

هذا يكتشف BOLA بشكل أفضل من الاختبارات السطحية.

---

# 87. Function-Level Test Matrix

مثلاً:

```http
GET /admin/users
```

اختبر:

```text
anonymous -> 401
viewer     -> 403
editor     -> 403
manager    -> maybe 403
admin      -> 200
```

لا تكتفِ باختبار admin.

---

# 88. Property-Level Test Matrix

في:

```http
PATCH /users/42
```

اختبر:

```json
{
  "name": "New Name"
}
```

ثم:

```json
{
  "role": "admin"
}
```

ثم:

```json
{
  "tenant_id": 999
}
```

يجب أن تكون حقول التصعيد مرفوضة للمستخدم العادي.

---

# 89. Permission Regression Tests

عند إضافة permission جديدة، يجب أن يكون هناك test يثبت:

```text
Who should have it?
Who should not?
```

لأن authorization bugs غالبًا تظهر من تغييرات صغيرة في policy.

---

# 90. Security Test as Code

مثال:

```python
async def test_viewer_cannot_delete_user(client, viewer_token):
    response = await client.delete(
        "/users/42",
        headers={
            "Authorization": f"Bearer {viewer_token}"
        },
    )

    assert response.status_code == 403
```

ثم:

```python
async def test_admin_can_delete_user(client, admin_token):
    response = await client.delete(
        "/users/42",
        headers={
            "Authorization": f"Bearer {admin_token}"
        },
    )

    assert response.status_code in {200, 204}
```

---

# 91. Negative Tests أهم من بعض Positive Tests

لماذا؟

لأن bug security غالبًا هو:

```text
User who should NOT access
successfully accesses
```

إذن اختبارات:

```text
DENY
```

مهمة جدًا.

---

# 92. Test BOLA

```python
async def test_user_cannot_read_other_users_order(
    client,
    user_a_token,
    order_owned_by_user_b,
):
    response = await client.get(
        f"/orders/{order_owned_by_user_b.id}",
        headers={
            "Authorization": f"Bearer {user_a_token}"
        },
    )

    assert response.status_code in {403, 404}
```

الاختيار بين 403 و404 يعتمد على سياسة إخفاء resource existence.

---

# 93. Test Cross-Tenant Access

```text
Tenant A user
       |
       +--> /projects/{tenant-B-project}
```

يجب أن يفشل حتى إذا كان لديه:

```text
projects:read
```

لأن permission لا تلغي tenant isolation.

---

# 94. Security Invariant

صمّم invariant واضحًا:

> **لا يوجد code path يستطيع إرجاع tenant-scoped object دون تمرير actor/tenant authorization.**

هذه أقوى من:

> "نحن نعتقد أن كل endpoint آمن."

---

# 95. Secure Repository Invariant

مثلًا:

```python
async def get_project_for_tenant(
    project_id: int,
    tenant_id: int,
):
    ...
```

واجعل:

```text
get_project(project_id)
```

غير متاح للـbusiness path إن كان يسمح بتجاوز tenant isolation.

---

# 96. Authorization Boundary

حدد boundary واضحًا:

```text
HTTP Request
   ↓
Authentication
   ↓
Authorization
   ↓
Use Case
   ↓
Repository
```

وللموارد الحساسة:

```text
Use Case
   ↓
Object Policy
   ↓
Repository scoped query
```

---

# 97. لا تضع Authorization في SQL فقط ولا في HTTP فقط

كل طبقة لها دور:

```text
HTTP layer
-> coarse endpoint permissions

Application layer
-> business authorization

Repository layer
-> tenant/object scoping

Database
-> constraints/defense where appropriate
```

هذا defense-in-depth.

---

# 98. Database Constraints

Authorization ليست كلها application logic.

قد تحتاج أيضًا إلى constraints مثل:

```text
FOREIGN KEY
UNIQUE
CHECK
NOT NULL
```

والـdatabase row-level security يمكن أن تكون مناسبة لبعض الأنظمة، لكن لا تفترض أن كل project يحتاج RLS.

---

# 99. Row-Level Security كطبقة إضافية

في PostgreSQL مثلًا يمكن أن تضيف سياسات row access.

الفكرة:

```text
Application says:
tenant_id = 7

Database policy says:
this role cannot see tenant 8 rows
```

هذا دفاع إضافي قوي لبعض multi-tenant systems.

لكن يزيد التعقيد التشغيلي.

---

# 100. RBAC لا يحل كل شيء

الـRBAC ممتاز عندما تكون السياسة:

```text
role -> permissions
```

لكن عندما تقول:

```text
A can edit B only if
same tenant
and B is not archived
and A is owner or manager
and business hours
```

أنت دخلت في policy/context territory.

لا تحاول إخفاء ذلك وراء `role == admin`.

---

# 101. Authorization DSL داخل المشروع

يمكن أن يكون لديك permission constants:

```python
class Permissions:
    USERS_READ = "users:read"
    USERS_CREATE = "users:create"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"

    ARTICLES_READ = "articles:read"
    ARTICLES_CREATE = "articles:create"
    ARTICLES_UPDATE = "articles:update"
    ARTICLES_PUBLISH = "articles:publish"
```

هذا يقلل typo مثل:

```text
users:reed
```

---

# 102. Enum للـActions

يمكن أيضًا:

```python
from enum import StrEnum


class Permission(StrEnum):
    USERS_READ = "users:read"
    USERS_DELETE = "users:delete"
    ARTICLES_PUBLISH = "articles:publish"
```

ثم:

```python
Permission.USERS_DELETE
```

---

# 103. Permission Naming Versioning

إذا تغير semantics، لا تغير قيمة قديمة بلا migration plan.

يمكن عند الحاجة استخدام:

```text
reports:export:v2
```

أو version policy في code/config.

لا تفعل ذلك إلا عند وجود سبب فعلي.

---

# 104. Role Management API

إذا كان لديك:

```http
POST /roles
POST /roles/{role}/permissions
POST /users/{id}/roles
```

هذه endpoints شديدة الحساسية.

يجب أن تخضع إلى:

```text
roles:manage
users:assign_role
```

وربما قواعد أعلى مثل:

```text
cannot assign permission higher than caller authority
```

---

# 105. Permission Escalation Rule

مثال:

```text
Manager has:
users:read
users:update
users:assign_role
```

لكن يجب ألا يستطيع إعطاء:

```text
system:admin
billing:refund
```

ما لم تكن policy تسمح بذلك.

إذن:

```text
Can assign role?
```

ليست permission ثنائية بسيطة دائمًا.

قد تحتاج:

```text
Can grant these permissions?
```

---

# 106. Hierarchical Permission Safety

إذا admin يستطيع كل شيء، فهذا واضح.

لكن في hierarchy المعقدة:

```text
super_admin
admin
manager
editor
```

حدد رسميًا:

```text
What does inheritance mean?
Can roles be combined?
Can lower role assign higher role?
Can role deny permission that parent grants?
```

لا تتركها للصدفة.

---

# 107. Deny Rules

بعض الأنظمة تحتاج explicit deny:

```text
Role A grants reports:read
Role B explicitly denies reports:read
```

هذا يزيد التعقيد.

لذلك استخدم deny rules فقط إذا domain يحتاجها، وإلا keep model simple:

```text
explicit grants
+ deny by default
```

---

# 108. Time-Based Authorization

مثال:

```text
billing:refund
```

مسموح فقط في:

```text
business hours
```

هذا ليس RBAC وحده.

يمكن أن يكون:

```text
role
+
permission
+
context.time
```

---

# 109. Location / Device Context

بعض الأنظمة شديدة الحساسية قد تضيف:

```text
device trust
IP/network
MFA state
risk score
```

إلى policy.

مثال:

```text
Allow refund if:
    user has billing:refund
    AND tenant matches
    AND MFA recently satisfied
```

هذا أقرب لـcontext-aware access control.

---

# 110. MFA للعمليات الحساسة

حتى لو المستخدم admin، بعض العمليات قد تتطلب إعادة تحقق أو MFA.

مثل:

```text
change billing bank account
rotate API keys
delete organization
refund large transaction
```

لا تجعل role alone هو كل security boundary.

---

# 111. Authorization + Rate Limits

Permission صحيحة لا تعني unlimited usage.

مثال:

```text
reports:export
```

قد يسمح للمستخدم بالتصدير، لكن:

```text
max 10 exports/hour
```

وهنا تجمع:

```text
authorization
+
resource limits
```

OWASP تضع Unrestricted Resource Consumption ضمن API Top 10، لأن صلاحية الوصول لا تعني أن الاستهلاك غير المحدود آمن. citeturn203318search2

---

# 112. Sensitive Business Flows

بعض الـflows حساسة حتى لو endpoint نفسه محمي.

مثال:

```text
POST /tickets/purchase
```

قد يسمح لمستخدم شرعي، لكن automation ضخمة يمكن أن تضر business.

لذلك تحتاج:

```text
authorization
+
rate limits
+
anti-automation controls
+
business rules
```

OWASP تصنف ذلك ضمن API6:2023 Sensitive Business Flows. citeturn203318search2

---

# 113. Authentication Security

Authorization قوية فوق Authentication ضعيفة لا تكفي.

يجب تأمين:

```text
password storage
login rate limit
token validation
refresh lifecycle
logout/revocation
MFA where appropriate
session management
```

FastAPI توضح في دليلها الحالي نمط OAuth2/JWT مع `pwdlib` وPyJWT كنقطة انطلاق لبناء Authentication، مع مرونة في اختيار model وقاعدة البيانات. citeturn467134search7

---

# 114. Login Brute Force

endpoint:

```http
POST /token
```

لا تتركه unlimited.

استخدم:

```text
rate limit
account protections
monitoring
backoff
MFA where required
```

---

# 115. Password Reset

Reset token يجب أن يكون:

```text
short-lived
single-use
unpredictable
bound to user/session context as appropriate
```

ولا تعتمد على:

```text
?user_id=42
```

كإثبات ملكية الحساب.

---

# 116. Access Token مقابل Refresh Token

من الأنماط الشائعة:

```text
Short-lived access token
+
Longer-lived refresh mechanism
```

لا تجعل access token طويل العمر أكثر من اللازم بلا سبب.

والـrefresh token يحتاج protection وrotation/revocation strategy حسب architecture.

---

# 117. JWT Storage في Browser

لا تتعامل مع:

```text
localStorage
```

كخيار آمن افتراضي لحفظ credentials.

OWASP تنبه إلى أن أي JavaScript يعمل في origin يستطيع الوصول إلى Web Storage، لذلك XSS قد يكشف tokens الموجودة هناك. في browser-centric systems يمكن أن تكون `HttpOnly; Secure; SameSite` cookies أو BFF pattern خيارات مناسبة حسب التصميم. citeturn467134search0

---

# 118. CORS ليس Authorization

CORS يقول للمتصفح:

> هل يسمح لهذا origin بقراءة response؟

لا يعني:

> هل هذا user يملك صلاحية access؟

حتى لو CORS مضبوط، attacker يستطيع استخدام curl أو server-side requests.

Authorization دائمًا server-side.

---

# 119. CSRF مقابل Bearer Headers

في cookie-based authentication، المتصفح قد يرسل credentials تلقائيًا، لذلك CSRF يصبح concern.

في cookie-less bearer model، التهديدات المختلفة مثل XSS/token theft تصبح مهمة.

لا تخلط threat models.

اختيار session/token transport يجب أن يكون جزءًا من security architecture.

---

# 120. Security Headers ليست RBAC

Headers مثل:

```text
CSP
HSTS
X-Content-Type-Options
```

مهمة، لكنها لا تقرر:

```text
هل المستخدم يحق له حذف order 42؟
```

هي طبقات دفاع مختلفة.

---

# 121. Defense in Depth

API security القوية ليست feature واحدة:

```text
TLS
+
Secure Authentication
+
Token Validation
+
RBAC
+
Object Authorization
+
Tenant Isolation
+
Input Validation
+
Rate Limiting
+
Logging
+
Monitoring
+
Database Constraints
```

لا توجد طبقة واحدة تكفي لكل شيء.

---

# 122. Security Invariants

أقوى طريقة لتصميم النظام هي صياغة invariants.

مثلاً:

> A user can never read data outside their tenant.

> A user can never assign permissions they don't have authority to grant.

> A request without valid authentication can never reach protected business logic.

> A user cannot modify security-sensitive fields through ordinary user update endpoints.

هذه الجمل تصبح أساس الاختبارات والتصميم.

---

# 123. Authorization Decision Logging

سجل:

```text
request_id
actor_id
action
resource_type
resource_id
allowed/denied
reason
tenant_id
```

لكن لا تسجل credentials أو secrets.

هذا يساعد في:

```text
incident response
security auditing
debugging
compliance
```

---

# 124. Do Not Leak Policy Internals

للمستخدم:

```text
403 Forbidden
```

قد يكون أفضل من:

```text
You failed because your role=editor and policy rule #14 requires manager in tenant 7.
```

الـinternal reason يجب أن يبقى في logs/telemetry عند الحاجة، لا في response الموجه للمهاجم.

---

# 125. Authorization Cache وRedis

يمكن أن نستخدم:

```text
authz:user:42
```

لتخزين:

```json
{
  "permissions": [
    "users:read",
    "articles:update"
  ]
}
```

لكن يجب أن نحدد:

```text
TTL

invalidation on role change

fallback if Redis unavailable
```

هذه نفس مشكلات caching التي تعلمناها، لكن الآن failure قد يصبح security issue بدل مجرد performance issue.

---

# 126. Security Cache Failure Policy

في cache عادي قد تقبل:

```text
Redis down
→ DB fallback
```

لكن في authorization cache:

```text
Redis down
```

لا يمكنك ببساطة افتراض:

```text
allow
```

هذا dangerous.

قد يكون القرار:

```text
fail closed
```

أي:

```text
No trustworthy authorization state
→ deny sensitive operation
```

أو تستخدم source of truth آخر.

هذه نقطة شديدة الأهمية.

---

# 127. Fail Open مقابل Fail Closed

في caching:

```text
Redis down -> maybe bypass cache
```

في authorization:

```text
cannot verify access
-> usually deny sensitive action
```

لذلك لا تستخدم نفس failure policy لكل dependency.

---

# 128. Authorization Service Interface

```python
from typing import Protocol


class AuthorizationService(Protocol):
    async def check(
        self,
        actor,
        action: str,
        resource=None,
        context=None,
    ) -> bool:
        ...
```

ثم implementation:

```python
class RBACAuthorizationService:
    async def check(
        self,
        actor,
        action,
        resource=None,
        context=None,
    ):
        if action not in actor.permissions:
            return False

        if resource is not None:
            if actor.tenant_id != resource.tenant_id:
                return False

        return True
```

---

# 129. لماذا Protocol؟

لأنك تستطيع إنشاء:

```text
RBACAuthorizationService
FakeAuthorizationService
TestAuthorizationService
PolicyEngineAdapter
```

والـbusiness layer لا تعتمد على implementation محددة.

هذا امتداد مباشر لمبادئ SOLID وDependency Inversion التي درسناها.

---

# 130. Policy Tests

اختبر policy نفسها بدون FastAPI:

```python
async def test_editor_can_update_article():
    actor = make_editor()
    article = make_article(tenant_id=actor.tenant_id)

    assert await policy.can_update(
        actor,
        article,
    )
```

واختبر:

```python
async def test_editor_cannot_update_other_tenant_article():
    actor = make_editor(tenant_id=1)
    article = make_article(tenant_id=2)

    assert not await policy.can_update(
        actor,
        article,
    )
```

---

# 131. Route Tests

ثم اختبر integration:

```text
HTTP
 ↓
Authentication
 ↓
Authorization
 ↓
Service
```

لكن لا تجعل كل policy test يحتاج HTTP.

افصل:

```text
unit policy tests
integration API tests
end-to-end tests
```

---

# 132. Authorization Matrix as Test Data

يمكن تمثيل matrix:

```python
cases = [
    ("viewer", "articles:read", True),
    ("viewer", "articles:update", False),
    ("editor", "articles:update", True),
    ("editor", "articles:delete", False),
    ("admin", "articles:delete", True),
]
```

ثم parameterized tests.

هذا يجعل regressions واضحة جدًا.

---

# 133. Fuzzing Authorization IDs

لو endpoint:

```http
GET /documents/{id}
```

اختبر عدة IDs:

```text
own
other user
other tenant
random UUID
nonexistent
deleted
archived
```

الهدف هو اكتشاف BOLA وedge cases.

---

# 134. Security Review Checklist للـAPI

لكل endpoint اسأل:

```text
Who is the actor?
How is identity established?
What action is requested?
What permission is required?
What object is involved?
Who owns the object?
What tenant does it belong to?
Can the actor modify security-sensitive properties?
What happens if the object does not exist?
What happens if policy cannot be evaluated?
```

---

# 135. API Inventory

وجود Authorization policy لا يفيد إذا نسيت endpoint جديد.

احتفظ بقائمة:

```text
GET /users/me
GET /users/{id}
PATCH /users/{id}
DELETE /users/{id}
GET /admin/users
POST /roles
POST /reports/export
```

ثم اربط لكل endpoint:

```text
Authentication
Required permission
Object policy
Rate limit
Sensitive data class
```

OWASP تضع Improper Inventory Management ضمن API Security Top 10 لأن endpoints والنسخ القديمة غير المعروفة قد تكون سطح هجوم. citeturn203318search2

---

# 136. Versioned APIs

لو لديك:

```text
/api/v1/users
/api/v2/users
```

لا تفترض أن authorization في v1 تنتقل تلقائيًا إلى v2.

اختبر كل version.

كذلك لا تترك:

```text
/admin-old
/debug
/internal-test
```

مكشوفة في production.

---

# 137. Security Misconfiguration

أمثلة:

```text
DEBUG=true

Swagger مفتوح للكل بدون سياسة واضحة

CORS واسع جدًا

Default credentials

Weak secret keys

Unused admin endpoints
```

RBAC لا ينقذك من misconfiguration.

---

# 138. Secrets

لا تضع:

```text
JWT_SECRET
DB_PASSWORD
API_KEY
```

في Git.

استخدم environment/secrets manager.

ولو تسرب secret:

```text
rotate
revoke
invalidate
investigate
```

---

# 139. JWT Secret Rotation

في systems طويلة العمر، فكر في key rotation.

مثل:

```text
kid = key-2026-01
```

ثم verifier يعرف active + previous keys أثناء migration.

لا تغير key دون plan إذا كان لديك tokens صالحة كثيرة.

---

# 140. Asymmetric Signing في الأنظمة الموزعة

في بعض architectures:

```text
Auth Server
  signs with private key

APIs
  verify with public key
```

هذا يجعل خدمات التحقق لا تحتاج secret signing key نفسه.

يمكن استخدام RS256/ES256 أو غيرها حسب design وlibraries، لكن اختيار algorithm يحتاج threat model وkey management؛ لا تختار algorithm لمجرد أن الاسم شائع.

---

# 141. JWKS / Key Discovery

في architectures التي تستخدم Authorization Server مركزي، يمكن للخدمات جلب public keys من JWKS endpoint، مع caching وrotation.

لكن لا تفتح fetch على كل request.

يجب أن يكون هناك:

```text
key cache
rotation strategy
issuer validation
audience validation
```

---

# 142. JWT Algorithm Confusion

لا تقبل algorithm من token كأنه policy.

الـserver يجب أن يعرف algorithms المسموح بها مسبقًا.

أي:

```python
jwt.decode(
    token,
    key,
    algorithms=["RS256"],
    audience="api.example.com",
    issuer="https://auth.example.com",
)
```

وليس:

```python
algorithm = token_header["alg"]
# trust blindly
```

---

# 143. Authorization Context

قد تحتاج إلى context object:

```python
@dataclass(frozen=True)
class AuthorizationContext:
    ip: str | None
    tenant_id: int
    device_id: str | None
    mfa_recent: bool
    request_id: str
```

ثم policy:

```python
policy.check(
    actor,
    action,
    resource,
    context,
)
```

هذا يفتح الباب لأنظمة أكثر تقدمًا دون تحويل كل route إلى `if` statements.

---

# 144. Policy Composition

بدل policy ضخمة:

```text
can_update_article
```

يمكن تركيب:

```text
HasPermission
AND
SameTenant
AND
ResourceStateAllowed
AND
OwnerOrManager
```

مفهوميًا:

```text
Allow =
    permission
    AND tenant_match
    AND state_rule
    AND relationship_rule
```

وهذا يجعل policy قابلة للفهم والاختبار.

---

# 145. Relationship-Based Authorization

أحيانًا السؤال ليس role فقط.

بل:

```text
Can user A access resource B?
```

حسب relation:

```text
owner
member
manager
reviewer
parent
```

مثال:

```text
Document 100
  owner = User 42
  reviewers = {7, 9}
```

User 7 قد يقرأ ويعلق، لكن لا يستطيع حذفه.

هذه relationship-based policy تتجاوز RBAC البسيط.

---

# 146. RBAC + ReBAC

في الأنظمة المعقدة قد تجمع:

```text
Role
+
Permission
+
Relationship
+
Tenant
```

مثل:

```text
editor
AND
member_of_project
AND
same_tenant
```

وهذا أكثر تعبيرًا من Role وحدها.

---

# 147. عندما يصبح النظام كبيرًا جدًا

يمكن أن تنتقل من:

```text
custom authorization service
```

إلى policy engine مثل:

```text
OPA / Rego
Cedar
OpenFGA
Keycloak authorization features
```

لكن لا تبدأ بها إلا عندما يكون التعقيد يبررها.

المبدأ الذي يجب تعلمه أولًا:

```text
Policy
Decision
Enforcement
Context
```

---

# 148. Policy Decision Point وPEP

مصطلحان مهمان:

## PDP — Policy Decision Point

من يقرر:

```text
allow / deny
```

## PEP — Policy Enforcement Point

من ينفذ القرار:

```text
if deny -> stop
if allow -> continue
```

مثال:

```text
FastAPI route/use-case
      |
      v
AuthorizationService (PDP)
      |
      v
allow/deny
      |
      v
Service/Repository (PEP enforcement)
```

قد تكون نفس الطبقة في implementation صغيرة، لكن الفصل الذهني مفيد جدًا.

---

# 149. Audit Trail

للعمليات الحساسة:

```text
who
what
when
which object
old state
new state
request_id
```

مثال:

```text
ADMIN_ROLE_ASSIGNED
actor=7
target=42
old_role=editor
new_role=admin
time=...
request_id=req_123
```

هذا مهم للأمن والتحقيقات وليس فقط debugging.

---

# 150. لا تجعل Audit Log قابلًا للتعديل من المستخدم

يجب أن يكون:

```text
append-only as much as practical
restricted
monitored
```

ولا تمنح `logs:delete` لأي role عادي.

---

# 151. Security Event Taxonomy

يمكنك تعريف events:

```text
AUTH_LOGIN_SUCCESS
AUTH_LOGIN_FAILURE
AUTH_TOKEN_REJECTED
AUTHZ_DENIED
ROLE_ASSIGNED
ROLE_REVOKED
PERMISSION_CHANGED
TENANT_ACCESS_DENIED
SENSITIVE_ACTION_EXECUTED
```

هذه تساعد في detection وincident response.

---

# 152. Rate Limiting Authorization Abuse

لو attacker يحاول:

```text
100000 object IDs
```

مهم أن تراقب:

```text
403 rate
404 rate
object-id enumeration patterns
```

لأن authorization failures المتكررة قد تشير لمحاولة enumeration أو probing.

---

# 153. Resource Enumeration

حتى لو endpoint يعيد 404، قد يستطيع attacker معرفة IDs متاحة عبر:

```text
timing
error patterns
list endpoints
search endpoints
```

لذلك security لا تقتصر على status code وحده.

---

# 154. Search Endpoint Authorization

سيئ:

```http
GET /users?search=...
```

ويعيد كل users مع internal fields.

الأفضل:

```text
scope search results by tenant
filter fields
apply role policy
paginate
rate limit
```

---

# 155. Bulk Endpoints

Endpoint مثل:

```http
POST /users/bulk-delete
```

أكثر خطورة من single delete.

لا يكفي فحص permission مرة واحدة فقط.

يجب أن يكون واضحًا أن actor يستطيع حذف **كل target objects الموجودة في الطلب**.

يمكن أن يكون policy:

```text
all objects must be authorized
```

أو:

```text
reject entire batch if any unauthorized
```

أو سياسة أخرى مقصودة.

---

# 156. Pagination Authorization

لا تفترض أن أول صفحة آمنة تعني كل الصفحات آمنة.

كل query يجب أن تحمل tenant/object filters نفسها.

مثال:

```sql
SELECT *
FROM documents
WHERE tenant_id = :tenant_id
ORDER BY id
LIMIT :limit
OFFSET :offset
```

---

# 157. Sorting/Filtering Security

حتى fields المستخدمة في filters قد تكشف data.

لا تسمح arbitrary SQL/order field injection.

استخدم allowlist:

```python
ALLOWED_SORT_FIELDS = {
    "created_at",
    "name",
}
```

وهذا يجمع authorization مع input validation.

---

# 158. Authorization في Async Jobs

تذكر درس Celery.

إذا HTTP request authorized user ثم enqueue task:

```text
POST /reports
    ↓
authorized
    ↓
Celery task
```

لا تفترض أن task دائمًا ينفذ في نفس security context.

مرر identifiers بوضوح، ثم تحقق من domain ownership عند الحاجة.

---

# 159. Do Not Blindly Trust Task Arguments

إذا task:

```python
send_report.delay(
    user_id=42,
    report_id=123,
)
```

فلا يعني أن أي actor استطاع enqueue يستطيع فعل أي شيء بهذين IDs.

الـworker يجب أن يطبق business invariants عند الحدود المناسبة.

---

# 160. Authorization في WebSockets

الـconnection authenticated مرة، لكن هذا لا يعني أن كل event مسموح.

يجب أن تكون:

```text
Connection authentication
+
Per-command authorization
+
Per-room authorization
```

مثال:

```text
User authenticated
        |
        v
chat.send room=42
        |
        v
Can user send in room 42?
```

هذا يربط مباشرةً درس RBAC مع درس WebSockets.

---

# 161. Authorization في GraphQL

نفس المبدأ:

```text
endpoint access
```

لا يكفي.

GraphQL قد يسمح للمستخدم بطلب object/property داخلي دون proper field/object authorization.

لذلك policy يجب أن تكون على level مناسب من resolver/use-case/object.

---

# 162. Authorization في Internal APIs

لا تقل:

> "ده internal، إذن آمن."

Internal services قد تتعرض compromise أو misconfiguration.

استخدم:

```text
service identity
mTLS/OAuth2
scopes
network policy
least privilege
```

حسب architecture.

---

# 163. Service-to-Service Authorization

مثال:

```text
Billing Service
```

يحتاج:

```text
invoices:read
invoices:write
```

ولا يحتاج:

```text
users:delete
```

استخدم machine identities وscopes مخصصة بدل user roles البشرية حيث يكون ذلك مناسبًا.

---

# 164. Token Audience في Microservices

لو token مخصص لـ:

```text
billing-api
```

يجب ألا تقبله:

```text
admin-api
```

لمجرد أن نفس issuer وقّعه.

تحقق من `aud` وفق trust model. citeturn467134search8

---

# 165. Authorization Cache في Microservices

لو صلاحيات user موزعة:

```text
Auth Service
```

وعدة APIs تحتاجها، قد تستخدم:

```text
JWT scopes
central introspection
permissions cache
policy service
```

وكل اختيار له trade-offs في:

```text
latency
freshness
availability
complexity
```

---

# 166. Authorization Availability

قرار مهم:

> ماذا يحدث إذا Authorization Service غير متاح؟

للعمليات الحساسة:

```text
fail closed
```

غالبًا أكثر أمانًا.

لكن لبعض الأنظمة يمكن أن تكون هناك cached decision strategy مع حدود زمنية.

القرار يجب أن يكون مبنيًا على threat model.

---

# 167. Cache Positive Decisions فقط؟

حتى هذا ليس قاعدة.

قد تحتاج caching لـ:

```text
allow
```

لكن deny أيضًا قد يُخزن لتقليل probing أو load.

المهم:

```text
TTL
invalidation
security semantics
```

---

# 168. Security Boundary Checklist

عند كل boundary اسأل:

```text
HTTP -> Service
Service -> Repository
API -> Internal API
User -> WebSocket
Service -> Service
Worker -> Database
Admin UI -> Admin API
```

أين يتم:

```text
authentication?
authorization?
identity propagation?
tenant propagation?
auditing?
```

---

# 169. Identity Propagation

في distributed request:

```text
Client
  ↓
API Gateway
  ↓
Orders Service
  ↓
Billing Service
```

يجب أن يعرف downstream:

```text
who is actor?
which tenant?
which scopes?
which request_id?
```

لكن لا تمرر identity بطريقة يمكن لأي خدمة تزويرها دون trust boundary واضح.

---

# 170. Trusted Headers مشكلة

خطأ:

```http
X-User-Id: 42
X-Role: admin
```

ثم الخدمة تثق بها من الإنترنت مباشرة.

لو لم تكن هناك trusted proxy/service boundary قوية، يمكن للعميل تزويرها.

الـidentity يجب أن تكون من authenticated token أو trusted identity propagation mechanism.

---

# 171. API Gateway وAuthorization

Gateway يمكن أن يقوم بـ:

```text
authentication
coarse scopes
rate limiting
routing
```

لكن لا تجعل gateway هو المكان الوحيد للـobject/business authorization.

الـdownstream service يجب أن يحمي business invariants نفسها.

---

# 172. Security Gateway Pattern

```text
Internet
  |
  v
API Gateway
  |
  +--> Authentication
  +--> coarse authorization
  +--> rate limit
  |
  v
Service
  |
  +--> object authorization
  +--> business policy
  +--> tenant isolation
```

هذه defense-in-depth جيدة.

---

# 173. Permission Discovery

يمكنك توفير endpoint مثل:

```http
GET /me/permissions
```

لـfrontend حتى يعرف الـUI ماذا يعرض.

لكن يجب ألا تستخدم endpoint هذا كبديل للـserver-side enforcement.

هو UX aid.

---

# 174. Role Names في Frontend

يمكن أن يعرض frontend:

```text
role = editor
```

لكن لا تبنِ security decision في browser اعتمادًا على:

```javascript
if (role === "admin") showDeleteButton()
```

هذا presentation logic فقط.

---

# 175. API Documentation

وثّق لكل endpoint:

```text
Authentication required
Required scopes/permissions
Resource policy
Tenant scope
Possible 401/403
```

FastAPI يمكن أن تعرض OAuth2 scopes في OpenAPI عندما تستخدم `Security` مع scopes. citeturn467134search1

---

# 176. مثال Endpoint Contract

```text
DELETE /users/{user_id}

Auth: Bearer token
Permission: users:delete
Object rule:
  - same tenant
  - target != actor
  - actor can manage target

Possible responses:
  401 invalid/missing authentication
  403 permission/object policy denied
  404 target not found / hidden by policy
```

هذا documentation مفيد جدًا للفريق.

---

# 177. Secure Coding Rule

أي function تستقبل identifier من client وتصل إلى resource يجب أن تسأل:

```text
Where is object authorization?
```

هذه من أهم العادات التي يجب أن تصبح automatic في ذهنك. citeturn203318search4

---

# 178. Authorization Review Rule

أي endpoint إداري يجب أن يسأل:

```text
Where is function-level authorization?
```

لأن admin endpoints هدف واضح لـBroken Function Level Authorization. citeturn203318search5

---

# 179. Sensitive Property Review Rule

أي update endpoint يجب أن يسأل:

```text
Which fields can this actor modify?
```

لا تسأل فقط:

```text
Can this actor access the endpoint?
```

هذه هي property-level authorization. citeturn203318search8

---

# 180. مشروع المرحلة — Advanced RBAC API

سنحوّل مشروع FastAPI السابق إلى API آمنة تحتوي على:

```text
Authentication
RBAC
Permissions
Object Authorization
Tenant Isolation
JWT/OAuth2 Scopes
Audit Logging
Rate Limits
Authorization Tests
```

---

# 181. بنية المشروع

```text
backend-mastery/
├── app/
│   ├── main.py
│   ├── config.py
│   │
│   ├── auth/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── password.py
│   │   ├── jwt.py
│   │   ├── dependencies.py
│   │   └── service.py
│   │
│   ├── authorization/
│   │   ├── permissions.py
│   │   ├── policies.py
│   │   ├── service.py
│   │   └── context.py
│   │
│   ├── users/
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   └── schemas.py
│   │
│   ├── articles/
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   └── policies.py
│   │
│   ├── tenants/
│   │   └── service.py
│   │
│   └── audit/
│       └── service.py
│
├── tests/
│   ├── auth/
│   ├── authorization/
│   ├── users/
│   └── articles/
│
├── .env.example
├── requirements.txt
└── README.md
```

---

# 182. Database Schema

ابدأ بـ:

```text
users
roles
permissions
user_roles
role_permissions
```

ثم أضف domain:

```text
tenants
articles
article_members / ownership relation
```

وأضف:

```text
audit_logs
```

للعمليات الحساسة.

---

# 183. User Model

```python
class User:
    id: int
    tenant_id: int
    email: str
    password_hash: str
    is_active: bool
```

لا تجعل `role` هو الحقل الوحيد إذا كان النظام يحتاج multiple roles.

---

# 184. Role Model

```python
class Role:
    id: int
    name: str
```

أمثلة:

```text
viewer
editor
manager
admin
```

---

# 185. Permission Model

```python
class Permission:
    id: int
    name: str
```

أمثلة:

```text
users:read
users:update
users:delete
articles:read
articles:update
articles:publish
reports:export
```

---

# 186. JWT Model

إنشئ claims مثل:

```json
{
  "sub": "42",
  "iss": "auth.example.com",
  "aud": "api.example.com",
  "exp": 1790937600,
  "jti": "...",
  "scope": "users:read articles:read"
}
```

لكن احرص أن تكون القيم generated server-side ومتحققًا منها عند كل request.

---

# 187. Password Service

باستخدام `pwdlib` أو مكتبة hashing موثوقة:

```python
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

hashed = password_hash.hash(password)
valid = password_hash.verify(password, hashed)
```

لا تكتب password hashing يدويًا.

والإعدادات يجب أن تتبع توجيهات الخوارزمية والمكتبة المستخدمة؛ OWASP الحالية تفضل Argon2id عندما يكون متاحًا. citeturn467134search2

---

# 188. JWT Verification Service

```python
async def verify_access_token(token: str):
    payload = jwt.decode(
        token,
        public_or_secret_key,
        algorithms=["..."],
        audience="api.example.com",
        issuer="auth.example.com",
    )

    return payload
```

لا تعتمد على signature فقط؛ تحقق من claims المطلوبة مثل `exp`, `iss`, `aud` حسب تصميم الثقة. citeturn467134search5turn467134search8

---

# 189. `get_current_user`

```python
async def get_current_user(...):
    payload = verify_access_token(token)

    user_id = parse_subject(payload)
    user = await user_repository.get_by_id(user_id)

    if not user or not user.is_active:
        raise invalid_credentials()

    return user
```

لاحظ أن identity تأتي من verified token.

---

# 190. Permission Loading

يمكن:

```python
permissions = await permission_repository.for_user(
    user_id=current_user.id,
)
```

أو:

```text
JWT scopes
```

أو hybrid.

الاختيار يعتمد على freshness وlatency وcomplexity.

---

# 191. Authorization Context

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthorizationContext:
    request_id: str
    tenant_id: int
    ip: str | None = None
    mfa_recent: bool = False
```

ثم:

```python
await authorization.check(
    actor=current_user,
    action="articles:update",
    resource=article,
    context=context,
)
```

---

# 192. Policy Example

```python
class ArticlePolicy:
    def can_update(self, actor, article) -> bool:
        if "articles:update" not in actor.permissions:
            return False

        if actor.tenant_id != article.tenant_id:
            return False

        if article.status == "archived":
            return False

        if article.owner_id == actor.id:
            return True

        return "articles:manage_any" in actor.permissions
```

---

# 193. FastAPI Route

```python
@app.patch("/articles/{article_id}")
async def update_article(
    article_id: int,
    payload: ArticleUpdate,
    current_user = Depends(get_current_user),
):
    article = await article_service.get_accessible_article(
        actor=current_user,
        article_id=article_id,
    )

    await authorization.require(
        actor=current_user,
        action="articles:update",
        resource=article,
    )

    return await article_service.update(
        article,
        payload,
    )
```

---

# 194. الأفضل: Scoped Repository

```python
article = await article_repository.get_for_actor(
    article_id=article_id,
    actor=current_user,
)
```

ثم policy:

```text
permission + state + relation
```

بحيث لا تستطيع route عن طريق الخطأ الوصول إلى object خارج tenant.

---

# 195. Admin Endpoint

```python
@app.get("/admin/users")
async def list_users(
    current_user = Depends(
        require_permission("users:read:admin")
    ),
):
    ...
```

لكن permission يجب أن تكون explicit.

لا تعتمد على obscurity مثل:

```text
/admin-secret
```

---

# 196. Role Assignment Endpoint

```http
POST /users/42/roles
```

الـpolicy يجب أن تتحقق من:

```text
actor has users:assign_role
actor and target are in same tenant
role exists
actor is allowed to grant this role
```

---

# 197. Audit Role Assignment

بعد النجاح:

```text
ROLE_ASSIGNED
actor=7
target=42
role=editor
request_id=...
```

ويجب أن يكون audit event مرتبطًا بالعملية.

---

# 198. Test: Viewer

```text
viewer
```

يستطيع:

```text
articles:read
```

ولا يستطيع:

```text
articles:update
articles:publish
```

---

# 199. Test: Editor

```text
editor
```

يستطيع:

```text
articles:read
articles:update
```

وقد يستطيع:

```text
articles:publish
```

حسب سياسة المشروع.

ولا يستطيع:

```text
users:delete
billing:refund
```

---

# 200. Test: Admin

```text
admin
```

يجب أن يمتلك permissions المحددة في matrix، وليس "كل شيء" ضمنيًا دون توثيق.

---

# 201. Test: BOLA

User A:

```text
tenant=1
```

Article:

```text
tenant=2
```

المطلوب:

```text
403 or 404
```

ولا يجب أن تعود البيانات.

---

# 202. Test: Property Escalation

User عادي يرسل:

```json
{
  "role": "admin",
  "tenant_id": 999,
  "is_active": true
}
```

المطلوب:

```text
role ignored/rejected
tenant_id ignored/rejected
is_active restricted
```

حسب endpoint contract.

---

# 203. Test: Cross-Tenant Role Assignment

User admin في Tenant A يحاول منح role لمستخدم في Tenant B.

المطلوب:

```text
DENY
```

حتى لو لديه `users:assign_role` في tenantه.

---

# 204. Test: Revoked Role

الخطوات:

```text
User -> admin
Issue token
Downgrade user -> viewer
Call sensitive endpoint with old token
```

حدد policy:

```text
short-lived token
or
fresh role check
or
revocation/session version
```

ثم اكتب test يثبت behavior المقصود.

---

# 205. Test: JWT Audience

أنشئ token صالحًا لخدمة أخرى:

```text
aud = other-api
```

وحاول استخدامه مع API الحالية.

المطلوب:

```text
DENY
```

إذا كان design يستخدم audience restriction.

---

# 206. Test: Expired Token

```text
exp < now
```

المطلوب:

```text
401
```

---

# 207. Test: Missing Scope

Token:

```text
scope = articles:read
```

Endpoint يحتاج:

```text
articles:update
```

المطلوب:

```text
403
```

FastAPI scopes تدعم هذا النوع من fine-grained authorization عبر `Security` و`SecurityScopes`. citeturn467134search1

---

# 208. Test: Inactive User

User لديه token صالح، لكن:

```text
is_active = false
```

حدد policy الخاصة بك، وغالبًا العمليات المحمية يجب رفضها.

لا تعتمد على token وحده إذا كانت حالة user الحالية مهمة للأمان.

---

# 209. Test: Missing Authorization

```http
GET /admin/users
```

بدون credentials.

المطلوب:

```text
401
```

---

# 210. Test: Wrong Role but Valid Identity

```text
viewer -> /admin/users
```

المطلوب:

```text
403
```

---

# 211. Test: Security-Sensitive Update

جرّب:

```json
{
  "password_hash": "..."
}
```

من endpoint user update العادي.

المطلوب أن يكون field غير مسموح به.

---

# 212. Test: Bulk Delete

User يملك permission حذف user واحد فقط.

حاول:

```http
POST /users/bulk-delete
```

يجب أن يكون لهذا endpoint policy واضحة، ولا تفترض أنه يرث تلقائيًا صلاحية single delete.

---

# 213. Test: Search

User من tenant A يحاول search عن:

```text
email of tenant B
```

المطلوب أن تكون النتائج tenant-scoped.

---

# 214. Authorization Test Coverage

لا تقل:

```text
"عندي tests"
```

افحص coverage على:

```text
positive paths
negative paths
cross-tenant
object ownership
role changes
scope changes
expired tokens
invalid tokens
sensitive properties
admin paths
bulk operations
```

---

# 215. Security Review Checklist

لكل endpoint:

```text
[ ] Authentication required?
[ ] Token verified correctly?
[ ] Issuer checked if applicable?
[ ] Audience checked if applicable?
[ ] Expiration checked?
[ ] Scope/permission checked?
[ ] Object authorization checked?
[ ] Tenant scoped?
[ ] Sensitive fields protected?
[ ] Rate limited?
[ ] Audit event needed?
[ ] Error response avoids leakage?
```

---

# 216. أخطاء شائعة جدًا

## الخطأ 1

```python
if current_user.role == "admin":
    allow_everything()
```

## الخطأ 2

```python
project = repo.get(project_id)
return project
```

بدون object/tenant authorization.

## الخطأ 3

```python
user.__dict__.update(payload)
```

## الخطأ 4

```python
if role_from_client == "admin":
    ...
```

## الخطأ 5

```python
JWT signature valid -> accept everything
```

بدون `aud/iss/exp` حسب policy.

## الخطأ 6

```text
CORS = authorization
```

## الخطأ 7

```text
Frontend hides button = security
```

## الخطأ 8

```text
UUID = authorization
```

## الخطأ 9

```text
RBAC alone solves multi-tenancy
```

## الخطأ 10

```text
Authorization cache failure -> allow
```

---

# 217. مشروع المرحلة النهائي

# Secure Multi-Tenant RBAC API

المطلوب:

```text
Authentication
        ↓
JWT/OAuth2
        ↓
Roles
        ↓
Permissions
        ↓
Object Policies
        ↓
Tenant Isolation
        ↓
Audit Logs
        ↓
Tests
```

---

# 218. Roles

```text
viewer
editor
manager
admin
```

---

# 219. Permissions

```text
users:read
users:update
users:delete
users:assign_role

articles:read
articles:create
articles:update
articles:publish
articles:delete

reports:read
reports:export

billing:read
billing:refund
```

---

# 220. Business Policies

## Viewer

```text
read articles
```

## Editor

```text
read
create
update
```

## Manager

```text
editor permissions
+
users:update
```

## Admin

```text
explicit admin permissions
```

لا تستخدم implicit "all" إلا إذا كان ذلك جزءًا واضحًا من policy.

---

# 221. Tenant Rules

كل resource لديه:

```text
tenant_id
```

وأي actor عادي لا يمكنه الوصول إلى resource خارج tenantه.

---

# 222. User Management API

```http
GET    /users/me
GET    /users/{id}
PATCH  /users/{id}
DELETE /users/{id}
POST   /users/{id}/roles
```

كل endpoint له authorization policy منفصلة.

---

# 223. Article API

```http
GET    /articles/{id}
POST   /articles
PATCH  /articles/{id}
POST   /articles/{id}/publish
DELETE /articles/{id}
```

---

# 224. Admin API

```http
GET /admin/users
GET /admin/audit-logs
POST /admin/roles
```

كلها protected صراحة.

---

# 225. Authentication API

```http
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
```

حدد lifecycle الخاص بالtokens/session.

---

# 226. `/auth/logout`

إذا كنت تستخدم stateless short-lived access tokens فقط، logout قد يكون local client action مع refresh token/session revocation strategy.

إذا تحتاج invalidation فورية، استخدم session/token revocation mechanism مثل session versioning أو `jti` denylist حسب التصميم. OWASP تناقش denylisting JWT عند الحاجة لإنهاء token قبل expiration. citeturn467134search5

---

# 227. Audit API

لا تجعل المستخدم العادي يقرأ:

```http
GET /admin/audit-logs
```

إلا بصلاحية واضحة مثل:

```text
audit:read
```

---

# 228. Required Audit Events

```text
LOGIN_SUCCESS
LOGIN_FAILURE
LOGOUT
AUTHZ_DENIED
ROLE_ASSIGNED
ROLE_REVOKED
PERMISSION_CHANGED
SENSITIVE_ACTION_EXECUTED
```

---

# 229. المشروع يجب أن يثبت هذه الحالات

```text
[ ] User login works
[ ] Invalid token denied
[ ] Expired token denied
[ ] Scope denied correctly
[ ] Viewer cannot admin
[ ] Editor cannot delete users
[ ] User cannot access other tenant
[ ] User cannot change own role
[ ] User cannot change tenant_id
[ ] Admin can perform allowed operations
[ ] Object-level checks exist
[ ] Sensitive fields protected
[ ] Audit logs generated
[ ] Authorization failures tested
```

---

# 230. Advanced Challenge — Role Assignment

صمم policy:

```text
A user may assign a role only if:

1. actor has users:assign_role
2. target belongs to same tenant
3. target role exists
4. actor is allowed to grant that role
5. action is audited
```

ثم نفذها في Policy class.

---

# 231. Advanced Challenge — Protected Admin

لنفترض:

```text
super_admin
```

لا يمكن لأي actor عادي:

```text
remove super_admin
modify super_admin role
change super_admin tenant
```

حتى لو كان لديه `users:update`.

هذا مثال على business-level authorization فوق RBAC.

---

# 232. Advanced Challenge — Temporary Permission

قد تحتاج:

```text
User 42
has reports:export
for 24 hours
```

التصميم قد يحتوي:

```text
user_permission_grants
permission
starts_at
expires_at
```

والpolicy:

```text
now between starts_at and expires_at
```

هذه بداية Time-Bounded Authorization.

---

# 233. Advanced Challenge — Break-Glass Access

في بعض الأنظمة الحساسة قد يوجد emergency access:

```text
break_glass
```

لكن يجب أن يكون:

```text
rare
explicit
audited
time-limited
highly monitored
```

هذا ليس role عاديًا.

---

# 234. Advanced Challenge — Relationship Policy

User يستطيع تعديل article إذا:

```text
has articles:update
AND
same tenant
AND
(
  owner
  OR
  manager
)
```

اكتب policy unit tests لكل branch من هذا المنطق.

---

# 235. Advanced Challenge — Service-to-Service

أنشئ service account لـ:

```text
report-worker
```

مسموح له:

```text
reports:read
reports:write
```

وليس:

```text
users:delete
billing:refund
```

اختبر أن token موجه لـbilling API لا يعمل مع admin API إذا كانت audience مختلفة.

---

# 236. Advanced Challenge — Authorization Cache

أضف Redis cache:

```text
authz:user:{id}
```

واختبر:

```text
role added
role removed
permission changed
cache invalidated
```

الهدف أن تتعلم أن cache security requires invalidation discipline.

---

# 237. Advanced Challenge — Fail Closed

تعمد إيقاف Redis authorization cache.

إذا لم تستطع الحصول على authorization state الموثوق في عملية حساسة:

```text
DENY
```

ولا:

```text
ALLOW
```

ثم وثّق لماذا.

---

# 238. Interview — Authentication

أجب بدون الرجوع للكتاب:

1. الفرق بين Authentication وAuthorization؟
2. ما الفرق بين 401 و403؟
3. لماذا JWT signature وحدها ليست كافية؟
4. ما أهمية `iss` و`aud` و`exp`؟
5. ما هي مشكلة JWT revocation؟
6. متى تستخدم short-lived access token؟
7. ما سبب خطر localStorage في browser-based token storage؟
8. ما وظيفة `jti`؟

---

# 239. Interview — RBAC

1. ما هو Role؟
2. ما هو Permission؟
3. لماذا permission أهم من role في enforcement؟
4. ما هو least privilege؟
5. لماذا deny-by-default؟
6. هل UUID يمنع BOLA؟
7. ما الفرق بين function-level وobject-level authorization؟
8. ما هو property-level authorization؟

---

# 240. Interview — Multi-Tenancy

1. كيف تمنع cross-tenant data access؟
2. لماذا `get(id)` وحده خطر؟
3. كيف تجعل repository tenant-aware؟
4. هل role admin في tenant A يجب أن يصل إلى tenant B؟
5. كيف تختبر tenant isolation؟

---

# 241. Interview — Architecture

1. أين تضع coarse authorization؟
2. أين تضع object-level authorization؟
3. هل يمكن أن تعتمد على frontend؟
4. متى تستخدم OAuth2 scopes؟
5. متى تحتاج policy engine؟
6. ما الفرق بين PDP وPEP؟
7. كيف تربط authorization بـaudit logs؟
8. كيف تتعامل مع authorization cache failure؟

---

# 242. سيناريو مقابلة Senior

لديك:

```text
User A
role = editor
tenant = 1
```

ويرسل:

```http
PATCH /articles/900
```

المقال:

```text
article_id = 900
tenant = 2
owner = User B
status = draft
```

User A يملك:

```text
articles:update
```

هل تسمح؟

الإجابة ليست مجرد:

```text
YES because permission exists
```

بل:

```text
NO
```

لأن:

```text
permission exists
BUT
resource belongs to another tenant
```

وهذا هو التفكير في object-level authorization.

---

# 243. سيناريو أصعب

User يملك:

```text
articles:publish
```

لكن المقال:

```text
status = archived
```

هل تسمح؟

القرار:

```text
depends on domain policy
```

وهذا يثبت أن:

```text
Permission != complete policy
```

---

# 244. سيناريو أصعب جدًا

User لديه:

```text
users:assign_role
```

ويحاول منح مستخدم آخر:

```text
super_admin
```

هل يسمح؟

ليس بالضرورة.

يجب فحص:

```text
Can actor grant this specific role?
```

وهذا هو privilege escalation defense.

---

# 245. Authorization Threat Model

قبل الإنتاج حدد:

```text
Assets
    ↓
Users
    ↓
Tenants
    ↓
Documents
    ↓
Billing
    ↓
Admin functions
```

ثم:

```text
Who can attack?
What can they control?
What can leak?
What can be modified?
What must be immutable?
```

بعدها صمّم policies.

---

# 246. Security Invariants للمشروع

ضع هذه في `SECURITY_INVARIANTS.md`:

```text
1. Every protected route requires a verified identity.

2. No request may access another tenant's data.

3. Every object-ID-based endpoint performs object-level authorization.

4. Security-sensitive properties are never mass-assigned.

5. Role assignment is itself authorized.

6. Unknown permission -> deny.

7. Authorization failure -> never execute the business action.

8. Sensitive actions generate audit events.

9. JWT issuer/audience/expiry are verified according to the trust model.

10. Authorization-cache uncertainty never silently grants privileged access.
```

---

# 247. Final Security Checklist

```text
[ ] Authentication is server-side
[ ] Passwords hashed with a modern password hashing algorithm
[ ] Tokens validated, not merely decoded
[ ] Issuer checked where applicable
[ ] Audience checked where applicable
[ ] Expiration checked
[ ] RBAC matrix documented
[ ] Permissions explicit
[ ] Deny by default
[ ] Least privilege
[ ] Function-level authorization
[ ] Object-level authorization
[ ] Property-level authorization
[ ] Tenant isolation
[ ] Role assignment protected
[ ] Mass assignment blocked
[ ] Response fields minimized
[ ] Sensitive flows rate-limited
[ ] Audit logging
[ ] Authorization tests
[ ] Cross-tenant tests
[ ] Revocation/session strategy
[ ] Secrets outside source code
[ ] Authentication endpoint rate limits
[ ] Authorization cache invalidation if used
[ ] Failure mode documented
```

---

# 248. Final Architecture

```text
                              CLIENT
                                |
                                v
                           HTTPS / TLS
                                |
                                v
                         FastAPI / Gateway
                                |
                     +----------+----------+
                     |                     |
                Authentication        Rate Limit
                     |
                     v
                Verified Actor
                     |
                     v
              Coarse Authorization
                     |
                     v
                 Use Case
                     |
             +-------+-------+
             |               |
             v               v
        Object Policy    Tenant Policy
             |               |
             +-------+-------+
                     |
                     v
              Scoped Repository
                     |
                     v
                 PostgreSQL
                     |
                     +------> Audit Log

Optional layers:

Redis -> authorization cache / session / rate limiting
OAuth2 -> scopes
JWT -> authenticated identity/claims
Policy Engine -> complex authorization decisions
```

---

# 249. الصورة الذهنية النهائية

عندما يصل request:

```text
HTTP Request
    |
    v
Who are you?
    |
    v
Authentication
    |
    v
What are you allowed to do?
    |
    v
Permission / Scope
    |
    v
Which object?
    |
    v
Object Authorization
    |
    v
Which tenant?
    |
    v
Tenant Isolation
    |
    v
Which fields?
    |
    v
Property Authorization
    |
    v
Which business state/context?
    |
    v
Policy Evaluation
    |
 +--+--+
 |     |
DENY  ALLOW
 |     |
403    v
      Business Logic
           |
           v
       Database
           |
           v
        Audit
```

إذا حفظت هذا الـflow وفهمته بعمق، ستبدأ في تصميم APIs بطريقة مختلفة تمامًا.

---

# 250. القواعد الذهبية

> **Authentication tells you who the actor is.**

> **Authorization decides what the actor may do.**

> **RBAC organizes permissions around roles.**

> **Permission does not automatically imply access to every object.**

> **Every object identifier from the client must trigger object-level authorization thinking.**

> **Tenant isolation is an authorization invariant, not a UI feature.**

> **Never trust client-supplied role, tenant, owner, or privilege fields.**

> **JWT verification is not just signature checking; claims and trust boundaries matter.**

> **Deny by default. Least privilege. Explicit grants.**

> **Security rules must be enforced server-side and tested as code.**

> **When authorization cannot be evaluated safely for a sensitive action, silently allowing it is usually the wrong failure mode.**

> **RBAC is a foundation, not the end of authorization engineering.**

---

# 251. المراجع الرسمية

1. FastAPI — OAuth2 with Password, hashing, Bearer with JWT:  
   https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/

2. FastAPI — OAuth2 Scopes:  
   https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/

3. OWASP API Security Top 10 2023:  
   https://owasp.org/www-project-api-security/

4. OWASP — Broken Object Level Authorization:  
   https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/

5. OWASP — Broken Function Level Authorization:  
   https://owasp.org/API-Security/editions/2023/en/0xa5-broken-function-level-authorization/

6. OWASP — Broken Object Property Level Authorization:  
   https://owasp.org/API-Security/editions/2023/en/0xa3-broken-object-property-level-authorization/

7. OWASP Authorization Cheat Sheet:  
   https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html

8. OWASP Password Storage Cheat Sheet:  
   https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html

9. OWASP JSON Web Token Cheat Sheet:  
   https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_Cheat_Sheet.html

10. OWASP Session Management Cheat Sheet:  
    https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html

---

# 252. الخلاصة النهائية

لا تخرج من الدرس بفكرة:

```text
RBAC = roles table
```

الصورة الصحيحة هي:

```text
Authentication
    |
    v
Identity
    |
    v
Roles
    |
    v
Permissions / Scopes
    |
    v
Object-Level Policy
    |
    v
Tenant Isolation
    |
    v
Property-Level Rules
    |
    v
Context / Business Rules
    |
    v
Audit + Monitoring
```

والـAPI الآمنة ليست API فيها JWT فقط.

إنها API تستطيع الإجابة على كل سؤال من الأسئلة الآتية **قبل تنفيذ العملية**:

```text
من أنت؟

ماذا تريد أن تفعل؟

هل تملك permission لذلك؟

على أي object؟

هل object يخص tenant الخاص بك؟

هل علاقتك بالobject تسمح بالفعل؟

هل الحالة الحالية للobject تسمح؟

هل الحقول التي تريد تعديلها مسموح لك بها؟

هل العملية الحساسة تحتاج شرطًا إضافيًا؟

كيف سنسجل ما حدث؟
```

إذا استطاع نظامك الإجابة عن هذه الأسئلة بطريقة مركزية، قابلة للاختبار، ومبنية على **deny-by-default + least privilege + object-level checks + tenant isolation**، فقد انتقلت من مجرد إضافة Login إلى بناء **Authorization Architecture** حقيقية.
