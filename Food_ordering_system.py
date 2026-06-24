import mysql.connector
from datetime import datetime
import getpass  # for admin password input (hides input on terminals)

# -------------------------
# CONFIG - change if needed
# -------------------------
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "your_mysql_password"     # change if your MySQL has password
DB_NAME = "food_ordering"
ADMIN_PASSWORD = "Your_admin_password"   # default admin password

# -------------------------
# DATABASE HELPERS
# -------------------------
def connect_server():
    """Connect to MySQL server (without selecting DB)."""
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        autocommit=True
    )

def connect_db():
    """Connect to the specific database (creates DB if missing)."""
    # First connect to server and ensure database exists
    sconn = connect_server()
    scur = sconn.cursor()
    scur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    sconn.close()

    # Now connect to the DB
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

def initialize_database():
    """Create tables if they don't exist and insert sample menu items."""
    db = connect_db()
    cursor = db.cursor()

    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS menu (
        item_id INT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(100),
        price FLOAT,
        type VARCHAR(20),
        category VARCHAR(50)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INT PRIMARY KEY AUTO_INCREMENT,
        customer_name VARCHAR(100),
        address VARCHAR(255),
        total_amount FLOAT,
        order_time DATETIME
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INT PRIMARY KEY AUTO_INCREMENT,
        order_id INT,
        item_id INT,
        quantity INT,
        FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
    )
    """)

    db.commit()

    # Insert some sample menu items only if menu is empty
    cursor.execute("SELECT COUNT(*) FROM menu")
    count = cursor.fetchone()[0]
    if count == 0:
        sample_items = [
            ("Paneer Roll", 80.0, "Veg", "Snacks"),
            ("Chicken Burger", 110.0, "Non-Veg", "Snacks"),
            ("Fries", 60.0, "Veg", "Snacks"),
            ("Veg Pizza", 150.0, "Veg", "Meals"),
            ("Chicken Biryani", 180.0, "Non-Veg", "Meals"),
            ("Cold Drink", 40.0, "Veg", "Drinks")
        ]
        cursor.executemany(
            "INSERT INTO menu (name, price, type, category) VALUES (%s, %s, %s, %s)",
            sample_items
        )
        db.commit()

    cursor.close()
    db.close()

# -------------------------
# UTILITY FUNCTIONS
# -------------------------
def show_menu():
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT item_id, name, price, type, category FROM menu ORDER BY item_id")
    rows = cursor.fetchall()
    if not rows:
        print("\nMenu is empty. Ask admin to add items.\n")
    else:
        print("\n----------- MENU -----------")
        print("ID | Name                | Price   | Type     | Category")
        print("--------------------------------------------------------")
        for r in rows:
            print(f"{r[0]:<3}| {r[1]:<18}| ₹{r[2]:<7.2f}| {r[3]:<8}| {r[4]}")
        print("--------------------------------------------------------\n")
    cursor.close()
    db.close()

def check_delivery_range(address):
    """Return True if the address is inside Lucknow (simple substring check)."""
    if address is None:
        return False
    return "lucknow" in address.lower()

# -------------------------
# ORDER FUNCTIONS
# -------------------------
def place_order():
    show_menu()
    name = input("Enter Customer Name: ").strip()
    if not name:
        print("Name cannot be empty.")
        return

    address = input("Enter Delivery Address (full address): ").strip()
    if not address:
        print("Address cannot be empty.")
        return

    cart = []
    while True:
        try:
            item_input = input("Enter Item ID to add to cart (0 to finish): ").strip()
            if item_input == "":
                print("Please enter a valid item id or 0.")
                continue
            item_id = int(item_input)
        except ValueError:
            print("Invalid input. Enter numeric Item ID.")
            continue

        if item_id == 0:
            break

        try:
            qty_input = input("Enter Quantity: ").strip()
            qty = int(qty_input)
        except ValueError:
            print("Invalid quantity. Enter a number.")
            continue

        if qty <= 0:
            print("Quantity should be at least 1.")
            continue

        # Verify item exists and fetch price
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("SELECT name, price FROM menu WHERE item_id=%s", (item_id,))
        item = cursor.fetchone()
        cursor.close()
        db.close()

        if not item:
            print("Invalid Item ID - item not found.")
            continue

        cart.append((item_id, item[0], float(item[1]), qty))
        print(f"Added to cart: {item[0]} x {qty}")

    if not cart:
        print("Cart is empty. Order canceled.")
        return

    # Calculate subtotal, gst, total
    subtotal = sum(item[2] * item[3] for item in cart)
    gst = round(subtotal * 0.05, 2)   # 5% GST
    total = round(subtotal + gst, 2)

    # Confirm and store in database
    print("\n----------- BILL -----------")
    print(f"Customer: {name}")
    for it in cart:
        print(f"{it[1]} x {it[3]} = ₹{it[2] * it[3]:.2f}")
    print(f"\nSubtotal: ₹{subtotal:.2f}")
    print(f"GST (5%): ₹{gst:.2f}")
    print(f"Total Amount: ₹{total:.2f}")
    print("----------------------------\n")

    confirm = input("Confirm order? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Order cancelled.")
        return

    db = connect_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO orders (customer_name, address, total_amount, order_time) VALUES (%s, %s, %s, %s)",
        (name, address, total, datetime.now())
    )
    db.commit()
    order_id = cursor.lastrowid

    # Insert order items
    for item_id, item_name, price, qty in cart:
        cursor.execute(
            "INSERT INTO order_items (order_id, item_id, quantity) VALUES (%s, %s, %s)",
            (order_id, item_id, qty)
        )

    db.commit()
    cursor.close()
    db.close()

    deliverable_text = "Deliverable (Inside Lucknow)" if check_delivery_range(address) else "NOT Deliverable (Outside Service Range)"
    print(f"\nOrder placed successfully! Order ID: {order_id}")
    print(f"Delivery Status: {deliverable_text}\n")

def view_previous_order():
    try:
        order_id = int(input("Enter Order ID to view: ").strip())
    except ValueError:
        print("Invalid Order ID.")
        return

    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT order_id, customer_name, address, total_amount, order_time FROM orders WHERE order_id=%s", (order_id,))
    order = cursor.fetchone()
    if not order:
        print("No such order found.")
        cursor.close()
        db.close()
        return

    print("\n------ ORDER DETAILS ------")
    print(f"Order ID   : {order[0]}")
    print(f"Customer   : {order[1]}")
    print(f"Address    : {order[2]}")
    print(f"Total Paid : ₹{order[3]:.2f}")
    print(f"Order Time : {order[4]}")

    cursor.execute("""
        SELECT m.name, m.price, oi.quantity
        FROM order_items oi
        JOIN menu m ON oi.item_id = m.item_id
        WHERE oi.order_id=%s
    """, (order_id,))
    items = cursor.fetchall()
    print("\nItems:")
    for it in items:
        print(f"{it[0]} x {it[2]} = ₹{it[1] * it[2]:.2f}")
    print("----------------------------\n")

    cursor.close()
    db.close()

# -------------------------
# ANALYTICS
# -------------------------
def most_ordered_food():
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT m.name, SUM(oi.quantity) AS total_ordered
        FROM order_items oi
        JOIN menu m ON oi.item_id = m.item_id
        GROUP BY oi.item_id
        ORDER BY total_ordered DESC
        LIMIT 5
    """)
    rows = cursor.fetchall()
    if not rows:
        print("\nNo orders yet.\n")
    else:
        print("\nTop Most Ordered Foods:")
        for idx, r in enumerate(rows, start=1):
            print(f"{idx}. {r[0]} - {int(r[1])} orders")
        print()
    cursor.close()
    db.close()

