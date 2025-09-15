fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
python-dotenv==1.0.0
web: uvicorn server:app --host=0.0.0.0 --port=${PORT}
worker: python discord_bot.py