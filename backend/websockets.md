# Backend Engineering Mastery

# بناء واجهات الاتصال في الوقت الفعلي (Real-Time) باستخدام WebSockets مع FastAPI

> **الهدف:** فهم WebSockets من الأساس وحتى مستوى معماري متقدم: البروتوكول والـhandshake، lifecycle، message protocol، authentication، rooms، presence، reconnect، ordering، backpressure، multi-instance، Redis Pub/Sub، persistence، replay، observability، وربط WebSockets مع Celery/RabbitMQ.

---

## 1. لماذا نحتاج Real-Time؟

الـHTTP التقليدي يعمل غالبًا بهذا الشكل:

```text
Client
   |
   | HTTP Request
   v
FastAPI
   |
   | HTTP Response
   v
Client
```

مثلًا:

```http
GET /messages
```

السيرفر يرجع النتيجة، وينتهي الطلب. لو وصلت رسالة جديدة بعد ذلك، لا يوجد اتصال مفتوح يمكن للسيرفر أن يدفع عليه الرسالة.

أبسط حل هو **Polling**:

```text
GET /messages
GET /messages
GET /messages
GET /messages
...
```

لكن لو لا توجد تحديثات، فالعميل يرسل requests لا تضيف قيمة.

### Long Polling

العميل يرسل request والسيرفر ينتظر ظهور تحديث ثم يرد، وبعدها يبدأ العميل request جديدًا.

هذا أفضل من polling لكنه ما زال يعتمد على دورة:

```text
request -> wait -> response -> request جديد
```

### SSE

Server-Sent Events مناسب عندما يكون الاتجاه الأساسي:

```text
Server -> Client
```

لكن عندما نحتاج قناة ثنائية الاتجاه بشكل مستمر، WebSocket غالبًا هو النموذج الأنسب.

---

# 2. ما هو WebSocket؟

WebSocket يوفر:

> **Persistent Full-Duplex Communication**

أي أن الاتصال يبقى مفتوحًا ويستطيع الطرفان إرسال الرسائل في أي وقت:

```text
Client <====================> Server
       messages both ways
```

بدل:

```text
Request
Response
Request
Response
```

نحصل على:

```text
Connection
  |
  +-- Client -> Server
  +-- Server -> Client
  +-- Client -> Server
  +-- Server -> Client
  +-- Server -> Client
  +-- Client -> Server
  ...
```

WebSocket مناسب لأشياء مثل:

- Chat
- Live notifications
- Typing indicators
- Presence
- Collaborative editing
- Live dashboards
- Realtime monitoring
- Multiplayer state
- Support systems
- Live progress updates

لكن **WebSocket ليس حلًا تلقائيًا لكل شيء**. الاختيار الصحيح يعتمد على طبيعة التحديث، الاتجاه، عدد الاتصالات، latency، وطبيعة البيانات.

---

# 3. WebSocket يبدأ من HTTP ثم يترقى

اتصال WebSocket يبدأ من HTTP handshake ثم تتم الترقية إلى WebSocket.

بصورة مبسطة يرسل العميل:

```http
GET /ws HTTP/1.1
Host: example.com
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: ...
Sec-WebSocket-Version: 13
```

ويرد السيرفر:

```http
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: ...
```

بعد نجاح ذلك يصبح الاتصال WebSocket connection.

إذن endpoint WebSocket ليس مجرد `GET` آخر؛ إنه بداية **connection lifecycle** طويل العمر.

---

# 4. أهم فرق ذهني: Request Lifecycle مقابل Connection Lifecycle

في HTTP:

```text
start
  |
process
  |
response
  |
done
```

في WebSocket:

```text
CONNECTING
    |
ACCEPTED
    |
AUTHENTICATED
    |
CONNECTED
    |
MESSAGING
    |
DISCONNECTING
    |
CLOSED
```

لذلك تصميم WebSocket يحتاج التفكير في:

```text
Connection
State
Messages
Disconnect
Cleanup
Reconnect
Backpressure
```

---

# 5. أول WebSocket في FastAPI

```python
from fastapi import FastAPI, WebSocket

app = FastAPI()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    while True:
        data = await websocket.receive_text()

        await websocket.send_text(
            f"You said: {data}"
        )
```

الفكرة الأساسية مدعومة مباشرة في FastAPI/Starlette: `accept()`, `receive_text()`, `send_text()`, وعمليات JSON/bytes، مع `WebSocketDisconnect` عند انقطاع العميل.

---

# 6. ماذا يفعل كل جزء؟

## `@app.websocket("/ws")`

يعرّف WebSocket route.

## `await websocket.accept()`

يقبل الاتصال.

## `receive_text()`

ينتظر رسالة من العميل.

## `send_text()`

يرسل رسالة للعميل.

## `while True`

الاتصال لا ينتهي بعد رسالة واحدة؛ يمكن أن يعيش ويستقبل ويرسل عددًا كبيرًا من الرسائل.

---

# 7. التعامل مع Disconnect

العميل قد يغلق المتصفح أو يتوقف الإنترنت أو ينتقل الهاتف إلى وضع آخر.

لذلك:

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")

    except WebSocketDisconnect:
        print("Client disconnected")
```

وفي التطبيقات الأكبر نحتاج أيضًا `finally` لتنظيف الموارد.

---

# 8. Connection Manager

لو لديك 1000 مستخدم، تحتاج معرفة أي connections موجودة ومن يملك كل اتصال.

نسخة تعليمية بسيطة:

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, message: str):
        websocket = self.active_connections.get(user_id)
        if websocket:
            await websocket.send_text(message)
```

