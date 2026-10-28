import pandas as pd


def transform_data(customers, products, orders, logger=print):
    """
    Nettoie et transforme les données des trois fichiers CSV.
    Retourne les trois DataFrames nettoyés.
    """

    # 1. Nettoyer les clients
    customers = customers.copy()

    customers["name"] = customers["name"].astype("string").str.strip()
    customers["email"] = (
        customers["email"].astype("string").str.strip().str.lower()
    )
    customers["city"] = customers["city"].astype("string").str.strip()

    customers["customer_id"] = pd.to_numeric(
        customers["customer_id"], errors="coerce"
    )

    customers = customers.dropna(
        subset=["customer_id", "name", "email", "city"]
    )

    customers = customers.drop_duplicates(subset=["customer_id"])
    customers["customer_id"] = customers["customer_id"].astype("int64")

    # 2. Nettoyer les produits
    products = products.copy()

    products["product_name"] = (
        products["product_name"].astype("string").str.strip()
    )
    products["category"] = (
        products["category"].astype("string").str.strip()
    )

    products["product_id"] = pd.to_numeric(
        products["product_id"], errors="coerce"
    )
    products["price"] = pd.to_numeric(
        products["price"], errors="coerce"
    )

    products = products.dropna(
        subset=["product_id", "product_name", "category", "price"]
    )

    products = products.drop_duplicates(subset=["product_id"])

    products = products[
        (products["price"] >= 0)
        & (products["product_name"] != "")
        & (products["category"] != "")
    ]

    products["product_id"] = products["product_id"].astype("int64")

    # 3. Nettoyer les commandes
    orders = orders.copy()

    for column in ["order_id", "customer_id", "product_id", "quantity"]:
        orders[column] = pd.to_numeric(
            orders[column], errors="coerce"
        )

    orders["order_date"] = pd.to_datetime(
        orders["order_date"], errors="coerce"
    )

    orders = orders.dropna(
        subset=[
            "order_id",
            "customer_id",
            "product_id",
            "quantity",
            "order_date",
        ]
    )

    orders = orders.drop_duplicates(subset=["order_id"])

    orders = orders[
        (orders["quantity"] > 0)
        & (orders["quantity"] % 1 == 0)
    ]

    # Ne conserver que les commandes associées à des
    # clients et des produits existants.
    orders = orders[
        orders["customer_id"].isin(customers["customer_id"])
        & orders["product_id"].isin(products["product_id"])
    ].copy()

    for column in ["order_id", "customer_id", "product_id", "quantity"]:
        orders[column] = orders[column].astype("int64")

    # 4. Afficher un résumé
    logger("\n--- Transformation terminée ---")
    logger(f"Clients conservés : {len(customers)}")
    logger(f"Produits conservés : {len(products)}")
    logger(f"Commandes conservées : {len(orders)}")

    return customers, products, orders