from flask_sqlalchemy import SQLAlchemy
import base64
import boto3
import datetime
import io
from io import BytesIO
from mimetypes import guess_extension, guess_type
import os
from PIL import Image
import random
import re
import string

db = SQLAlchemy()

EXTENSIONS = ["png","gif","jpg","jpeg"]
BASE_DIR = os.getcwd()
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
S3_BASE_URL = f"https://{S3_BUCKET_NAME}.s3.us-east-1.amazonaws.com"

class Asset(db.Model):
    """
    Asset model
    """
    __tablename__ = "assets"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    base_url = db.Column(db.String, nullable=True)
    salt = db.Column(db.String, nullable=True)
    extension = db.Column(db.String, nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)

    def __init__(self, **kwargs):
        """
        Initializes an Asset object
        """
        self.create(kwargs.get("image_data"))

    def serialize(self):
        """
        Serializes an Asset object
        """
        return {
            "url": f"{self.base_url}/{self.salt}.{self.extension}",
            "created_at": str(self.created_at)
        }

    def create(self, image_data):
        """
        Given an image in base64 form, does the following:
            1. Rejects the image if it's not supported filetype
            2. Generates a random string for the image filename
            3. Decodes the image and attempts to upload it to AWS
        """
        try:
            ext = guess_extension(guess_type(image_data)[0])[1:]

            # only accept supported file extension
            if ext not in EXTENSIONS:
                raise Exception(f"Extension {ext} not supported")

            # securely generate a random string for image name
            salt = "".join(
                random.SystemRandom().choice(
                    string.ascii_uppercase + string.digits
                )
                for _ in range(16)
            )

            # remove base64 header
            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_data = base64.b64decode(img_str)
            img = Image.open(BytesIO(img_data))

            self.base_url = S3_BASE_URL
            self.salt = salt
            self.extension = ext
            self.width = img.width
            self.height = img.height
            self.created_at = datetime.datetime.now()

            img_filename = f"{self.salt}.{self.extension}"
            self.upload(img, img_filename)

        except Exception as e:
            print(f"Error while creating image: {e}")

    def upload(self, img, img_filename):
        """
        Attempt to upload the image into S3 bucket
        """

        try:
            # save image temporarily on the server
            img_temploc = f"{BASE_DIR}/{img_filename}"
            img.save(img_temploc)

            # upload the image to S3
            s3_client = boto3.client("s3")
            s3_client.upload_file(img_temploc, S3_BUCKET_NAME, img_filename)

            # make s3 image url public
            s3_resource = boto3.resource("s3")
            object_acl = s3_resource.ObjectAcl(S3_BUCKET_NAME, img_filename)
            object_acl.put(ACL="public-read")

            # remove image from server
            os.remove(img_temploc)

        except Exception as e:
            print(f"Error while uploading image: {e}")


cuisine_recipe = db.Table(
    "cuisine_recipe",
    db.Column("recipe_id", db.Integer, db.ForeignKey("recipe.id")),
    db.Column("category_id", db.Integer, db.ForeignKey("category.id"))
)

meal_type_recipe = db.Table(
    "meal_type_recipe",
    db.Column("recipe_id", db.Integer, db.ForeignKey("recipe.id")),
    db.Column("category_id", db.Integer, db.ForeignKey("category.id"))
)

prep_time_recipe = db.Table(
    "prep_time_recipe",
    db.Column("recipe_id", db.Integer, db.ForeignKey("recipe.id")),
    db.Column("category_id", db.Integer, db.ForeignKey("category.id"))
)

categories_recipe = db.Table(
    "categories_recipe",
    db.Column("recipe_id", db.Integer, db.ForeignKey("recipe.id")),
    db.Column("category_id", db.Integer, db.ForeignKey("category.id"))
)

class Recipe(db.Model):
    """
    Recipe model
    """

    __tablename__ = "recipe"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    ingredients = db.Column(db.String, nullable=False)
    steps = db.Column(db.String, nullable=False)
    cuisine = db.relationship("Category", secondary=cuisine_recipe, back_populates="recipes")
    meal_type = db.relationship("Category", secondary=meal_type_recipe, back_populates="recipes")
    prep_time = db.relationship("Category", secondary=prep_time_recipe, back_populates="recipes")


    def __init__(self, **kwargs):
        """
        Initializes a Recipe object
        """

        self.title = kwargs.get("title", "")
        self.description = kwargs.get("description", "")
        self.ingredients = kwargs.get("ingredients", "")
        self.steps = kwargs.get("steps", "")
        
    def serialize(self):
        """
        Serializes a Recipe object
        """

        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "ingredients": self.ingredients,
            "steps": self.steps,
            "cuisine": [i.simple_serialize() for i in self.cuisine],
            "meal_type": [i.simple_serialize() for i in self.meal_type],
            "prep_time": [s.simple_serialize() for s in self.prep_time]
        }

    def simple_serialize(self):
        """
        Serialize a Recipe object without cuisine, meal type, or prep time fields
        """

        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "ingredients": self.ingredients,
            "steps": self.steps
        }


class Category(db.Model):
    """
    Category model
    """

    __tablename__ = "category"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    description = db.Column(db.String, nullable=False)
    recipes = db.relationship("Recipe", secondary=categories_recipe)

    def __init__(self, **kwargs):
        """
        Initializes a Category object
        """
        self.description = kwargs.get("description", "")

    def serialize(self):
        """
        Serializes a Category object
        """

        return {
            "id": self.id,
            "description": self.description,
            "recipes": [c.simple_serialize() for c in self.recipes]
        }

    def simple_serialize(self):
        """
        Serialize a Category object without the recipes field
        """

        return {
            "id": self.id,
            "description": self.description
        }