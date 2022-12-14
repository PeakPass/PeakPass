import bcrypt
import psycopg2
from reader import CONNECTION_STRING

async def correct_login_information(email: str, password: str):
    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor()

    cur.execute("SELECT password FROM users WHERE email = %s", (email,))
    hashed_password = cur.fetchone()
    conn.close()

    if hashed_password:
        if bcrypt.checkpw(password.encode('utf-8'), str(hashed_password[0]).encode('utf-8')):
            return True
    return False
