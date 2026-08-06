import pyodbc

# Bağlantı bilgilerinizi buraya girin
server = 'localhost'  # veya '.\SQLEXPRESS', '127.0.0.1' vb.
database = 'tubitak_db'  # veritabanı adınız
username = 'your_username'  # SQL Server kullanıcı adınız
password = 'your_password'  # SQL Server şifreniz
driver = 'ODBC Driver 17 for SQL Server'  # ODBC sürücü adınız

# Bağlantı dizesini oluşturun
conn_str = f'DRIVER={{{driver}}};SERVER={server};DATABASE={database};UID={username};PWD={password}'

try:
    # Bağlantıyı açın
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    # Test sorgusu çalıştırın
    cursor.execute("SELECT @@VERSION")
    row = cursor.fetchone()
    print(f"SQL Server Versiyonu: {row[0]}")
    
    # Bağlantıyı kapatın
    cursor.close()
    conn.close()
    
    print("Bağlantı başarılı!")
except Exception as e:
    print(f"Bağlantı hatası: {e}")