لكن هذا ليس تصميمًا نهائيًا.

---

# 9. User ليس Connection

المستخدم الواحد قد يملك:

```text
User 42
  |- Chrome
  |- Mobile App
  `- Tablet
```

إذن العلاقة غالبًا:

```text
1 user -> N connections
```

الأفضل أن تستخدم `connection_id` مستقلًا:

```text
connections:
  conn-a -> websocket
  conn-b -> websocket
  conn-c -> websocket

users:
  42 -> {conn-a, conn-b}
  51 -> {conn-c}
```

وهذا مهم جدًا في وجود أكثر من جهاز أو tab.

---

# 10. Connection Model

يمكن تمثيل connection بالشكل:

```python
from dataclasses import dataclass, field
from asyncio import Queue


@dataclass
class Connection:
    id: str
    user_id: int
    websocket: WebSocket
    outgoing: Queue = field(
        default_factory=lambda: Queue(maxsize=100)
    )
```

هنا بدأنا نفصل:

- هوية الاتصال
- صاحب الاتصال
- قناة WebSocket
- طابور الرسائل الخارجة

---

# 11. Rooms

في Chat قد يوجد:

```text
room: backend
room: python
room: ai
```

كل room لها مجموعة connections:

```python
rooms = {
    "backend": {"conn-1", "conn-2"},
    "python": {"conn-3", "conn-7"},
}
```

عند `join` نضيف connection للـroom، وعند disconnect أو leave نزيله.

---

# 12. Message Protocol

أكبر خطأ هو إرسال JSON عشوائي بلا contract.

سيئ:

```json
{
  "message": "hello"
}
```

الأفضل هو envelope موحد:

```json
{
  "id": "evt_123",
  "type": "chat.message",
  "version": 1,
  "timestamp": "2026-10-02T10:00:00Z",
  "room_id": "room-1",
  "data": {
    "text": "Hello"
  }
}
```

### لماذا `type`؟

لتمييز:

```text
chat.message
presence.update
typing.start
notification.new
room.joined
error
```

### لماذا `id`؟

للتعامل مع duplicate messages واكتشاف ما إذا وصل event أكثر من مرة.

### لماذا `version`؟

لأن الـprotocol سيتطور.

---

# 13. Commands مقابل Events

فرق معماري مهم جدًا.

## Client -> Server = Command

```json
{
  "type": "chat.send",
  "request_id": "req-10",
  "data": {
    "room_id": "42",
    "text": "hello"
  }
}
```

المعنى:

> افعل شيئًا.

## Server -> Client = Event

```json
{
  "id": "evt-123",
  "type": "chat.message.created",
  "data": {
    "message_id": "m-10",
    "sender_id": 42,
    "text": "hello"
  }
}
```

المعنى:

> حدث شيء بالفعل.

الفصل بين command وevent يجعل التصميم أوضح وأقوى.

---

# 14. Pydantic لرسائل WebSocket

بدل توزيع فحوصات `dict[...]` في الكود:

```python
from pydantic import BaseModel


class ChatSendData(BaseModel):
    room_id: str
    text: str


class ChatSendCommand(BaseModel):
    type: str
    request_id: str
    data: ChatSendData
```

ثم:

```python
payload = ChatSendCommand.model_validate(raw_message)
```

وهكذا أصبح WebSocket protocol typed وقابلًا للاختبار.

---

# 15. Chat Flow الصحيح

لا تجعل WebSocket هو business source of truth.

الـflow الأفضل غالبًا:

```text
Client
  |
  | chat.send
  v
WebSocket Server
  |
  | validate
  v
Authorize
  |
  v
PostgreSQL
  |
  | commit
  v
Create event
  |
  v
Broadcast
  |
  +--> Client A
  +--> Client B
  `--> Client C
```

أي:

```text
PostgreSQL = durable business state
WebSocket  = realtime delivery
```

---

# 16. لماذا الحفظ قبل البث؟

لو أرسلت الرسالة للعملاء أولًا ثم فشلت عملية DB:

```text
WebSocket broadcast
       |
       v
DB insert FAILED
```

العملاء شاهدوا شيئًا لم يحدث فعليًا في business state.

في بعض الأنظمة قد تقبل نماذج أخرى، لكن القرار يجب أن يكون مقصودًا.

---

# 17. History مقابل Realtime

استخدم HTTP للحصول على history:

```http
GET /rooms/42/messages
```

واستخدم WebSocket للتحديثات الحية:

```text
WS /ws
```

هذا يخلق فصلًا ممتازًا:

```text
HTTP      -> CRUD / History / Commands
WebSocket -> Live events / Presence / Typing
```

---

# 18. Presence

Presence تعني حالات مثل:

```text
online
offline
away
typing
```

لكن `online` ليست دائمًا حقيقة مطلقة. انقطاع الشبكة قد لا يظهر للسيرفر فورًا.

لذلك نستخدم غالبًا:

```text
heartbeat
last_seen
TTL
Disconnect detection
```

---

# 19. Heartbeat

على مستوى التطبيق يمكن أن يكون:

```json
{
  "type": "heartbeat"
}
```

ثم:

```json
{
  "type": "heartbeat_ack"
}
```

لكن يجب التفريق بين هذا وبين WebSocket protocol-level `Ping/Pong` control frames.

كما يجب ألا ترسل heartbeat بشكل مبالغ فيه؛ عند 100,000 connection يمكن أن يتحول معدل heartbeats إلى حمل ضخم.

---

# 20. Presence باستخدام Redis TTL

