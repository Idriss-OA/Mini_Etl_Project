import pandas as pd


def _blank(series):
    return series.isna() | series.astype("string").str.strip().eq("").fillna(True)


def _numeric(series):
    return pd.to_numeric(series, errors="coerce")


def _issue_counts(raw_frames, clean_frames):
    specs = {
        "Clients": {
            "customer_id": ("numeric",),
            "name": ("text",),
            "email": ("text",),
            "city": ("text",),
        },
        "Produits": {
            "product_id": ("numeric",),
            "product_name": ("text",),
            "category": ("text",),
            "price": ("price",),
        },
        "Commandes": {
            "order_id": ("numeric",),
            "customer_id": ("numeric",),
            "product_id": ("numeric",),
            "quantity": ("quantity",),
            "order_date": ("date",),
        },
    }
    results = []

    for (table, columns), raw, clean in zip(
        specs.items(), raw_frames, clean_frames
    ):
        errors_by_column = {}
        for column, rules in columns.items():
            values = raw[column]
            issues = _blank(values) if "text" in rules else values.isna()

            if "numeric" in rules or "price" in rules or "quantity" in rules:
                number = _numeric(values)
                issues = issues | number.isna()
                if "price" in rules:
                    issues = issues | (number < 0)
                if "quantity" in rules:
                    issues = issues | (number <= 0) | (number % 1 != 0)
                if column in ("customer_id", "product_id", "order_id"):
                    eligible = number.notna()
                    if table == "Clients":
                        eligible &= ~_blank(raw["name"])
                        eligible &= ~_blank(raw["email"])
                        eligible &= ~_blank(raw["city"])
                    elif table == "Produits":
                        eligible &= ~_blank(raw["product_name"])
                        eligible &= ~_blank(raw["category"])
                        eligible &= _numeric(raw["price"]).notna()
                    elif table == "Commandes":
                        for required in ("customer_id", "product_id", "quantity"):
                            eligible &= _numeric(raw[required]).notna()
                        eligible &= pd.to_datetime(
                            raw["order_date"], errors="coerce"
                        ).notna()
                        eligible &= _numeric(raw["quantity"]).gt(0)
                        eligible &= (
                            _numeric(raw["quantity"]) % 1
                        ).eq(0)
                    issues = issues | (
                        eligible & number.duplicated(keep="first")
                    )

            if "date" in rules:
                issues = issues | pd.to_datetime(
                    values, errors="coerce"
                ).isna()

            if table == "Commandes" and column in (
                "customer_id",
                "product_id",
            ):
                ids = _numeric(values)
                valid_orders = pd.Series(True, index=raw.index)
                for required in (
                    "order_id",
                    "customer_id",
                    "product_id",
                    "quantity",
                ):
                    valid_orders &= _numeric(raw[required]).notna()
                valid_orders &= pd.to_datetime(
                    raw["order_date"], errors="coerce"
                ).notna()
                valid_orders &= _numeric(raw["quantity"]).gt(0)
                valid_orders &= (
                    _numeric(raw["quantity"]) % 1
                ).eq(0)
                valid_orders &= ~_numeric(raw["order_id"]).duplicated(
                    keep="first"
                )
                valid_ids = (
                    clean["customer_id"]
                    if column == "customer_id"
                    else clean["product_id"]
                )
                issues = issues | (
                    valid_orders & ~ids.isin(valid_ids)
                )

            errors_by_column[column] = int(issues.sum())

        total_issues = sum(errors_by_column.values())
        total_rows = len(raw)
        results.append(
            {
                "table": table,
                "source_rows": total_rows,
                "clean_rows": len(clean),
                "rejected_rows": total_rows - len(clean),
                "rejected_percent": (
                    (total_rows - len(clean)) / total_rows * 100
                    if total_rows
                    else 0
                ),
                "issue_count": total_issues,
                "columns": [
                    {
                        "name": column,
                        "count": count,
                        "percent": count / total_rows * 100
                        if total_rows
                        else 0,
                    }
                    for column, count in errors_by_column.items()
                ],
            }
        )

    return results


def _format_value(value):
    if pd.isna(value):
        return "(vide)"
    return str(value)


