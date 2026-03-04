import psycopg
conn = psycopg.connect('postgresql://postgres:postgres@localhost:5432/adaptiv_health')
cur = conn.cursor()
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='public' AND table_name='users' ORDER BY ordinal_position")
cols = cur.fetchall()
print(f"Local users table: {len(cols)} columns")
for col, dtype in cols:
    print(f"  {col:<40} {dtype}")
conn.close()
