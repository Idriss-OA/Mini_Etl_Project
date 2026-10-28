import os

import pandas as pd
from sqlalchemy import URL, create_engine


def load_data(customers, products, orders, logger=print):
    """
    Charge les DataFrames nettoyés dans PostgreSQL.
    """

    # Lire les paramètres de connexion
    password = os.getenv("DB_PASSWORD")

    if not password:
        raise ValueError(
            "La variable d'environnement DB_PASSWORD n'est pas définie."
        )

    database_url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("DB_USER", "postgres"),
        password=password,
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "etl_database"),
    )

    engine = create_engine(database_url)

    try:
        # Charger les données dans PostgreSQL
        with engine.begin() as connection:
            customers.to_sql(
                "customers",
                con=connection,
                if_exists="replace",
                index=False,
            )

            products.to_sql(
                "products",
                con=connection,
                if_exists="replace",
                index=False,
            )

            orders.to_sql(
                "orders",
                con=connection,
                if_exists="replace",
                index=False,
            )

        logger("\n--- Chargement terminé ---")
        logger("Table customers : données chargées.")
        logger("Table products : données chargées.")
        logger("Table orders : données chargées.")

    finally:
        engine.dispose()