import pyodbc

# Cadena de conexión corregida
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=ELVER;"
    "DATABASE=Diagnosticos;"
    "Trusted_Connection=yes"
)
try:
    conn = pyodbc.connect(conn_str)
    print("Conexión exitosa a SQL Server")
    conn.close()
except pyodbc.Error as e:
    print(f"Error de conexión: {str(e)}")