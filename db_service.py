import sqlite3
import os
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
from datetime import datetime

load_dotenv()

DB_PATH = os.getenv("DB_PATH")




def get_connection():
    return sqlite3.connect(DB_PATH)



# CUSTOMER SERVICES

def get_customer_by_phone(phone):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE phone = ?", (phone,))
    result = cur.fetchone()
    conn.close()
    return result


def insert_customer(name, phone, email):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO customers (name, phone, email) VALUES (?, ?, ?)",
        (name, phone, email)
    )
    conn.commit()
    conn.close()
    return True



# MEDICINE SERVICES

def get_medicine_by_name(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM medicines WHERE LOWER(name) = LOWER(?)", (name,))
    result = cur.fetchone()
    conn.close()
    return result


def get_substitutes_by_salt(salt_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM medicines WHERE LOWER(salt_name) = LOWER(?)",
        (salt_name,)
    )
    substitutes = cur.fetchall()
    conn.close()
    return substitutes

def get_medicine_fuzzy(user_input):
    """
    Returns best fuzzy match from medicines table.
    """

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM medicines")
    all_medicines = cur.fetchall()
    conn.close()

    best_match = None
    best_score = 0

    for med in all_medicines:
        name = med[1]  # medicine name

        score = fuzz.token_set_ratio(user_input.lower(), name.lower())

        if score > best_score:
            best_score = score
            best_match = med

    # Avoid wrong random matches
    if best_score >= 60:
        return best_match

    return None



'''def get_medicine_fuzzy_candidates(user_input, limit=5, min_score=60):--->for multiple matches-->in future
    """
    Returns top-N fuzzy matches from medicines table.
    Output: list of (medicine_row, score)
    Sorted by best score first.
    Only items with score >= min_score are returned.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM medicines")
    all_medicines = cur.fetchall()
    conn.close()

    user = user_input.lower().strip()

    scored = []
    for med in all_medicines:
        name = med[1]  # medicine name
        score = fuzz.token_set_ratio(user, name.lower())
        scored.append((med, score))

    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    # Keep only items that meet threshold
    candidates = [(m, s) for (m, s) in scored if s >= min_score]

    # Limit count
    return candidates[:limit]'''


# ORDER SERVICES

def create_order(customer_id, medicine_id, quantity, total_amount, address):
    conn = get_connection()
    cur = conn.cursor()

    order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO orders 
        (customer_id, medicine_id, quantity, total_amount, status, address, order_date)
        VALUES (?, ?, ?, ?, 'pending', ?, ?)
    """, (customer_id, medicine_id, quantity, total_amount, address, order_date))

    conn.commit()
    order_id = cur.lastrowid
    conn.close()

    return order_id


def update_order_payment(order_id, mode, payment_status):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE orders
        SET payment_mode = ?, payment_status = ?
        WHERE order_id = ?
    """, (mode, payment_status, order_id))

    conn.commit()
    conn.close()
    return True

def update_order_status(order_id, status):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE orders
        SET status = ?
        WHERE order_id = ?
    """, (status, order_id))

    conn.commit()
    conn.close()
    return True



def get_order(order_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    result = cur.fetchone()
    conn.close()
    return result

# PAYMENT SERVICES

def insert_payment(order_id, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO payments (order_id, status) VALUES (?, ?)",
        (order_id, status)
    )
    conn.commit()
    payment_id = cur.lastrowid
    conn.close()
    return payment_id


def update_payment_status(payment_id, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE payments SET status = ? WHERE payment_id = ?",
        (status, payment_id)
    )
    conn.commit()
    conn.close()
    return True


def get_payment_status(order_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM payments WHERE order_id = ?", (order_id,))
    result = cur.fetchone()
    conn.close()
    return result



# PRESCRIPTION REQUEST SERVICES

def insert_prescription_request(customer_name, customer_phone, medicine_name):
    conn = get_connection()
    cur = conn.cursor()

    request_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO prescription_requests 
        (customer_name, customer_phone, medicine_name, request_date)
        VALUES (?, ?, ?, ?)
    """, (customer_name, customer_phone, medicine_name, request_date))

    conn.commit()
    conn.close()
    return True


# ORDER_ITEMS SERVICES  (multiple_items)

def insert_order_item(order_id, medicine_id, quantity, price, line_total, expiry_date):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO order_items (order_id, medicine_id, quantity, price, line_total, expiry_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (order_id, medicine_id, quantity, price, line_total, expiry_date))
    conn.commit()
    conn.close()
    return True


def get_order_items(order_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    result = cur.fetchall()
    conn.close()
    return result


