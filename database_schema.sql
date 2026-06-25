CREATE DATABASE IF NOT EXISTS food_ordering;

USE food_ordering;

CREATE TABLE IF NOT EXISTS menu (
    item_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100),
    price FLOAT,
    type VARCHAR(20),
    category VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_name VARCHAR(100),
    address VARCHAR(255),
    total_amount FLOAT,
    order_time DATETIME
);

CREATE TABLE IF NOT EXISTS order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT,
    item_id INT,
    quantity INT,
    FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE CASCADE
);

INSERT INTO menu (name, price, type, category) VALUES
('Paneer Roll', 80.0, 'Veg', 'Snacks'),
('Chicken Burger', 110.0, 'Non-Veg', 'Snacks'),
('Fries', 60.0, 'Veg', 'Snacks'),
('Veg Pizza', 150.0, 'Veg', 'Meals'),
('Chicken Biryani', 180.0, 'Non-Veg', 'Meals'),
('Cold Drink', 40.0, 'Veg', 'Drinks');