يمكن استخدام state مؤقت مثل:

```text
presence:user:42 = online
TTL = 30s
```

ويجدد heartbeat الـTTL.

إذا لم يعد هناك heartbeat وانتهت صلاحية المفتاح:

```text
user 42 -> considered offline
```

هذا state تقريبي وليس بالضرورة strong-consistency state.

---

# 21. Reconnect

الاتصال يمكن أن ينقطع بسبب:

- Wi-Fi
- Mobile network
- Sleep
- Server restart
- Load balancer
- Deployment
- Proxy timeout

إذن التطبيق يحتاج reconnect strategy.

لا تستخدم reconnect loop سريعًا بلا حدود؛ استخدم exponential backoff + jitter:

```text
attempt 1 -> 0.5s
attempt 2 -> 1s
attempt 3 -> 2s
attempt 4 -> 4s
attempt 5 -> 8s
```

مع jitter حتى لا يعيد آلاف العملاء الاتصال في نفس اللحظة.

---

# 22. Reconnect لا يعني Recovery

قد يكون العميل آخر مرة رأى:

```text
sequence = 100
```

ثم انقطع.

خلال الانقطاع حدثت:

```text
101
102
103
104
```

عند reconnect يجب أن يكون لديك قرار:

```text
lost forever?
replay?
snapshot?
resync?
```

إذا كانت الرسائل مهمة، تحتاج durable recovery strategy.

---

# 23. Sequence Numbers

أضف sequence:

```json
{
  "id": "evt-105",
  "sequence": 105,
  "type": "chat.message.created"
}
```

إذا استقبل العميل:

```text
101
103
```

يمكنه اكتشاف أن `102` مفقودة.

---

# 24. Replay

الـclient عند reconnect يمكن أن يرسل:

```text
last_seen = 101
```

ويطلب:

```text
replay 102..latest
```

ثم ينتقل إلى live mode.

هذا يعطي architecture قوية:

```text
Catch-up + Live Tail
```

---

# 25. Snapshot + Delta

ليس من الضروري الاحتفاظ بكل event إلى الأبد.

يمكن إرسال:

```text
Snapshot at T0
   |
   +-- event 1001
   +-- event 1002
   +-- event 1003
```

فالعميل يستعيد state بسرعة ثم يستهلك التغييرات الحديثة.

هذا pattern ممتاز للـlive games والـcollaborative state والـdashboards.

---

# 26. Redis Pub/Sub للـMulti-Instance

في server واحد يمكن حفظ connections في memory.

لكن مع:

```text
Load Balancer
   |
   +-- Server A
   +-- Server B
   `-- Server C
```

كل process لديه connection map مختلف.

لو user على A وuser على B، لا تستطيع A الوصول مباشرة إلى WebSocket object الموجود في B.

هنا نستخدم Redis Pub/Sub كـevent bus:

```text
Business event
    |
    v
Redis Pub/Sub
    |
    +--> Server A
    +--> Server B
    `--> Server C
```

كل server يوزع event على الـconnections المحلية لديه.

---

# 27. Redis Pub/Sub ليس Connection Manager

Redis لا يستطيع الاحتفاظ بـWebSocket object نفسه.

الـWebSocket يعيش داخل process.

Redis يعرف فقط:

```text
"هناك event يجب توزيعه"
```

والـRealtime server المحلي يعرف من يجب أن يستلم الرسالة.

إذن:

```text
Redis        = cross-process event distribution
Server memory = local connections
```

---

# 28. Redis Pub/Sub ليس Durable Replay

Redis Pub/Sub هو live fan-out model.

إذا كان subscriber offline وقت النشر، فالرسالة لا يتم حفظها له ليقرأها لاحقًا.

إذا احتجت persistence/replay، انظر إلى:

```text
Redis Streams
Kafka
PostgreSQL/Event Store
```

إذن:

```text
Pub/Sub -> live broadcast
Streams/Kafka -> replayable stream patterns
```

---

# 29. Room Broadcast عبر عدة Servers

مثال:

```text
Server A:
  conn-1 in room-42

Server B:
  conn-7 in room-42

Server C:
  no one in room-42
```

ينشر أحد السيرفرات:

```text
PUBLISH ws:room:42 {...}
```

كل nodes تتلقى event.

كل node يسأل محليًا:

```text
هل عندي connections في room-42؟
```

إذا نعم يرسل لها.

هذه أبسط بنية قابلة للتوسع من memory فقط.

---

# 30. Direct Messaging عبر عدة Servers

لو user 42 لديه:

```text
connection A -> server A
connection B -> server C
```

وسيرفر B يريد إرسال direct message للمستخدم، فهناك أكثر من pattern:

1. publish إلى كل nodes وتترك كل node تفحص الـlocal map.
2. تخزين `user -> server(s)` كـrouting hint في Redis.
3. استخدام realtime gateway/sharding أكثر تخصصًا.

الاختيار يعتمد على الحجم.

---

# 31. Backpressure

أهم مشكلة عملية في realtime.

إذا السيرفر ينتج:

```text
100 messages/sec
```

والعميل يستطيع استهلاك:

```text
10 messages/sec
```

فالتراكم هو:

```text
90 messages/sec
```

وبعد فترة تصبح المشكلة:

```text
Memory growth
Buffer growth
Latency growth
```

وهذا هو **Backpressure**.

---

# 32. Bounded Outgoing Queue

بدل queue لا نهائية، استخدم حدًا:

```python
from asyncio import Queue

queue = Queue(maxsize=100)
```

عندما تمتلئ queue، يجب أن توجد سياسة.

