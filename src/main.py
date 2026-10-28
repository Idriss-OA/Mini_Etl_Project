from extract import extract_data
from transform import transform_data
from load import load_data
from analytics import build_analysis


def run_pipeline(data_dir=None, logger=print):
    logger("=" * 50)
    logger("DÉMARRAGE DU PIPELINE ETL")
    logger("=" * 50)

    # ÉTAPE 1 : EXTRACTION
    logger("\n[1/3] Extraction des données...")

    raw_frames = extract_data(data_dir, logger)
    customers, products, orders = raw_frames

    # ÉTAPE 2 : TRANSFORMATION
    logger("\n[2/3] Transformation des données...")

    customers, products, orders = transform_data(
        customers,
        products,
        orders,
        logger,
    )
    analysis = build_analysis(
        raw_frames,
        (customers, products, orders),
    )

    # ÉTAPE 3 : CHARGEMENT
    logger("\n[3/3] Chargement dans PostgreSQL...")

    load_data(customers, products, orders, logger)

    logger("\n" + "=" * 50)
    logger("PIPELINE ETL TERMINÉ AVEC SUCCÈS")
    logger("=" * 50)
    return analysis


def main():
    run_pipeline()


if __name__ == "__main__":
    main()