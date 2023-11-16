import mysql.connector
from mysql.connector.errors import OperationalError


# Function to connect to the MySQL database
def connect_to_mysql():
    try:
        cnx = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root',
            database='puppy_love_cafe'
        )
        return cnx
    except OperationalError as e:
        print(f"Error: {e}")
        return None


# Function to execute a query and return the result
def execute_query(cnx, query, params=None):
    try:
        cursor = cnx.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        cursor.close()
        return result
    except OperationalError as e:
        print(f"Error: {e}")
        return None


# Function to get order status
def get_order_status(order_id):
    cnx = connect_to_mysql()
    if cnx:
        query = "SELECT status FROM order_tracking WHERE order_id = %s"
        result = execute_query(cnx, query, (order_id,))
        cnx.close()

        if result is not None:
            return result[0]
    return None


# Function to return the next order ID
def return_next_order_id():
    cnx = connect_to_mysql()
    if cnx:
        query = "SELECT MAX(order_id) FROM orders"
        result = execute_query(cnx, query)
        cnx.close()

        if result is not None:
            return result[0] + 1
    return 1


# Function to insert an order item
def insert_order_item(food_item, quantity, order_id):
    cnx = connect_to_mysql()
    if cnx:
        try:
            cursor = cnx.cursor()
            cursor.callproc("insert_order_item", (food_item, quantity, order_id))
            print("inserted ", food_item)
            cnx.commit()
            cursor.close()
            return 1
        except BaseException as e:
            print(f"Error: {e}")
            cnx.rollback()
            return 0
        finally:
            cnx.close()
    return None


# Function to get the total order price
def get_total_order_price(order_id):
    cnx = connect_to_mysql()
    if cnx:
        query = f"SELECT get_total_order_price({order_id})"
        result = execute_query(cnx, query)
        cnx.close()

        if result is not None:
            return result[0]
    return None


# Function to insert order tracking
def insert_order_tracking(next_order_id, status):
    cnx = connect_to_mysql()
    if cnx:
        try:
            cursor = cnx.cursor()
            insert_query = "INSERT INTO order_tracking (order_id, status) VALUES (%s, %s)"
            cursor.execute(insert_query, (next_order_id, status))
            cnx.commit()
            cursor.close()
        except OperationalError as e:
            print(f"Error: {e}")
            return None
        finally:
            cnx.close()


def save_to_db(order: dict):
    next_order_id = return_next_order_id()
    for food_item, quantity in order.items():
        db_fine = insert_order_item(food_item, quantity, next_order_id)
        if not db_fine:
            return 0
    insert_order_tracking(next_order_id, "in progress")

    return next_order_id
