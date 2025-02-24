#!/usr/bin/env python3
from models import db, Restaurant, RestaurantPizza, Pizza
from flask_migrate import Migrate
from flask import Flask, request, jsonify, make_response
from flask_restful import Api, Resource
from sqlalchemy.orm import Session
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.environ.get("DB_URI", f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}")

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.json.compact = False

migrate = Migrate(app, db)

db.init_app(app)

api = Api(app)


class RestaurantsResource(Resource):
    def get(self):
        with Session(db.engine) as session:
            restaurants = session.query(Restaurant).all()
            return jsonify([restaurant.to_dict(only=("id", "name", "address")) for restaurant in restaurants])


class RestaurantResource(Resource):
    def get(self, id):
        with Session(db.engine) as session:
            restaurant = session.get(Restaurant, id)
            if restaurant is None:
                return make_response(jsonify({"error": "Restaurant not found"}), 404)
            return jsonify(restaurant.to_dict())

    def delete(self, id):
        with Session(db.engine) as session:
            restaurant = session.get(Restaurant, id)
            if restaurant is None:
                return make_response(jsonify({"error": "Restaurant not found"}), 404)

            try:
                # Delete associated RestaurantPizzas first
                session.query(RestaurantPizza).filter_by(restaurant_id=id).delete()
                session.delete(restaurant)
                session.commit()
                return make_response("", 204)  # Empty response for DELETE success
            except Exception as e:
                session.rollback()  # Rollback in case of failure
                return make_response(jsonify({"error": str(e)}), 500)  # Show actual error in JSON


class PizzasResource(Resource):
    def get(self):
        with Session(db.engine) as session:
            pizzas = session.query(Pizza).all()
            return jsonify([pizza.to_dict(only=("id", "name", "ingredients")) for pizza in pizzas])


class RestaurantPizzasResource(Resource):
    def post(self):
        data = request.get_json()

        # Validate required fields
        price = data.get("price")
        pizza_id = data.get("pizza_id")
        restaurant_id = data.get("restaurant_id")

        if price is None or pizza_id is None or restaurant_id is None:
            return make_response(jsonify({"errors": ["validation errors"]}), 400)

        # Validate price range
        if not (1 <= price <= 30):
            return make_response(jsonify({"errors": ["validation errors"]}), 400)

        with Session(db.engine) as session:
            # Validate Pizza and Restaurant existence
            pizza = session.get(Pizza, pizza_id)
            restaurant = session.get(Restaurant, restaurant_id)

            if not pizza or not restaurant:
                return make_response(jsonify({"errors": ["validation errors"]}), 400)

            try:
                # Create RestaurantPizza record
                restaurant_pizza = RestaurantPizza(price=price, pizza_id=pizza_id, restaurant_id=restaurant_id)
                session.add(restaurant_pizza)
                session.commit()

                return make_response(jsonify(restaurant_pizza.to_dict()), 201)
            except Exception:
                session.rollback()
                return make_response(jsonify({"errors": ["validation errors"]}), 400)


api.add_resource(RestaurantsResource, "/restaurants")
api.add_resource(RestaurantResource, "/restaurants/<int:id>")
api.add_resource(PizzasResource, "/pizzas")
api.add_resource(RestaurantPizzasResource, "/restaurant_pizzas")


@app.route("/")
def index():
    return "<h1>Code challenge</h1>"


if __name__ == "__main__":
    app.run(port=5555, debug=True)