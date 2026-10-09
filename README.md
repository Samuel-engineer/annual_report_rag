# SEC submissions ingestion

La Lambda `ingestion_json` accepte les CIK SEC des entreprises dans un
événement JSON :

```json
{
  "enterprises": {
    "Amazon": "1018724",
    "Microsoft": "789019"
  }
}
```

Pour chaque entreprise, elle normalise le CIK sur 10 chiffres, appelle
`https://data.sec.gov/submissions/CIK{cik}.json` et dépose le JSON SEC brut dans
le bucket configuré par `EXCEL_BUCKET_NAME`, sous la clé
`{entreprise}/CIK{cik}.json` (par exemple
`Amazon/CIK0001018724.json`). Les deux formes suivantes sont acceptées :
`{"enterprises": {"Amazon": "1018724"}}` et un objet plat tel que
`{"Amazon": "1018724"}`.

Les noms d'entreprise sont nettoyés avant de les utiliser dans les clés S3.
Le fichier JSON est conservé tel que retourné par la SEC et porte le type de
contenu `application/json`.

Pour respecter les règles d'accès de la SEC, configurez la variable
d'environnement `SEC_USER_AGENT` avant la synthèse CDK avec un identifiant
d'application et une adresse e-mail de contact, par exemple
`annual-report-rag/1.0 (PrenomNom prenom.nom@domaine.com)`. La même valeur est
transmise aux deux Lambdas pour les requêtes SEC ; l'ingestion refuse de
continuer si elle n'inclut pas d'adresse e-mail.

L'invocation EventBridge utilise Amazon comme événement d'exemple. Pour
traiter d'autres entreprises, invoquez `ingestion_json` avec le JSON ci-dessus.

Dans `function/ingestion_json`, `main.py` orchestre le flux, `config.py` valide
la configuration, `utils.py` valide les entreprises et normalise les CIK,
`sec_client.py` interroge l'API SEC, et `storage.py` prépare la clé et écrit
le résultat dans S3.

La notification S3 `ObjectCreated` déclenche `ingestion_doc` pour les objets
`.json` du bucket de métadonnées. `ingestion_doc` valide et filtre les
formulaires 10-K et DEF 14A, reconstruit les URLs SEC, télécharge les documents
avec `SEC_USER_AGENT` et écrit les fichiers sous
`{année}/{CIK sans zéros}/annual_report_{document}` pour les 10-K ou
`{année}/{CIK sans zéros}/proxy_statement_{document}` pour les DEF 14A dans
le bucket `RAW_BUCKET_NAME`. Les requêtes sont espacées d'au moins 0,11 seconde
et la concurrence Lambda est limitée à une instance. Chaque objet brut porte
les métadonnées `form`, `filingDate` et `accessionNumber`.

Dans `function/ingestion_doc`, `main.py` orchestre le traitement, `filings.py`
valide et transforme les tableaux SEC en dépôts individuels, `sec_client.py`
gère les téléchargements, gzip et la limitation de débit, et `storage.py`
centralise la lecture/écriture S3.