def _audit_rows(raw_frames, clean_frames):
    tables = ("Clients", "Produits", "Commandes")
    key_columns = {
        "Clients": "customer_id",
        "Produits": "product_id",
        "Commandes": "order_id",
    }
    customer_ids = set(clean_frames[0]["customer_id"])
    product_ids = set(clean_frames[1]["product_id"])
    audit = []

    for table, raw, clean in zip(tables, raw_frames, clean_frames):
        details = []
        clean_indices = set(clean.index)
        seen_keys = set()

        for position, (index, row) in enumerate(raw.iterrows()):
            issues = {}
            for column in raw.columns:
                value = row[column]
                if column in ("name", "email", "city", "product_name", "category"):
                    if pd.isna(value) or not str(value).strip():
                        issues[column] = "Valeur manquante"
                elif column == "order_date":
                    if pd.isna(pd.to_datetime(value, errors="coerce")):
                        issues[column] = "Date invalide ou manquante"
                elif column in ("customer_id", "product_id", "order_id", "price", "quantity"):
                    number = pd.to_numeric(
                        pd.Series([value]), errors="coerce"
                    ).iloc[0]
                    if pd.isna(number):
                        issues[column] = "Valeur numérique invalide ou manquante"
                    elif column == "price" and number < 0:
                        issues[column] = "Le prix doit être positif ou nul"
                    elif column == "quantity" and (
                        number <= 0 or number % 1 != 0
                    ):
                        issues[column] = "La quantité doit être un entier positif"

            key = key_columns[table]
            key_value = pd.to_numeric(
                pd.Series([row[key]]), errors="coerce"
            ).iloc[0]
            if table == "Clients":
                dedup_candidate = not any(
                    pd.isna(row[column])
                    for column in ("name", "email", "city")
                ) and not pd.isna(key_value)
            elif table == "Produits":
                price = pd.to_numeric(
                    pd.Series([row["price"]]), errors="coerce"
                ).iloc[0]
                dedup_candidate = (
                    not pd.isna(key_value)
                    and not pd.isna(price)
                    and not pd.isna(row["product_name"])
                    and not pd.isna(row["category"])
                )
            else:
                dedup_candidate = (
                    all(
                        not pd.isna(
                            pd.to_numeric(
                                pd.Series([row[column]]), errors="coerce"
                            ).iloc[0]
                        )
                        for column in (
                            "order_id",
                            "customer_id",
                            "product_id",
                            "quantity",
                        )
                    )
                    and not pd.isna(
                        pd.to_datetime(row["order_date"], errors="coerce")
                    )
                )
            if dedup_candidate:
                if key_value in seen_keys:
                    issues[key] = "Identifiant dupliqué"
                else:
                    seen_keys.add(key_value)

            if table == "Commandes" and not issues:
                customer_id = pd.to_numeric(
                    pd.Series([row["customer_id"]]), errors="coerce"
                ).iloc[0]
                product_id = pd.to_numeric(
                    pd.Series([row["product_id"]]), errors="coerce"
                ).iloc[0]
                if customer_id not in customer_ids:
                    issues["customer_id"] = "Client inexistant"
                if product_id not in product_ids:
                    issues["product_id"] = "Produit inexistant"

            if index not in clean_indices:
                for column, reason in issues.items():
                    details.append(
                        {
                            "source_line": int(position + 2),
                            "status": "Rejetée",
                            "column": column,
                            "before": _format_value(row[column]),
                            "after": "Ligne rejetée",
                            "reason": reason,
                        }
                    )
                if not issues:
                    details.append(
                        {
                            "source_line": int(position + 2),
                            "status": "Rejetée",
                            "column": "—",
                            "before": "—",
                            "after": "Ligne rejetée",
                            "reason": "Écart détecté pendant le nettoyage",
                        }
                    )
                continue

            cleaned_row = clean.loc[index]
            for column in raw.columns:
                before = row[column]
                after = cleaned_row[column]
                if pd.isna(before) and pd.isna(after):
                    continue
                if str(before) != str(after):
                    details.append(
                        {
                            "source_line": int(position + 2),
                            "status": "Modifiée",
                            "column": column,
                            "before": _format_value(before),
                            "after": _format_value(after),
                            "reason": "Valeur normalisée ou convertie",
                        }
                    )

        audit.append({"table": table, "rows": details})

    return audit


def build_analysis(raw_frames, clean_frames):
    """Construit les indicateurs qualité et ventes des données ETL."""
    raw_customers, raw_products, raw_orders = raw_frames
    customers, products, orders = clean_frames
    quality = _issue_counts(raw_frames, clean_frames)

    enriched_orders = orders.merge(
        products[["product_id", "product_name", "price"]],
        on="product_id",
        how="left",
        validate="many_to_one",
    ).merge(
        customers[["customer_id", "name"]],
        on="customer_id",
        how="left",
        validate="many_to_one",
    )
    enriched_orders["revenue"] = (
        enriched_orders["quantity"] * enriched_orders["price"]
    )

    customer_totals = (
        enriched_orders.groupby(["customer_id", "name"], as_index=False)
        .agg(
            order_count=("order_id", "count"),
            units=("quantity", "sum"),
            revenue=("revenue", "sum"),
        )
        .sort_values(
            ["order_count", "units", "revenue", "customer_id"],
            ascending=[False, False, False, True],
        )
        .head(1)
    )
    product_totals = (
        enriched_orders.groupby(
            ["product_id", "product_name"], as_index=False
        )
        .agg(
            order_count=("order_id", "count"),
            units=("quantity", "sum"),
            revenue=("revenue", "sum"),
        )
        .sort_values(
            ["units", "order_count", "revenue", "product_id"],
            ascending=[False, False, False, True],
        )
        .head(5)
    )

    return {
        "quality": quality,
        "row_audit": _audit_rows(raw_frames, clean_frames),
        "customer_count": len(customers),
        "product_count": len(products),
        "order_count": len(orders),
        "revenue": float(enriched_orders["revenue"].sum()),
        "top_customers": customer_totals.to_dict("records"),
        "top_products": product_totals.to_dict("records"),
        "quality_issue_count": sum(item["issue_count"] for item in quality),
        "source_row_count": sum(
            len(frame) for frame in (raw_customers, raw_products, raw_orders)
        ),
    }
