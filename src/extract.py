from pathlib import Path
import pandas as pd

# Chemin vers le dossier racine du projet
BASE_DIR = Path(__file__).resolve().parent.parent

# Chemin vers le dossier contenant les fichiers CSV
DATA_DIR = BASE_DIR / "data"


def extract_data(data_dir=None, logger=print):
    """
    Lit les trois fichiers CSV et retourne les données sous forme
    de DataFrames Pandas.
    """
    source_dir = Path(data_dir) if data_dir is not None else DATA_DIR

    customers = pd.read_csv(source_dir / "customers.csv")
    products = pd.read_csv(source_dir / "products.csv")
    orders = pd.read_csv(source_dir / "orders.csv")

    logger("Extraction terminée !")
    logger(f"Nombre de clients : {len(customers)}")
    logger(f"Nombre de produits : {len(products)}")
    logger(f"Nombre de commandes : {len(orders)}")

    return customers, products, orders


if __name__ == "__main__":
    extract_data()