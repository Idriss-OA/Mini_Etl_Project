# ETL CSV

## Lancer l'interface graphique sous Windows

Depuis le dossier du projet, activez l'environnement Python puis démarrez
l'application :

```powershell
.\.venv\Scripts\Activate.ps1
python .\src\gui.py
```

L'interface permet de choisir le dossier contenant `customers.csv`,
`products.csv` et `orders.csv`, de renseigner la connexion PostgreSQL et de
lancer le pipeline. Le journal affiche les étapes, les volumes traités et les
erreurs éventuelles. Après un chargement réussi, un tableau de bord présente
les erreurs par colonne (nombre et pourcentage des lignes sources), les tables
les plus touchées, le client ayant le plus de commandes, les produits les plus
commandés et le chiffre d'affaires calculé. Le chiffre d'affaires est
calculé avec `quantité × prix unitaire` et reste exprimé dans l'unité des prix
des fichiers CSV, car ceux-ci ne précisent pas de devise. Le mot de passe n'est
pas enregistré.

Depuis l'analyse, le bouton « Afficher les lignes rejetées ou modifiées »
ouvre le détail par fichier CSV. Il indique le numéro de ligne, la colonne
concernée, la valeur avant nettoyage, la valeur conservée après nettoyage ou
le rejet de la ligne, ainsi que la raison. Les valeurs rejetées ne sont pas
réparées automatiquement par le pipeline.

Le fichier `data\orders.csv` comprend des commandes d'exemple supplémentaires
pour montrer des clients avec plusieurs commandes.

PostgreSQL doit être accessible et les dépendances du projet doivent être
installées (`pip install -r requirements.txt`).
Pour une nouvelle installation locale, Python 3.12 ou une version compatible
est nécessaire. Sous Windows, Tkinter est fourni avec l'installation standard
de Python et ne s'installe pas avec pip. PostgreSQL est un serveur externe à
installer et démarrer séparément ; il ne fait pas partie des dépendances Python
de `requirements.txt`.

## Lancer en ligne de commande

Le pipeline reste également exécutable sans interface :

```powershell
python .\src\main.py
```

Dans ce mode, `DB_PASSWORD` doit être défini dans l'environnement. Les autres
paramètres de connexion peuvent aussi être configurés avec `DB_HOST`,
`DB_PORT`, `DB_NAME` et `DB_USER`.

## Publier le projet sur GitHub

Après avoir créé un dépôt GitHub vide, liez-le au dépôt local et publiez la
branche `main` :

```cmd
git remote add origin https://github.com/VOTRE-COMPTE/NOM-DU-DEPOT.git
git push -u origin main
```

Le fichier `.gitignore` exclut l'environnement virtuel, les fichiers de
configuration locale contenant des secrets, les journaux et les rapports
générés. Les CSV d'exemple sont inclus ; vérifiez qu'ils ne contiennent pas de
données réelles avant de rendre un dépôt public.