مثلاً:

```text
critical event -> لا يُسقط
important event -> قد ينتظر
ephemeral event -> قد يُسقط
slow consumer -> disconnect
```

---

# 33. One Reader + One Writer

من أفضل الأنماط لكل connection:

```text
             Connection
             /        \
         Reader      Writer
            |           ^
            |           |
       Incoming      Outgoing Queue
```

الـreader يستقبل ويعالج input.

الـwriter هو المسؤول عن الكتابة إلى socket.

هذا يقلل مشاكل التنافس بين أماكن متعددة تحاول إرسال البيانات في نفس اللحظة.

---

# 34. Writer Task

```python
async def writer(connection):
    try:
        while True:
            event = await connection.outgoing.get()
            await connection.websocket.send_json(event)
    except Exception:
        pass
```

والـreader:

```python
async def reader(connection):
    while True:
        message = await connection.websocket.receive_json()
        await handle_message(connection, message)
```

يجب إدارة lifecycle للـtasks مع cancellation: إذا مات reader ينبغي إيقاف writer، والعكس.

---

# 35. Event Coalescing

ليست كل الرسائل متساوية.

مثال cursor movement:

```text
cursor(10,10)
cursor(11,10)
cursor(12,10)
cursor(13,11)
...
```

لا يحتاج العميل بالضرورة كل حدث.

يمكن الاحتفاظ بآخر state فقط.

هذا يسمى:

# Event Coalescing

ومفيد جدًا في:

```text
cursor
mouse movement
presence refresh
live metrics
```

---

# 36. Rate Limiting

Connection حقيقية يمكن أن تنتج spam.

ضع limits على:

```text
messages / second / connection
messages / second / user
connections / IP
connections / user
message size
```

يمكن استخدام Redis counters أو rate limiting layer مناسبة.

---

# 37. Connection Exhaustion

المهاجم قد لا يحتاج إرسال آلاف الرسائل؛ يكفي فتح عدد ضخم من WebSockets.

كل connection تستهلك:

```text
memory
file descriptors
socket buffers
event-loop tasks
network resources
```

لذلك حماية النظام تشمل connection limits وrate limiting وcapacity planning.

---

# 38. Message Size Limits

لا تسمح برسائل ضخمة بلا حدود.

سياسة مثل:

```text
max message size = 64 KB
```

قد تكون مناسبة لبعض التطبيقات، لكن القيمة تعتمد على domain.

يجب رفض الرسائل الضخمة بأمان بدل السماح بتراكم الذاكرة.

---

# 39. Authentication

الـWebSocket connection يحتاج authentication مثل HTTP.

في browser native WebSocket API لا تتعامل بنفس سهولة `fetch` في تمرير arbitrary `Authorization` header من constructor.

الخيارات الشائعة:

```text
Cookies
Short-lived websocket tickets
Subprotocols
Query parameters (بحذر)
```

لا تضع access tokens طويلة العمر في query strings بلا دراسة، لأن URLs قد تظهر في logs أو history أو monitoring.

---

# 40. Origin Validation

لا تعتبر مجرد وصول WebSocket handshake كافيًا.

راجع `Origin` في browser-based applications، واسمح فقط بالـorigins المناسبة.

كذلك ضع في اعتبارك:

```text
SameSite
CSRF-like risks
Cookie scope
Secure
HttpOnly
```

---

# 41. Authorization

Authentication تقول:

> من أنت؟

Authorization تقول:

> ماذا يحق لك أن تفعل؟

مثلًا المستخدم 42 قد يكون authenticated لكنه لا يحق له:

```text
join room 99
read room 99
send to room 99
moderate room 99
```

يجب فحص authorization عند:

- Join room
- Send command
- Subscribe to data
- Request replay
- Access private events

---

# 42. Error Protocol

لا ترسل نصًا عشوائيًا فقط.

استخدم envelope واضحًا:

```json
{
  "type": "error",
  "code": "ROOM_FORBIDDEN",
  "message": "You cannot access this room",
  "request_id": "req-123"
}
```

ويمكن أن تكون لديك codes مثل:

```text
AUTH_REQUIRED
AUTH_INVALID
ROOM_NOT_FOUND
ROOM_FORBIDDEN
UNKNOWN_COMMAND
MESSAGE_TOO_LARGE
RATE_LIMITED
PROTOCOL_ERROR
```

---

# 43. Application-Level ACK

الـWebSocket transport لا يعني أن business command قد قُبل.

يمكن للعميل إرسال:

```json
{
  "type": "chat.send",
  "request_id": "req-10",
  "data": {}
}
```

والسيرفر يرد:

```json
{
  "type": "command.ack",
  "request_id": "req-10"
}
```

هذا **application-level acknowledgment** وليس هو نفسه TCP/WebSocket transport semantics.

---

# 44. Idempotency عند Reconnect

قد يحدث:

```text
Client sends command request_id=123
Server receives it
Network dies before response
Client reconnects
Client retries request_id=123
```

إذا command غير idempotent قد ينفذ مرتين.

لذلك في الأوامر المهمة استخدم `request_id` كـidempotency key داخل business layer عندما يلزم.

مثال:

```text
request_id = abc
already_processed?
  YES -> return previous result
  NO  -> execute + record
```

---

# 45. Ordering

لا تفترض ترتيبًا عالميًا مطلقًا عندما تدخل:

```text
multiple servers
multiple workers
async processing
retries
reconnect
```

إذا كان ترتيب الأحداث مهمًا، أضف sequence numbers مناسبة للـscope.

قد يكون الترتيب:

