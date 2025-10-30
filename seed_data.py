import random
from pymongo import MongoClient

client = MongoClient("mongodb+srv://admin:admin7466@sh0o0lin-tech.bg7wyfm.mongodb.net/")
db = client["myshop"]
collection = db["products"]

colors = ["red", "blue", "black", "white", "green", "yellow", "pink", "beige", "navy", "orange", "purple"]
materials = ["cotton", "linen", "denim", "silk", "polyester", "wool", "rayon", "chiffon"]
categories = ["shirt", "t-shirt", "dress", "jeans", "kurta", "saree", "shorts", "jacket", "skirt", "blouse", "coat"]
seasons = ["summer", "winter", "spring", "autumn"]
genders = ["men", "women", "unisex"]
brands = ["UrbanWear", "StyleEdge", "CottonVibe", "DenimZone", "SilkHouse", "FashionFiesta", "TrendSetters"]

sizes = ["XS", "S", "M", "L", "XL", "XXL"]
tags = ["casual", "formal", "ethnic", "party", "beach", "workwear", "daily", "sporty", "festive"]

def random_price():
    return random.randint(499, 4999)

def random_title(color, material, category):
    return f"{color.title()} {material.title()} {category.title()}"

def random_desc(color, material, category):
    return f"A stylish {color} {material} {category} perfect for {random.choice(['daily wear', 'weekends', 'office', 'summer outings', 'festive occasions', 'parties', 'sports'])}."

def make_product(i):
    color = random.choice(colors)
    material = random.choice(materials)
    category = random.choice(categories)
    season = random.choice(seasons)
    gender = random.choice(genders)
    brand = random.choice(brands)
    price = random_price()
    return {
        "sku": f"P{i:05d}",
        "title": random_title(color, material, category),
        "description": random_desc(color, material, category),
        "color": color,
        "material": material,
        "season": season,
        "category": category,
        "gender": gender,
        "price": price,
        "sizes": random.sample(sizes, k=random.randint(2, 5)),
        "brand": brand,
        "tags": random.sample(tags, k=random.randint(2, 4)),
        "images": [f"https://example.com/images/{category}_{color}_{i}.jpg"]
    }

# Clear old demo data
collection.delete_many({})
print("Cleared existing demo data...")

# Insert 1000 demo items
demo_products = [make_product(i) for i in range(1, 1001)]
collection.insert_many(demo_products)
print(f"Inserted {len(demo_products)} demo products into 'myshop.products'.")