def veg_nonveg_preference():
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT m.type, SUM(oi.quantity) AS total_qty
        FROM order_items oi
        JOIN menu m ON oi.item_id = m.item_id
        GROUP BY m.type
    """)
    rows = cursor.fetchall()
    if not rows:
        print("\nNo order data yet.\n")
    else:
        print("\nVeg/Non-Veg Preference:")
        total = 0
        counts = {}
        for r in rows:
            typ = r[0] if r[0] else "Unknown"
            qty = int(r[1]) if r[1] is not None else 0
            counts[typ] = qty
            total += qty
            print(f"{typ}: {qty} items ordered")

        # Determine preferred
        if counts:
            preferred = max(counts.items(), key=lambda x: x[1])
            print(f"\nMost Preferred: {preferred[0]} ({preferred[1]} items)")
        print()
    cursor.close()
    db.close()

# -------------------------
# ADMIN FUNCTIONS (PASSWORD PROTECTED)
# -------------------------
def admin_login():
    """Ask for password (hidden) and return True if correct."""
    # use getpass for hidden input; fallback to input if not available
    try:
        entered = getpass.getpass("Enter Admin Password: ")
    except Exception:
        entered = input("Enter Admin Password: ")
    return entered == ADMIN_PASSWORD

def admin_add_item():
    name = input("Food Name: ").strip()
    try:
        price = float(input("Price (e.g. 99.50): ").strip())
    except ValueError:
        print("Invalid price.")
        return
    ftype = input("Type (Veg/Non-Veg): ").strip() or "Veg"
    category = input("Category (Snacks/Meals/Drinks/etc): ").strip() or "General"

    db = connect_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO menu (name, price, type, category) VALUES (%s, %s, %s, %s)",
                   (name, price, ftype, category))
    db.commit()
    print("Item added successfully.")
    cursor.close()
    db.close()

def admin_update_price():
    try:
        item_id = int(input("Enter Item ID to update: ").strip())
        new_price = float(input("Enter new price: ").strip())
    except ValueError:
        print("Invalid input.")
        return
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("UPDATE menu SET price=%s WHERE item_id=%s", (new_price, item_id))
    if cursor.rowcount == 0:
        print("No item found with that ID.")
    else:
        db.commit()
        print("Price updated successfully.")
    cursor.close()
    db.close()

def admin_delete_item():
    try:
        item_id = int(input("Enter Item ID to delete: ").strip())
    except ValueError:
        print("Invalid input.")
        return
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM menu WHERE item_id=%s", (item_id,))
    if cursor.rowcount == 0:
        print("No item found with that ID.")
    else:
        db.commit()
        print("Item deleted.")
    cursor.close()
    db.close()

def admin_view_menu():
    show_menu()

def admin_view_all_orders():
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT order_id, customer_name, address, total_amount, order_time FROM orders ORDER BY order_time DESC")
    orders = cursor.fetchall()
    if not orders:
        print("\nNo orders found.\n")
    else:
        print("\n---- ADMIN: ALL ORDERS ----")
        for o in orders:
            order_id, name, address, amount, otime = o
            status = "Deliverable (Inside Lucknow)" if check_delivery_range(address) else "NOT Deliverable (Outside Service Range)"
            print(f"Order ID : {order_id}")
            print(f"Customer : {name}")
            print(f"Address  : {address}")
            print(f"Amount   : ₹{amount:.2f}")
            print(f"Time     : {otime}")
            print(f"Delivery : {status}")
            print("-------------------------------")
    cursor.close()
    db.close()

def admin_panel():
    if not admin_login():
        print("Incorrect password. Returning to main menu.")
        return

    while True:
        print("\n------ ADMIN PANEL ------")
        print("1. Add Food Item")
        print("2. Update Price")
        print("3. Delete Food Item")
        print("4. View Menu")
        print("5. View All Orders & Delivery Status")
        print("6. Back to Main Menu")
        choice = input("Enter choice: ").strip()
        if choice == "1":
            admin_add_item()
        elif choice == "2":
            admin_update_price()
        elif choice == "3":
            admin_delete_item()
        elif choice == "4":
            admin_view_menu()
        elif choice == "5":
            admin_view_all_orders()
        elif choice == "6":
            break
        else:
            print("Invalid choice. Try again.")

# -------------------------
# MAIN PROGRAM
# -------------------------
def main():
    initialize_database()
    print("Welcome to the Online Food Ordering System")
    while True:
        print("\n========== MAIN MENU ==========")
        print("1. View Menu")
        print("2. Place Order")
        print("3. View Previous Order (by Order ID)")
        print("4. Most Ordered Food (Top 5)")
        print("5. Veg/Non-Veg Preference Report")
        print("6. Admin Panel (password protected)")
        print("7. Exit")

        ch = input("Enter choice: ").strip()
        if ch == "1":
            show_menu()
        elif ch == "2":
            place_order()
        elif ch == "3":
            view_previous_order()
        elif ch == "4":
            most_ordered_food()
        elif ch == "5":
            veg_nonveg_preference()
        elif ch == "6":
            admin_panel()
        elif ch == "7":
            print("Thank you for using the system. Goodbye!")
            break
        else:
            print("Invalid input. Enter a number between 1 and 7.")

if __name__ == "__main__":
    main()