```text
per room
per aggregate
per user
```

وليس بالضرورة global.

---

# 46. WebSocket لا يوفر Exactly-Once Business Semantics

WebSocket transport لا يعني:

```text
exactly once
```

إذا كانت لديك عملية حساسة مثل payment، يجب أن تكون business state في storage موثوق، ويجب أن تكون العملية نفسها idempotent وفق الـbusiness key.

نفس الفكرة التي تعلمتها في Celery/RabbitMQ تنطبق هنا:

```text
network failure
+ retry
= potential duplicate
```

---

# 47. Redis Pub/Sub مقابل Redis Streams

## Pub/Sub

```text
live fan-out
low persistence
offline subscriber misses events
```

## Streams

```text
persistent entries
replay
consumer groups
more complex delivery semantics
```

إذا كان هدفك مجرد نشر event حي إلى realtime nodes، Pub/Sub قد يكون كافيًا.

إذا أردت catch-up/replay durable، Streams أو Kafka أو event store قد يكون أنسب.

---

# 48. Multi-Instance Architecture

بنية عملية:

```text
                         Clients
                            |
                     Load Balancer
                            |
          +-----------------+-----------------+
          |                 |                 |
          v                 v                 v
      Server A          Server B          Server C
          |                 |                 |
   Local Connections  Local Connections  Local Connections
          \                 |                 /
           +---------------+----------------+
                           |
                    Redis Pub/Sub
                           |
                    Business Services
                           |
                     PostgreSQL
```

هذه تفصل:

```text
local socket state
```

عن:

```text
cross-process events
```

---

# 49. WebSocket مع Celery/RabbitMQ

يمكنك جمع ما تعلمته سابقًا.

مثال:

```text
Client
  |
  | generate_report
  v
FastAPI WebSocket
  |
  v
RabbitMQ
  |
  v
Celery Worker
  |
  v
Heavy Processing
  |
  v
Redis Pub/Sub / Event Bus
  |
  v
Realtime Node
  |
  v
WebSocket Client
```

أي أن WebSocket هو **قناة realtime**، بينما Celery/RabbitMQ مسؤولان عن **heavy background execution**.

---

# 50. Business State مقابل Realtime Delivery

هذه من أهم القواعد:

```text
PostgreSQL
    = durable business state

WebSocket
    = realtime delivery

Redis Pub/Sub
    = cross-node fan-out

RabbitMQ + Celery
    = background work
```

لا تجعل WebSocket بديلًا عن database.

ولا تجعل Redis Pub/Sub بديلًا عن durable event history.

---

# 51. Notifications Architecture

لو حدث شيء مهم:

```text
Business Service
       |
       +--> persist notification in DB
       |
       `--> publish realtime event
                     |
                     v
                Redis Pub/Sub
                     |
             +-------+-------+
             v               v
         Node A            Node B
             |               |
             v               v
          WebSocket       WebSocket
```

إذا المستخدم offline، يظل notification في DB.

عند العودة:

```http
GET /notifications
```

ويمكن أن يحصل على state الذي فاته.

هذه architecture أقوى بكثير من الاعتماد على WebSocket وحده.

---

# 52. Realtime Chat Architecture

```text
                    Client
                 /         \
                /           \
             HTTP         WebSocket
              |                |
              v                v
        History/API       Realtime Node
              |                |
              v                v
         PostgreSQL       Local Manager
              |                |
              +--------+-------+
                       |
                  Redis Pub/Sub
                       |
              +--------+--------+
              |                 |
        Realtime Node B   Realtime Node C
```

---

# 53. Message Flow في Chat

Client sends:

```json
{
  "type": "chat.send",
  "request_id": "r2",
  "data": {
    "room_id": "42",
    "text": "Hello"
  }
}
```

السيرفر:

```text
1. Parse
2. Validate
3. Authenticate
4. Authorize room
5. Persist message
6. Commit
7. Build event
8. Publish/broadcast
```

والـevent:

```json
{
  "id": "evt-100",
  "type": "chat.message.created",
  "sequence": 100,
  "room_id": "42",
  "data": {
    "message_id": "m100",
    "sender_id": 17,
    "text": "Hello"
  }
}
```

---

# 54. Typing Indicators

Typing events غالبًا ephemeral:

```json
{
  "type": "typing.start"
}
```

لا تحتاج عادة إلى حفظ كل keypress في PostgreSQL.

يمكن أن تكون:

```text
WebSocket
+
local memory / Redis Pub/Sub
```

حسب architecture.

---

# 55. Slow Client Protection

ضع لكل connection outgoing queue محدودة:

```python
Queue(maxsize=100)
```

إذا امتلأت:

```text
critical   -> wait / preserve
important  -> policy
ephemeral  -> drop/coalesce
slow client -> disconnect if necessary
```

لا توجد سياسة واحدة صحيحة لكل domain؛ يجب تحديدها حسب business semantics.

---

# 56. Graceful Shutdown

عند deployment لا تقتل العملية دون تفكير.

أفضل flow:

```text
Stop accepting new connections
        |
Drain/close existing connections
        |
Clients detect close
        |
Reconnect with backoff
        |
