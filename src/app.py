import json

from db import db
from db import Asset
from flask import Flask, request
from db import Recipe, Category

app = Flask(__name__)
db_filename = "recipes.db"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
with app.app_context():
    db.create_all()

def success_response(data, code=200):
    return json.dumps(data), code

def failure_response(message, code=404):
    return json.dumps({"error": message}), code

# -- IMAGES -------------------------------------------------------------


@app.route("/upload/", methods=["POST"])
def upload():
    """
    Endpoint for uploading an image to AWS given its base64 form,
    then storing/returning the URL of that image
    """
    body = json.loads(request.data)
    image_data = body.get("image_data")
    if image_data is None:
        return failure_response("No Base64 URL")

    # create new Asset object
    asset = Asset(image_data=image_data)
    db.session.add(asset)
    db.session.commit()

    return success_response(asset.serialize(), 201)


# -- RECIPE ROUTES ------------------------------------------------------


@app.route("/api/recipes/")
def get_recipes():
    """
    Endpoint for getting all recipes
    """
    recipes = [recipe.serialize() for recipe in Recipe.query.all()]
    return success_response({"recipes": recipes})


@app.route("/api/recipes/", methods=["POST"])
def create_recipe():
    """
    Endpoint for creating a new recipe
    """
    body = json.loads(request.data)

    if body.get("title") is None or body.get("description") is None or body.get("ingredients") is None \
        or body.get("steps") is None:
        return failure_response("Recipe title or description or ingredients or steps is not provided.", 400)

    new_recipe = Recipe(
        title = body.get("title"),
        description = body.get("description"),
        ingredients = body.get("ingredients"),
        steps = body.get("steps")
    )

    db.session.add(new_recipe)
    db.session.commit()
    return success_response(new_recipe.serialize(), 201)


@app.route("/api/recipes/<int:recipe_id>/")
def get_recipe(recipe_id):
    """
    Endpoint for getting a recipe by id
    """
    recipe = Recipe.query.filter_by(id=recipe_id).first()
    if recipe is None:
        return failure_response("Recipe not found!")
    return success_response(recipe.serialize())


@app.route("/recipes/<int:recipe_id>/", methods=["POST"])
def update_recipe(recipe_id):
    """
    Endpoint for updating a recipe by id
    """
    body = json.loads(request.data)
    recipe = Recipe.query.filter_by(id=recipe_id).first()
    if recipe is None:
        return failure_response("Recipe not found!")
    recipe.title = body.get("title", recipe.title)
    recipe.description = body.get("description", recipe.description)
    recipe.ingredients = body.get("ingredients", recipe.ingredients)
    recipe.steps = body.get("steps", recipe.steps)
    db.session.commit()
    return success_response(recipe.serialize())


@app.route("/api/recipes/<int:recipe_id>/", methods=["DELETE"])
def delete_recipe(recipe_id):
    """
    Endpoint for deleting a recipe by id
    """
    recipe = Recipe.query.filter_by(id=recipe_id).first()
    if recipe is None:
        return failure_response("Recipe not found!")
    db.session.delete(recipe)
    db.session.commit()
    return success_response(recipe.serialize())


# -- CATEGORY ROUTES --------------------------------------------------


@app.route("/api/categories/", methods=["POST"])
def create_category():
    """
    Endpoint for creating a new category
    """
    body = json.loads(request.data)

    if body.get("description") is None:
        return failure_response("Description is not provided.", 400)

    new_category = Category(
        description = body.get("description")
    )

    db.session.add(new_category)
    db.session.commit()
    return success_response(new_category.serialize(), 201)


@app.route("/api/categories/<int:category_id>/")
def get_category(category_id):
    """
    Endpoint for getting a category by id
    """
    category = Category.query.filter_by(id=category_id).first()
    if category is None:
        return failure_response("Category not found!")
    return success_response(category.serialize())


@app.route("/api/categories/<int:recipe_id>/add/", methods=["POST"])
def add_category_to_recipe(recipe_id):
    """
    Endpoint for adding a category to a recipe by id
    """
    recipe = Recipe.query.filter_by(id=recipe_id).first()
    if recipe is None:
        return failure_response("Recipe not found!")
    body = json.loads(request.data)
    category_description = body.get("description")
    category_type = body.get("type")

    category = Category.query.filter_by(description=category_description).first()
    if category is None:
        return failure_response("Category not found!")
    if category_type != "cuisine" and category_type != "meal type" and category_type != "preparation time":
        return failure_response("Category type does not exist.")
    if category_type == "cuisine":
        recipe.cuisine.append(category)
    if category_type == "meal type":
        recipe.meal_type.append(category)
    if category_type == "preparation time":
        recipe.prep_time.append(category)
    category.recipes.append(recipe)
    db.session.commit()
    return success_response(recipe.serialize())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
