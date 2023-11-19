from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Replace these values with your actual database credentials
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DB_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Flask-SQLAlchemy
db = SQLAlchemy(app)

# Define your MenuItems model


class MenuItem(db.Model):
    __tablename__ = 'menu_items'  # Explicitly set the table name
    ID = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    description = db.Column(db.String(255))
    price = db.Column(db.Integer)
    availability = db.Column(db.Boolean)

# Route to get all menu items


@app.route('/menu_items', methods=['GET'])
def get_menu_items():
    menu_items = MenuItem.query.all()
    menu_items_data = [{'id': item.ID, 'name': item.name, 'description': item.description, 'price': item.price, 'availability': item.availability}
                       for item in menu_items]

    return jsonify({'menu_items': menu_items_data})

# Route to add a new menu item


@app.route('/menu_items', methods=['POST'])
def add_menu_item():
    data = request.get_json()
    new_menu_item = MenuItem(name=data['name'], description=data['description'],
                             price=data['price'], availability=data['availability'])
    db.session.add(new_menu_item)
    db.session.commit()
    return jsonify({'message': 'Menu item added successfully'}), 201

# Route to update a menu item


@app.route('/menu_items/<int:item_id>', methods=['PUT'])
def update_menu_item(item_id):
    menu_item = MenuItem.query.get(item_id)
    if menu_item:
        data = request.get_json()
        menu_item.name = data['name']
        menu_item.description = data['description']
        menu_item.price = data['price']
        menu_item.availability = data['availability']
        db.session.commit()
        return jsonify({'message': 'Menu item updated successfully'})
    else:
        return jsonify({'message': 'Menu item not found'}), 404

# Route to delete a menu item


@app.route('/menu_items/<int:item_id>', methods=['DELETE'])
def delete_menu_item(item_id):
    menu_item = MenuItem.query.get(item_id)
    if menu_item:
        db.session.delete(menu_item)
        db.session.commit()
        return jsonify({'message': 'Menu item deleted successfully'})
    else:
        return jsonify({'message': 'Menu item not found'}), 404

# Define your Orders model


class Order(db.Model):
    __tablename__ = 'orders'  # Explicitly set the table name
    order_id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(255))
    status = db.Column(db.String(255))
    total_amount = db.Column(db.Float)

    # Relationship between Order and MenuItem
    items = db.relationship('OrderItem', backref='order', lazy=True)

# Define your OrderItem model


class OrderItem(db.Model):
    __tablename__ = 'orderitem'  # Explicitly set the table name
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey(
        'orders.order_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey(
        'menu_items.ID'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
# Route to get all orders


@app.route('/orders', methods=['GET'])
def get_orders():
    orders = Order.query.all()
    orders_data = []

    for order in orders:
        order_data = {
            'order_id': order.order_id,
            'customer_name': order.customer_name,
            'status': order.status,
            'total_amount': order.total_amount,
            'items': []
        }

        # Iterate through order items and add details
        for order_item in order.items:
            menu_item = MenuItem.query.get(order_item.item_id)
            if menu_item:
                item_data = {
                    'dish_id': order_item.item_id,
                    'dish_name': menu_item.name,
                    'price': menu_item.price,
                    'quantity': order_item.quantity  # Include quantity in the response
                }
                order_data['items'].append(item_data)

        orders_data.append(order_data)

    return jsonify({'orders': orders_data})

# Route to place a new order


@app.route('/orders', methods=['POST'])
def place_order():
    data = request.get_json()
    customer_name = data.get("customer_name")
    order_items = data.get("items", [])

    valid_order_items = []
    total_amount = 0.0  # Initialize total amount

    new_order = Order(customer_name=customer_name,
                      status='received', total_amount=0.0)
    db.session.add(new_order)
    db.session.commit()

    for item_id in order_items:
        # Ensure that the item_id is an integer and exists in the menu_items table
        if isinstance(item_id, int):
            menu_item = MenuItem.query.get(item_id)

            if menu_item and menu_item.availability:
                valid_order_items.append({
                    "dish_id": item_id,
                    "name": menu_item.name,
                    "price": menu_item.price
                })

                # Add order item to the database
                order_item = OrderItem(
                    order_id=new_order.order_id, item_id=item_id, quantity=1)
                db.session.add(order_item)

                total_amount += menu_item.price

    new_order.total_amount = total_amount
    db.session.commit()

    if valid_order_items:
        return jsonify({"message": f"Order with ID {new_order.order_id} has been received. Total amount: ${total_amount:.2f}"}), 201
    else:
        return jsonify({"message": "Invalid order items or item availability."}), 400

# Route to update an order


@app.route('/orders/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    order = Order.query.get(order_id)
    if order:
        data = request.get_json()
        order.status = data.get('status', order.status)
        db.session.commit()
        return jsonify({'message': f'Order with ID {order_id} updated successfully'}), 200
    else:
        return jsonify({'message': f'Order with ID {order_id} not found'}), 404



# Route to review orders


@app.route('/orders/review', methods=['GET'])
def review_orders():
    review_options = request.args.get('status', 'all')

    review_filters = {
        'all': lambda order: True,
        'received': lambda order: order.status == "received",
        'preparing': lambda order: order.status == "preparing",
        'ready': lambda order: order.status == "ready",
        'delivered': lambda order: order.status == "delivered"
    }

    selected_orders = [
        order for order in Order.query.all() if review_filters[review_options](order)
    ]

    reviewed_orders = []

    for order in selected_orders:
        reviewed_order = {
            "order_id": order.order_id,
            "customer_name": order.customer_name,
            "status": order.status,
            "total_amount": order.total_amount,
            "items": []
        }

        for order_item in order.items:
            menu_item = MenuItem.query.get(order_item.item_id)
            if menu_item:
                item_data = {
                    "dish_id": order_item.item_id,
                    "dish_name": menu_item.name,
                    "price": menu_item.price,
                    "quantity": order_item.quantity
                }
                reviewed_order["items"].append(item_data)

        reviewed_orders.append(reviewed_order)

    return jsonify({'orders': reviewed_orders})


# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