New nodes accept connections
```

وقد تحتاج versioned protocol حتى يعمل client القديم مؤقتًا مع server الجديد.

---

# 57. Load Balancer وSticky Sessions

WebSocket اتصال طويل العمر، لذلك الاتصال الحالي يبقى على node معين.

Sticky sessions قد تكون مفيدة في بعض architectures، لكنها ليست بديلًا عن shared event distribution.

حتى لو كان العميل ثابتًا على Server A:

```text
User A -> Server A
User B -> Server B
```

ما زلنا نحتاج وسيلة ليعرف A أحداث B، والعكس.

---

# 58. Observability

في realtime لا تكتفِ بـ"السيرفر شغال".

راقب:

```text
active_connections
connections_per_instance
new_connections_per_sec
disconnects_per_sec
messages_in_total
messages_out_total
broadcast_latency
reconnects_total
slow_clients_total
queue_overflow_total
connection_errors_total
```

وكذلك:

```text
P50 message latency
P95 message latency
P99 message latency
```

---

# 59. Correlation IDs

ربط lifecycle الكامل مهم:

```text
HTTP request_id
       |
       v
task_id / event_id
       |
       v
worker logs
       |
       v
WebSocket event
```

بهذا يمكن تتبع رحلة عملية واحدة عبر عدة services.

---

# 60. Queue Depth وFan-Out

لو room لديها 500,000 clients وأرسلت event واحدًا، فهذا قد يعني:

```text
1 event
-> 500,000 socket writes
```

هذه مشكلة fan-out، وليست مشكلة WebSocket API فقط.

الحلول المحتملة بحسب النظام:

```text
throttling
coalescing
delta updates
partitioning
regional fan-out
specialized gateways
```

---

# 61. WebSocket ليس دائمًا الخيار الأفضل

استخدم HTTP عندما يكون النظام request-oriented.

استخدم Polling عندما تكون التحديثات نادرة جدًا والبساطة أهم.

استخدم SSE عندما يكون Server -> Client هو الاتجاه الرئيسي.

استخدم WebSocket عندما تحتاج bidirectional low-latency communication.

استخدم RabbitMQ/Celery للـbackground work.

استخدم Redis Pub/Sub للـlive fan-out عندما تناسب semantics.

استخدم Streams/Kafka عند الحاجة إلى event stream durable/replayable.

---

# 62. Protocol Design Example

## Join Room

Client:

```json
{
  "type": "room.join",
  "request_id": "r1",
  "data": {
    "room_id": "backend"
  }
}
```

Server:

```json
{
  "type": "room.joined",
  "request_id": "r1",
  "data": {
    "room_id": "backend"
  }
}
```

## Send Chat

```json
{
  "type": "chat.send",
  "request_id": "r2",
  "data": {
    "room_id": "backend",
    "text": "Hello"
  }
}
```

## Error

```json
{
  "type": "error",
  "code": "ROOM_FORBIDDEN",
  "request_id": "r2",
  "message": "Access denied"
}
```

---

# 63. مشروع الدرس: Production Realtime Chat Platform

## هيكل المشروع

```text
backend-mastery/
├── app/
│   ├── main.py
│   ├── realtime/
│   │   ├── router.py
│   │   ├── connection.py
│   │   ├── manager.py
│   │   ├── protocol.py
│   │   ├── heartbeat.py
│   │   └── publisher.py
│   ├── chat/
│   │   ├── models.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   └── events.py
│   └── infrastructure/
│       └── redis.py
├── tests/
│   ├── test_websocket.py
│   ├── test_protocol.py
│   ├── test_chat.py
│   └── test_realtime.py
└── README.md
```

---

# 64. المستوى الأول: Echo

نفذ:

```text
WS /ws
```

والـflow:

```text
receive_text
     |
     v
send_text
```

معيار النجاح: client يرسل `hello` ويحصل على `echo: hello`.

---

# 65. المستوى الثاني: Connection Manager

أضف:

```text
connection_id
user_id
connect
 disconnect
 cleanup
```

اختبر أكثر من client.

---

# 66. المستوى الثالث: Rooms

أضف:

```text
room.join
room.leave
```

ثم broadcast إلى members فقط.

---

# 67. المستوى الرابع: Persistence

نفذ:

```text
chat.send
   -> validate
   -> authorize
   -> DB
   -> commit
   -> event
   -> broadcast
