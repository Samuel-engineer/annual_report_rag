# SEC filings ingestion

La Lambda `ingestion_excel` accepte un événement JSON associant chaque nom
d'entreprise à son CIK SEC :

```json
{
  "companies": {
    "Amazon": "1018724",
    "Microsoft": "789019"
  }
}
```

Elle télécharge les exports 10-K et DEF 14A depuis la page SEC de chaque CIK
et les archive dans le bucket Excel. Une notification S3 déclenche ensuite la
Lambda `ingestion_doc`, qui lit chaque classeur, télécharge chaque URL de la
colonne `Filings URL`, puis dépose les documents dans le bucket raw sous la
forme `{année Reporting Date}/{entreprise}/{nom du fichier}`.

Le CIK est normalisé sur 10 chiffres. Le nom d'entreprise utilisé dans les clés
S3 est nettoyé pour supprimer les caractères incompatibles avec un chemin.
La période de recherche de date de dépôt commence par défaut au `2020-01-01` ;
elle peut être modifiée avec la variable d'environnement `FILING_DATE_FROM`.

Pour respecter les règles d'accès de la SEC, configurez `SEC_USER_AGENT` avec
un identifiant d'application et une adresse de contact. La valeur peut être
fournie dans l'environnement lors de la synthèse CDK.

L'invocation EventBridge existante utilise Amazon comme événement d'exemple.
Pour traiter d'autres entreprises, invoquez `ingestion_excel` avec le JSON
ci-dessus. L'événement S3 transmet automatiquement chaque export à
`ingestion_doc`.

Dans `function/ingestion_excel`, `main.py` orchestre la Lambda, `retrieve_excel.py`
gère le téléchargement des exports SEC via Playwright et `utils.py` regroupe
les utilitaires de validation du payload, de normalisation du CIK, de création
des URLs SEC et de préparation des clés S3.

Dans `function/ingestion_doc`, `main.py` orchestre le traitement des événements
S3 et l'écriture des documents dans le bucket raw. `excel_utils.py` extrait
les URLs de filings et les années de reporting ; `sec_utils.py` valide et
télécharge les URLs SEC et prépare les noms de fichiers ; `s3_utils.py` valide
les clés d'exports et extrait le bucket et la clé des événements S3.