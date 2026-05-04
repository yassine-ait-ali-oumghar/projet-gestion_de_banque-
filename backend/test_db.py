import mysql.connector

connexion = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  # XAMPP = vide
    database="projet_python_banque"
)

if connexion.is_connected():
    print("Connexion réussie !")

cursor = connexion.cursor() 

cursor.execute("SELECT * FROM users")

for row in cursor.fetchall():
    print(row)