```

---

# 68. المستوى الخامس: Presence

أضف:

```text
online/offline
heartbeat
last_seen
TTL
```

اختبر disconnect غير المتوقع.

---

# 69. المستوى السادس: Redis Pub/Sub

شغل نسختين من FastAPI:

```text
Server A
Server B
```

Client A على A وClient B على B، وكلاهما في نفس room.

يجب أن ترسل A message ويستقبلها B.

هذه أول تجربة Distributed Realtime حقيقية.

---

# 70. المستوى السابع: Reconnect + Sequence

أضف:

```text
last_event_id
sequence
reconnect
catch-up
```

حدد أين تحفظ الأحداث إذا كان replay مطلوبًا.

---

# 71. المستوى الثامن: Backpressure

اجعل:

```python
Queue(maxsize=10)
```

ثم أرسل events أسرع من client.

طبّق سياسة واضحة:

```text
drop
coalesce
disconnect
```

بحسب event type.

---

# 72. المستوى التاسع: Security

أضف:

```text
authentication
authorization
origin validation
message size limit
connection limits
rate limits
```

---

# 73. المستوى العاشر: Observability

أضف:

```text
active connections
messages in/out
disconnects
reconnects
queue overflow
broadcast latency
errors
```

وسجل:

```text
connection_id
user_id
room_id
request_id
event_id
```

---

# 74. المستوى الحادي عشر: Graceful Deploy

شغّل:

```text
Server A
Server B
```

ثم أوقف A بطريقة graceful.

يجب أن يكتشف العملاء الانقطاع ويعيدوا الاتصال، بينما B يستمر.

---

# 75. المستوى الثاني عشر: Load Test

اختبر تدريجيًا:

```text
100 connections
1000
5000
10000
```

وقس:

```text
CPU
RAM
network
latency
Redis load
connection time
message throughput
```

لا تفترض أن النظام scalable قبل القياس.

---

# 76. تمارين تنفيذية أساسية

## Exercise 1 — Echo

**الهدف:** فهم lifecycle الأساسي.

**التنفيذ:** `WS /ws`، ثم `receive_text()` و`send_text()`.

**القبول:** echo صحيح.

---

## Exercise 2 — Multiple Connections

افتح tabين للمستخدم نفسه.

**القبول:** كلاهما يسجلان connection مستقلًا.

---

## Exercise 3 — Disconnect Cleanup

أغلق connection فجأة.

**القبول:** لا يبقى dead socket في manager.

---

## Exercise 4 — Room Broadcast

ثلاثة clients في room واحدة.

**القبول:** رسالة A تصل إلى أعضاء room حسب policy.

---

## Exercise 5 — Room Authorization

حاول دخول room لا يحق للمستخدم دخولها.

**القبول:** `ROOM_FORBIDDEN`.

---

## Exercise 6 — Persistence Before Broadcast

اجعل DB insert يفشل عمدًا.

**القبول:** لا يتم broadcast لرسالة لم تُحفظ وفق policy المشروع.

---

## Exercise 7 — Typing Indicators

نفذ `typing.start/stop` دون حفظ كل keypress.

**القبول:** event حي سريع بدون ضغط غير ضروري على DB.

---

## Exercise 8 — Redis Pub/Sub

شغل serverين واختبر cross-node broadcast.

**القبول:** client على A يرى event صدر عبر B والعكس.

---

## Exercise 9 — Reconnect

افصل client ثم أعد الاتصال.

**القبول:** لا توجد reconnect storm، ويوجد backoff.

---

## Exercise 10 — Sequence Numbers

اعمل `sequence` لكل event.

**القبول:** client يكتشف gap مثل 101 ثم 103.

---

## Exercise 11 — Replay

نفّذ recovery للأحداث المفقودة إن كانت business requirement.

**القبول:** client يستطيع catch-up قبل العودة للـlive stream.

---

## Exercise 12 — Slow Consumer

أوقف قراءة client عمدًا.

**القبول:** outgoing queue لا تنمو بلا حدود، وتُطبّق policy واضحة.

---

## Exercise 13 — Message Rate Limit

حاول إرسال 100 message/sec من مستخدم واحد.

**القبول:** server يحد المعدل ولا ينهار.

---

## Exercise 14 — Duplicate Command

أرسل نفس `request_id` مرتين.

**القبول:** command الحساس idempotent إذا كان ذلك جزءًا من التصميم.

---

## Exercise 15 — Oversized Message

أرسل رسالة أكبر من الحد.

**القبول:** رفض آمن دون memory growth غير محدود.

---

## Exercise 16 — Graceful Shutdown

شغّل 50 client ثم أعد تشغيل server بطريقة graceful.

**القبول:** clients reconnect بصورة متدرجة.

---

# 77. أسئلة الفهم — المستوى الأساسي

1. ما هو WebSocket؟
2. لماذا لا يكفي HTTP للـrealtime في بعض الحالات؟
3. ما الفرق بين polling وlong polling؟
4. ما الفرق بين SSE وWebSocket؟
5. ما هو handshake؟
6. لماذا WebSocket connection طويلة العمر؟
7. ما وظيفة `accept()`؟
8. لماذا نحتاج `WebSocketDisconnect`؟

---

# 78. المستوى المتوسط

9. لماذا user ليس connection؟
10. كيف يمكن لمستخدم امتلاك عدة tabs/devices؟
11. ما هو room؟
12. لماذا نحتاج message type؟
13. ما الفرق بين event وcommand؟
14. لماذا نحتاج message ID؟
15. ما وظيفة heartbeat؟
16. لماذا نحتاج reconnect backoff؟

---

# 79. المستوى المتقدم

17. ما هو backpressure؟
18. ما هو slow consumer؟
19. لماذا outgoing queue يجب أن تكون bounded؟
20. لماذا one writer لكل connection مفيد؟
21. لماذا لا يكفي local memory مع عدة servers؟
22. كيف يعمل Redis Pub/Sub في realtime architecture؟
23. لماذا Redis Pub/Sub لا يوفر replay؟
24. ما الفرق بين event وstate؟
25. كيف تصمم presence؟
26. كيف تكتشف missing events؟

---

# 80. المستوى Senior

27. صمم Chat على ثلاثة servers.
28. كيف توصل event من Server A إلى Client على Server B؟
29. كيف تمنع duplicate command بعد reconnect؟
30. كيف تدعم replay؟
31. كيف تمنع slow client من استهلاك الذاكرة؟
32. كيف تمنع connection exhaustion؟
33. كيف تتعامل مع graceful shutdown؟
34. كيف توزع room hot جدًا؟
35. متى تستخدم Redis Pub/Sub ومتى Redis Streams/Kafka؟
36. كيف تراقب P99 realtime latency؟

---

# 81. أهم 25 قاعدة احفظها

```text
1. WebSocket = long-lived bidirectional transport.
2. WebSocket is not a database.
3. WebSocket is not a durable event log.
4. HTTP and WebSocket can coexist.
5. User != Connection.
6. One user may have many connections.
7. Connection lifecycle must be explicit.
8. Every message needs a contract.
9. Separate commands from events.
10. Validate every incoming message.
11. Authenticate the connection.
12. Authorize room/action access.
13. Business state belongs in durable storage.
14. Realtime delivery is a separate concern.
15. Reconnect is mandatory in real systems.
16. Reconnect needs exponential backoff + jitter.
17. Duplicate commands are possible after reconnect.
18. Idempotency protects business effects.
19. Slow clients create backpressure.
20. Outgoing queues should be bounded.
21. Multi-instance requires cross-node event distribution.
22. Redis Pub/Sub is live fan-out, not durable replay.
23. Sequence numbers help detect gaps.
24. Observability is part of the design.
25. Real-time engineering is about correctness under failure, not just low latency.
```

---

# 82. Decision Matrix

| الحاجة | الاختيار المحتمل |
|---|---|
| CRUD API | HTTP |
| Updates نادرة | Polling |
| Server -> Client stream | SSE |
| Bidirectional low-latency | WebSocket |
| Background jobs | Celery |
| Work queue | RabbitMQ |
| Live fan-out | Redis Pub/Sub |
| Replayable stream | Redis Streams / Kafka |
| Durable business state | PostgreSQL |

---

# 83. سؤال التصميم الحقيقي

لو طلب منك شخص:

> "ابني Chat بـFastAPI"

لا تبدأ بالكود.

اسأل:

```text
هل نحتاج history؟
هل الرسائل durable؟
هل يوجد rooms؟
هل المستخدم لديه عدة devices؟
هل يوجد presence؟
هل يوجد typing؟
هل يوجد read receipts؟
كم عدد concurrent connections؟
كم أقصى حجم للرسالة؟
ما rate limit؟
هل نحتاج replay؟
هل يوجد أكثر من server؟
كيف يتم cross-node broadcast؟
ماذا يحدث عند reconnect؟
ماذا يحدث أثناء deployment؟
ماذا يحدث إذا Redis وقع؟
ماذا يحدث لو client بطيء؟
```

هذه الأسئلة هي الفرق بين معرفة API وبين هندسة نظام realtime.

---

# 84. الصورة المعمارية النهائية

```text
                             CLIENTS
                    +----------+----------+
                    |          |          |
                    v          v          v
                 Browser    Mobile     Tablet
                    |          |          |
                    +----------+----------+
                               |
                           WebSocket
                               |
                      +--------v--------+
                      |  Load Balancer  |
                      +--------+--------+
                               |
              +----------------+----------------+
              |                |                |
              v                v                v
        Realtime A       Realtime B       Realtime C
              |                |                |
       local sockets      local sockets      local sockets
              \                |                /
               +---------------+---------------+
                               |
                        Redis Pub/Sub
                               |
                    +----------+----------+
                    |                     |
                    v                     v
             Business Services       Presence State
                    |                     |
                    v                     v
               PostgreSQL              Redis
