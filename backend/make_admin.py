from app.db.session import engine
from sqlalchemy import text
conn = engine.connect()
conn.execute(text("UPDATE users SET is_superuser = true WHERE email = 'ahmed11morsi11@gmail.com'"))
conn.commit()
print('? Account elevated to Admin successfully!')
conn.close()
