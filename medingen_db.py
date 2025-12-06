import sqlite3
from datetime import date, timedelta
import random
import os

# Connect / Create database
conn = sqlite3.connect('medingen.db')
cur = conn.cursor()


# Create customers table

cur.execute("""
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL
);
""")

# Create orders table

cur.execute("""
CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    medicine_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    total_amount REAL NOT NULL,
    status TEXT NOT NULL,
    address TEXT NOT NULL,
    payment_mode TEXT,
    payment_status TEXT,
    order_date TEXT NOT NULL,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY(medicine_id) REFERENCES medicines(medicine_id)
);
""")


# Create order_items table (multiple -items per order)
cur.execute("""
CREATE TABLE IF NOT EXISTS order_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    medicine_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,            -- price per strip at time of purchase
    line_total REAL NOT NULL,       -- quantity * price
    expiry_date TEXT NOT NULL,      -- store expiry of that strip
    FOREIGN KEY(order_id) REFERENCES orders(order_id),
    FOREIGN KEY(medicine_id) REFERENCES medicines(medicine_id)
);
""")



#prescription_requests


cur.execute("""
CREATE TABLE IF NOT EXISTS prescription_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    medicine_name TEXT NOT NULL,
    request_date TEXT NOT NULL
);
""")


# Create payments table

cur.execute("""
CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders(order_id)
);
""")


# Create medicines table
cur.execute("""
CREATE TABLE IF NOT EXISTS medicines (
    medicine_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    salt_name TEXT NOT NULL,
    price REAL NOT NULL,
    no_of_tablets INTEGER NOT NULL,
    stock_in_strips INTEGER NOT NULL,
    prescription_required TEXT CHECK(prescription_required IN ('yes', 'no')),
    expiry_date TEXT NOT NULL
);
""")

# Sample medicine dataset: 
base_data = [
    ("Dolo 650", "Paracetamol", 30, "no", 15),
    ("Crocin Advance", "Paracetamol", 28, "no", 15),
    ("Calpol 500", "Paracetamol", 26, "no", 15),
    ("Augmentin 625", "Amoxicillin + Clavulanic Acid", 120, "yes", 10),
    ("Azithral 500", "Azithromycin", 95, "yes", 5),
    ("Cefixime 200", "Cefixime", 110, "yes", 10),
    ("Montair LC", "Levocetirizine + Montelukast", 180, "yes", 10),
    ("Allegra 180", "Fexofenadine", 160, "no", 10),
    ("Ecosprin 75", "Aspirin", 20, "no", 14),
    ("Atorva 10", "Atorvastatin", 95, "yes", 10),
    ("Amlokind 5", "Amlodipine", 25, "no", 15),
    ("Telma 40", "Telmisartan", 150, "yes", 10),
    ("Metformin 500", "Metformin", 28, "no", 15),
    ("Glycomet GP1", "Metformin + Glimepiride", 60, "yes", 15),
    ("Pantocid DSR", "Pantoprazole + Domperidone", 130, "yes", 10),
    ("Nexpro RD", "Esomeprazole + Domperidone", 135, "yes", 10),
    ("Rabekind D", "Rabeprazole + Domperidone", 120, "yes", 10),
    ("Zifi 200", "Cefixime", 110, "yes", 10),
    ("Sinarest", "Chlorpheniramine + Paracetamol + Phenylephrine", 45, "no", 10),
    ("Vicks Action 500", "Paracetamol + Phenylephrine + Caffeine", 30, "no", 10),
    ("Benadryl", "Diphenhydramine", 95, "no", 1),
    ("Cetzine", "Cetirizine", 45, "no", 10),
    ("Okacet", "Cetirizine", 42, "no", 10),
    ("Omez 20", "Omeprazole", 40, "no", 10),
    ("Aciloc 150", "Ranitidine", 35, "no", 10),
    ("Pan 40", "Pantoprazole", 70, "yes", 10),
    ("Razo D", "Rabeprazole + Domperidone", 130, "yes", 10),
    ("Shelcal 500", "Calcium Carbonate + Vitamin D3", 90, "no", 15),
    ("Calcimax", "Calcium Citrate + Vitamin D3", 100, "no", 15),
    ("Neurobion Forte", "Vitamin B complex", 55, "no", 10),
    ("Liv 52", "Herbal liver formulation", 75, "no", 10),
    ("Thyronorm 50", "Thyroxine", 110, "yes", 100),
    ("Thyrox 75", "Thyroxine", 125, "yes", 100),
    ("Ecosprin AV 75", "Aspirin + Atorvastatin", 140, "yes", 10),
    ("Drotin 40", "Drotaverine", 70, "no", 10),
    ("Spasmonil", "Dicyclomine + Paracetamol", 65, "no", 10),
    ("Zincovit", "Multivitamin + Zinc", 85, "no", 15),
    ("Revital H", "Ginseng + Multivitamins", 125, "no", 10),
    ("Limcee 500", "Vitamin C", 35, "no", 15),
    ("Celin 500", "Vitamin C", 38, "no", 15),
    ("Combiflam", "Ibuprofen + Paracetamol", 50, "no", 15),
    ("Brufen 400", "Ibuprofen", 45, "no", 15),
    ("Betadine Gargle", "Povidone Iodine", 70, "no", 1),
    ("Himalaya Ashwagandha", "Ashwagandha", 120, "no", 60),
    ("Evion 400", "Vitamin E", 45, "no", 10),
    ("Metrogyl 400", "Metronidazole", 60, "yes", 10),
    ("Flagyl 400", "Metronidazole", 55, "yes", 10),
    ("Cepodem 200", "Cefpodoxime", 145, "yes", 10),
    ("Monocef 1gm", "Ceftriaxone", 210, "yes", 1),
    ("Becosules", "Vitamin B Complex", 80, "no", 15),
]

# Insert random stock and expiry dates
for med in base_data:
    expiry = date.today() + timedelta(days=random.randint(300, 900))
    stock_in_strips = random.randint(10, 150)
    cur.execute("""
    INSERT INTO medicines (name, salt_name, price, no_of_tablets, stock_in_strips, prescription_required, expiry_date)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (med[0], med[1], med[2], med[4], stock_in_strips, med[3], expiry.isoformat()))

conn.commit()
conn.close()

print("✅ Database 'medingen.db' created successfully with 50 medicines (including stock & tablet details).")
