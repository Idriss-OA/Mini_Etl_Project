import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from main import run_pipeline


class EtlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ETL CSV - Exécution du pipeline")
        self.root.geometry("760x650")
        self.root.minsize(620, 520)
        self.messages = queue.Queue()
        self.analysis_window = None

        self.data_dir = tk.StringVar(
            value=str(Path(__file__).resolve().parent.parent / "data")
        )
        self.db_host = tk.StringVar(value=os.getenv("DB_HOST", "localhost"))
        self.db_port = tk.StringVar(value=os.getenv("DB_PORT", "5432"))
        self.db_name = tk.StringVar(
            value=os.getenv("DB_NAME", "etl_database")
        )
        self.db_user = tk.StringVar(value=os.getenv("DB_USER", "postgres"))
        self.db_password = tk.StringVar(value=os.getenv("DB_PASSWORD", ""))
        self.status = tk.StringVar(value="Prêt à exécuter le pipeline.")

        self._build_ui()
        self.root.after(100, self._process_messages)

    def _build_ui(self):
        container = ttk.Frame(self.root, padding=18)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="Pipeline ETL CSV",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            container,
            text="Extraction, transformation et chargement vers PostgreSQL",
        ).pack(anchor="w", pady=(2, 16))

        settings = ttk.LabelFrame(
            container, text="Configuration", padding=12
        )
        settings.pack(fill="x")
        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="Dossier des fichiers CSV").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=5
        )
        ttk.Entry(settings, textvariable=self.data_dir).grid(
            row=0, column=1, sticky="ew", pady=5
        )
        ttk.Button(settings, text="Parcourir...", command=self._browse).grid(
            row=0, column=2, padx=(8, 0), pady=5
        )

        fields = (
            ("Hôte PostgreSQL", self.db_host, None),
            ("Port", self.db_port, None),
            ("Base de données", self.db_name, None),
            ("Utilisateur", self.db_user, None),
            ("Mot de passe", self.db_password, "*"),
        )
        for row, (label, variable, mask) in enumerate(fields, start=1):
            ttk.Label(settings, text=label).grid(
                row=row, column=0, sticky="w", padx=(0, 10), pady=5
            )
            ttk.Entry(settings, textvariable=variable, show=mask or "").grid(
                row=row, column=1, columnspan=2, sticky="ew", pady=5
            )

        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=12)
        self.run_button = ttk.Button(
            actions,
            text="Lancer le pipeline",
            command=self._start_pipeline,
        )
        self.run_button.pack(side="left")
        ttk.Label(actions, textvariable=self.status).pack(
            side="left", padx=12
        )

        output = ttk.LabelFrame(container, text="Journal d'exécution", padding=8)
        output.pack(fill="both", expand=True)
        self.log = tk.Text(
            output,
            wrap="word",
            state="disabled",
            font=("Consolas", 10),
            height=14,
        )
        scrollbar = ttk.Scrollbar(
            output, orient="vertical", command=self.log.yview
        )
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _browse(self):
        selected = filedialog.askdirectory(
            title="Choisir le dossier contenant les fichiers CSV",
            initialdir=self.data_dir.get() or str(Path.cwd()),
        )
        if selected:
            self.data_dir.set(selected)

    def _start_pipeline(self):
        data_dir = Path(self.data_dir.get()).expanduser()
        if not data_dir.is_dir():
            self.status.set("Le dossier CSV est introuvable.")
            self._append_log(f"Erreur : dossier introuvable : {data_dir}")
            return

        try:
            port = int(self.db_port.get())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            self.status.set("Port PostgreSQL invalide.")
            self._append_log("Erreur : le port doit être compris entre 1 et 65535.")
            return

        if not self.db_password.get():
            self.status.set("Mot de passe PostgreSQL requis.")
            self._append_log(
                "Erreur : renseignez le mot de passe PostgreSQL."
            )
            return

        database_settings = {
            "DB_HOST": self.db_host.get().strip(),
            "DB_PORT": str(port),
            "DB_NAME": self.db_name.get().strip(),
            "DB_USER": self.db_user.get().strip(),
            "DB_PASSWORD": self.db_password.get(),
        }
        if not all(
            database_settings[key]
            for key in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")
        ):
            self.status.set("Configuration PostgreSQL incomplète.")
            self._append_log(
                "Erreur : renseignez l'hôte, la base, l'utilisateur "
                "et le mot de passe."
            )
            return

        self._append_log("\n--- Nouvelle exécution ---")
        self.status.set("Pipeline en cours...")
        self.run_button.configure(state="disabled")
        threading.Thread(
            target=self._run_pipeline,
            args=(data_dir, database_settings),
            daemon=True,
        ).start()

    def _run_pipeline(self, data_dir, database_settings):
        previous_values = {
            key: os.environ.get(key) for key in database_settings
        }
        try:
            os.environ.update(database_settings)
            analysis = run_pipeline(data_dir=data_dir, logger=self._queue_log)
        except Exception as error:
            self.messages.put(("error", str(error)))
        else:
            self.messages.put(("success", analysis))
        finally:
            for key, value in previous_values.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def _queue_log(self, message):
        self.messages.put(("log", str(message)))

    def _process_messages(self):
        try:
            while True:
                kind, message = self.messages.get_nowait()
                if kind == "log":
                    self._append_log(message)
                elif kind == "error":
                    self._append_log(f"\nÉCHEC : {message}")
                    self.status.set("Échec du pipeline.")
                    self.run_button.configure(state="normal")
                elif kind == "success":
                    self.status.set("Pipeline terminé avec succès.")
                    self.run_button.configure(state="normal")
                    self._show_analysis(message)
        except queue.Empty:
            pass
        self.root.after(100, self._process_messages)

    def _append_log(self, message):
        self.log.configure(state="normal")
        self.log.insert("end", f"{message}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _show_analysis(self, analysis):
        if self.analysis_window is not None and self.analysis_window.winfo_exists():
            self.analysis_window.destroy()

        window = tk.Toplevel(self.root)
        self.analysis_window = window
        window.title("Analyse des données ETL")
        window.geometry("1120x820")
        window.minsize(860, 680)

        container = ttk.Frame(window, padding=16)
        container.pack(fill="both", expand=True)
        ttk.Label(
            container,
            text="Analyse des données",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            container,
            text="Qualité des données et résultats calculés après nettoyage.",
        ).pack(anchor="w", pady=(2, 12))
        ttk.Button(
            container,
            text="Afficher les lignes rejetées ou modifiées",
            command=lambda: self._show_row_audit(analysis["row_audit"]),
        ).pack(anchor="w", pady=(0, 12))

        cards = ttk.Frame(container)
        cards.pack(fill="x", pady=(0, 12))
        metrics = (
            ("Chiffre d'affaires calculé", f"{analysis['revenue']:,.2f}"),
            ("Commandes conservées", str(analysis["order_count"])),
            ("Clients conservés", str(analysis["customer_count"])),
            ("Produits conservés", str(analysis["product_count"])),
        )
        for label, value in metrics:
            card = ttk.LabelFrame(cards, text=label, padding=10)
            card.pack(side="left", fill="both", expand=True, padx=(0, 8))
            ttk.Label(
                card, text=value, font=("Segoe UI", 14, "bold")
            ).pack(anchor="w")
        ttk.Label(
            container,
            text="Le chiffre d'affaires est la somme quantité × prix unitaire ; "
            "l'unité monétaire est celle des prix du CSV.",
        ).pack(anchor="w", pady=(0, 12))

        charts = ttk.Frame(container)
        charts.pack(fill="both", expand=True)
        quality_chart, quality_canvas = self._chart_panel(
            charts,
            "Qualité des données — erreurs par colonne (% des lignes sources)",
            height=240,
        )
        quality_chart.grid(
            row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 12)
        )
        customer_chart, customer_canvas = self._chart_panel(
            charts,
            "Client ayant le plus de commandes",
            height=240,
        )
        product_chart, product_canvas = self._chart_panel(
            charts,
            "Produits les plus commandés (unités)",
            height=240,
        )
        customer_chart.grid(
            row=1, column=0, sticky="nsew", padx=(0, 6), pady=(0, 8)
        )
        product_chart.grid(
            row=1, column=1, sticky="nsew", padx=(6, 0), pady=(0, 8)
        )
        charts.columnconfigure(0, weight=1, uniform="chart")
        charts.columnconfigure(1, weight=1, uniform="chart")
        charts.rowconfigure(0, weight=1)
        charts.rowconfigure(1, weight=1)

        quality_labels = []
        for table in analysis["quality"]:
            for column in table["columns"]:
                if column["count"]:
                    quality_labels.append(
                        (
                            f"{table['table']} · {column['name']}",
                            column["percent"],
                            f"{column['count']} erreur(s) "
                            f"({column['percent']:.1f} %)",
                        )
                    )
        self._draw_bars(quality_canvas, quality_labels, "#E76F51")
        self._draw_bars(
            customer_canvas,
            [
                (
                    str(item["name"]),
                    item["order_count"],
                    f"{item['order_count']} commande(s)",
                )
                for item in analysis["top_customers"]
            ],
            "#2A9D8F",
        )
        self._draw_bars(
            product_canvas,
            [
                (
                    str(item["product_name"]),
                    item["units"],
                    f"{item['units']} unité(s)",
                )
                for item in analysis["top_products"]
            ],
            "#457B9D",
        )

        quality_frame = ttk.LabelFrame(
            container,
            text="Synthèse qualité par table",
            padding=8,
        )
        quality_frame.pack(fill="x", pady=(12, 0))
        tree = ttk.Treeview(
            quality_frame,
            columns=("table", "source", "kept", "rejected", "percent", "issues"),
            show="headings",
            height=3,
        )
        headings = (
            ("table", "Table", 130),
            ("source", "Lignes source", 110),
            ("kept", "Conservées", 100),
            ("rejected", "Rejetées", 100),
            ("percent", "Rejetées (%)", 110),
            ("issues", "Erreurs par colonne", 150),
        )
        for column, heading, width in headings:
            tree.heading(column, text=heading)
            tree.column(column, width=width, anchor="center")
        for table in analysis["quality"]:
            tree.insert(
                "",
                "end",
                values=(
                    table["table"],
                    table["source_rows"],
                    table["clean_rows"],
                    table["rejected_rows"],
                    f"{table['rejected_percent']:.1f} %",
                    table["issue_count"],
                ),
            )
        tree.pack(fill="x")
        worst_table = max(
            analysis["quality"],
            key=lambda table: table["issue_count"],
            default=None,
        )
        if worst_table:
            ttk.Label(
                quality_frame,
                text=(
                    f"Table avec le plus d'erreurs : {worst_table['table']} "
                    f"({worst_table['issue_count']} valeur(s) en erreur)."
                ),
            ).pack(anchor="w", pady=(6, 0))

    def _show_row_audit(self, audit):
        window = tk.Toplevel(self.analysis_window)
        window.title("Détail des lignes rejetées ou modifiées")
        window.geometry("1180x680")
        window.minsize(850, 500)

        container = ttk.Frame(window, padding=14)
        container.pack(fill="both", expand=True)
        ttk.Label(
            container,
            text=(
                "Comparaison des valeurs du CSV source avec le résultat du "
                "nettoyage. Une ligne apparaît pour chaque colonne concernée."
            ),
            wraplength=1100,
        ).pack(anchor="w", pady=(0, 10))

        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True)
        columns = (
            ("source_line", "Ligne CSV", 85),
            ("status", "Résultat", 100),
            ("column", "Colonne", 130),
            ("before", "Valeur avant", 220),
            ("after", "Valeur après", 220),
            ("reason", "Détail", 280),
        )
        for table in audit:
            page = ttk.Frame(notebook, padding=8)
            notebook.add(page, text=table["table"])
            if not table["rows"]:
                ttk.Label(
                    page,
                    text="Aucune ligne rejetée ou modifiée.",
                ).pack(anchor="w", pady=12)
                continue

            frame = ttk.Frame(page)
            frame.pack(fill="both", expand=True)
            tree = ttk.Treeview(
                frame,
                columns=tuple(column[0] for column in columns),
                show="headings",
            )
            for identifier, heading, width in columns:
                tree.heading(identifier, text=heading)
                tree.column(identifier, width=width, minwidth=70, anchor="w")
            vertical = ttk.Scrollbar(
                frame, orient="vertical", command=tree.yview
            )
            horizontal = ttk.Scrollbar(
                frame, orient="horizontal", command=tree.xview
            )
            tree.configure(
                yscrollcommand=vertical.set,
                xscrollcommand=horizontal.set,
            )
            tree.grid(row=0, column=0, sticky="nsew")
            vertical.grid(row=0, column=1, sticky="ns")
            horizontal.grid(row=1, column=0, sticky="ew")
            frame.rowconfigure(0, weight=1)
            frame.columnconfigure(0, weight=1)
            for row in table["rows"]:
                tree.insert(
                    "",
                    "end",
                    values=tuple(row[column[0]] for column in columns),
                )
            ttk.Label(
                page,
                text=f"{len(table['rows'])} changement(s) ou erreur(s) détaillé(s).",
            ).pack(anchor="w", pady=(8, 0))

    def _chart_panel(self, parent, title, height=260):
        panel = ttk.LabelFrame(parent, text=title, padding=8)
        canvas = tk.Canvas(
            panel,
            background="#F8FAFC",
            highlightthickness=0,
            height=height,
        )
        canvas.pack(fill="both", expand=True, padx=4, pady=4)
        return panel, canvas

    @staticmethod
    def _draw_bars(canvas, bars, color):
        canvas.delete("all")
        canvas.update_idletasks()
        width = max(canvas.winfo_width(), 320)
        height = max(canvas.winfo_height(), 220)
        left, right = 145, width - 135
        value_x = width - 12
        max_value = max((item[1] for item in bars), default=0)
        max_value = max_value or 1

        if not bars:
            canvas.create_text(
                width / 2,
                height / 2,
                text="Aucune donnée à afficher",
                fill="#526579",
                font=("Segoe UI", 10),
            )
            return

        row_height = min(36, (height - 32) / len(bars))
        bar_height = min(18, row_height * 0.58)
        chart_width = right - left
        for tick in range(5):
            x = left + chart_width * tick / 4
            canvas.create_line(
                x,
                8,
                x,
                height - 20,
                fill="#DCE5ED",
                dash=(2, 3),
            )
            canvas.create_text(
                x,
                height - 10,
                text=f"{max_value * tick / 4:.0f}",
                fill="#687D90",
                font=("Segoe UI", 8),
            )
        for index, (label, value, detail) in enumerate(bars):
            y = 12 + index * row_height
            center_y = y + row_height / 2
            canvas.create_text(
                left - 8,
                center_y,
                text=label[:24],
                anchor="e",
                fill="#24415A",
                font=("Segoe UI", 9),
            )
            canvas.create_rectangle(
                left,
                y,
                right,
                y + bar_height,
                fill="#E5ECF2",
                outline="",
            )
            bar_width = (right - left) * value / max_value
            if value > 0:
                canvas.create_rectangle(
                    left,
                    y,
                    left + bar_width,
                    y + bar_height,
                    fill=color,
                    outline="",
                )
            canvas.create_text(
                value_x,
                center_y,
                text=detail,
                anchor="e",
                fill="#24415A",
                font=("Segoe UI", 9, "bold"),
            )


def main():
    root = tk.Tk()
    EtlApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
