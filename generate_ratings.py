"""
Alpine Analytics — Rating Generator + PostgreSQL Loader
--------------------------------------------------------
This script:
1. Reads resorts.csv and European_Ski_Resorts.csv
2. Generates a simulated rating (1-5) based on resort characteristics
3. Loads all 3 tables into PostgreSQL (alpine_analytics database)

Rating methodology:
- Based on: total slopes, lift capacity, snowparks, nightskiing, snow cannons, price value
- Small random noise added so ratings look realistic, not mechanical
- Documented as simulated data — transparent in README
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# ─────────────────────────────────────────
# 1. LOAD ENVIRONMENT VARIABLES
# ─────────────────────────────────────────
load_dotenv()

DB_USER     = "postgres"
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST     = "localhost"
DB_PORT     = "5432"
DB_NAME     = "alpine_analytics"

if not DB_PASSWORD:
    raise ValueError("DB_PASSWORD not found in .env file. Please check your .env file.")

# ─────────────────────────────────────────
# 2. LOAD CSV FILES
# ─────────────────────────────────────────
print("Loading CSV files...")

resorts  = pd.read_csv("data/resorts.csv", encoding="latin-1")
european = pd.read_csv("data/European_Ski_Resorts.csv", encoding="latin-1")

print(f"  resorts.csv              → {len(resorts)} rows")
print(f"  European_Ski_Resorts.csv → {len(european)} rows")

# ─────────────────────────────────────────
# 3. CLEAN COLUMN NAMES
# ─────────────────────────────────────────
resorts.columns = (
    resorts.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)

european.columns = (
    european.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)

# Drop unnamed index column from european if present
if "unnamed:_0" in european.columns:
    european = european.drop(columns=["unnamed:_0"])

# ─────────────────────────────────────────
# 4. GENERATE SIMULATED RATINGS
# ─────────────────────────────────────────
print("\nGenerating simulated ratings...")

np.random.seed(42)

def generate_rating(row):
    score = 0

    # Total slopes (up to 2 points)
    if row["total_slopes"] >= 200:
        score += 2.0
    elif row["total_slopes"] >= 100:
        score += 1.5
    elif row["total_slopes"] >= 50:
        score += 1.0
    else:
        score += 0.5

    # Lift capacity (up to 1 point)
    if row["lift_capacity"] >= 50000:
        score += 1.0
    elif row["lift_capacity"] >= 20000:
        score += 0.7
    else:
        score += 0.3

    # Snowparks bonus
    if str(row["snowparks"]).strip().lower() == "yes":
        score += 0.3

    # Night skiing bonus
    if str(row["nightskiing"]).strip().lower() == "yes":
        score += 0.2

    # Snow cannons (reliability)
    if row["snow_cannons"] >= 200:
        score += 0.3
    elif row["snow_cannons"] >= 50:
        score += 0.15

    # Value: slopes per euro
    if row["price"] > 0:
        value = row["total_slopes"] / row["price"]
        if value >= 3:
            score += 0.2

    # Random noise ±0.3
    noise = np.random.uniform(-0.3, 0.3)
    score += noise

    # Normalize to 1.0 – 5.0
    rating = 1.0 + (score / 4.0) * 4.0
    rating = round(min(max(rating, 1.0), 5.0), 1)

    return rating

resorts["simulated_rating"] = resorts.apply(generate_rating, axis=1)

ratings = resorts[["id", "resort", "country", "simulated_rating"]].copy()
ratings.columns = ["resort_id", "resort", "country", "rating"]

print(f"  Generated {len(ratings)} ratings")
print(f"  Rating range : {ratings['rating'].min()} – {ratings['rating'].max()}")
print(f"  Average rating: {ratings['rating'].mean():.2f}")

# ─────────────────────────────────────────
# 5. CONNECT TO POSTGRESQL
# ─────────────────────────────────────────
print("\nConnecting to PostgreSQL...")

import psycopg

engine = create_engine(
    "postgresql+psycopg://",
    creator=lambda: psycopg.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
)

with engine.connect() as conn:
    conn.execute(text("SELECT 1"))
print("  Connected successfully!")

# ─────────────────────────────────────────
# 6. LOAD TABLES INTO POSTGRESQL
# ─────────────────────────────────────────
print("\nLoading tables into PostgreSQL...")

resorts.to_sql("raw_resorts", engine, if_exists="replace", index=False)
print(f"  raw_resorts          → {len(resorts)} rows loaded")

european.to_sql("raw_european_resorts", engine, if_exists="replace", index=False)
print(f"  raw_european_resorts → {len(european)} rows loaded")

ratings.to_sql("raw_ratings", engine, if_exists="replace", index=False)
print(f"  raw_ratings          → {len(ratings)} rows loaded")

print("\n✅ All done! Your 3 tables are ready in PostgreSQL.")
print("   Open pgAdmin and check the alpine_analytics database.")