```

وفي حالة heavy background processing:

```text
Client
  |
  v
FastAPI / WebSocket
  |
  v
RabbitMQ
  |
  v
Celery Workers
  |
  v
Heavy Work
  |
  v
Event Bus / Redis PubSub
  |
  v
Realtime Nodes
  |
  v
WebSocket
  |
  v
Client
```

---

# 85. العلاقة مع الدروس السابقة

لقد تعلمت في Redis:

```text
Cache
TTL
Invalidation
Stampede
```

وفي Celery/RabbitMQ:

```text
Queue
Worker
ACK
Retry
Backoff
Idempotency
```

والآن في WebSockets ستجمع:

```text
Persistent connection
Realtime events
Presence
Reconnect
Backpressure
Multi-instance distribution
```

ثم في مراحل الـDistributed Systems ستجمع كل ذلك مع:

```text
Kafka
Event-driven architecture
Microservices
Consistency
Observability
```

---

# 86. الخلاصة

WebSocket نفسه بسيط نسبيًا:

```python
await websocket.accept()
await websocket.receive_json()
await websocket.send_json(...)
```

لكن **نظام Real-Time Production ليس بسيطًا**.

الهندسة الحقيقية تبدأ عندما تسأل:

```text
ماذا يحدث عندما ينقطع الاتصال؟
ماذا يحدث عندما يتصل المستخدم من جهازين؟
ماذا يحدث عندما يصبح client بطيئًا؟
ماذا يحدث إذا وصلت الرسالة مرتين؟
ماذا يحدث إذا فقد client events أثناء offline؟
ماذا يحدث إذا شغلت 10 servers؟
ماذا يحدث إذا Redis وقع؟
ماذا يحدث أثناء deployment؟
أين توجد الحقيقة الدائمة؟
كيف أراقب latency وconnection health؟
كيف أحمي النظام من flood أو connection exhaustion؟
```

إذا استطعت الإجابة عن هذه الأسئلة، فأنت لا تعرف WebSockets فقط؛ أنت بدأت تفهم **Real-Time Backend Systems Engineering**.

---

# 87. القاعدة الذهبية

> **WebSocket هو قناة نقل.**
>
> أما durability، ordering، replay، idempotency، authorization، business correctness، scalability، وfailure handling — فأنت من يصممها فوق هذه القناة.

وهذه هي العقلية التي نريدها في بقية مسار Backend Engineering.

---

## مراجع رسمية

- FastAPI — WebSockets: https://fastapi.tiangolo.com/advanced/websockets/
- Starlette — WebSockets: https://www.starlette.dev/websockets/
- Redis — Pub/Sub: https://redis.io/docs/latest/develop/pubsub/
- Redis — Pub/Sub use cases: https://redis.io/docs/latest/develop/use-cases/pub-sub/

