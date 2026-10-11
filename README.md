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

Le workflow Step Functions reçoit `mode` et, pour les modes `full` et
`documents_sync`, une liste d'entreprises à traiter. Pour démarrer le flux
complet manuellement :

```json
{
  "mode": "full",
  "enterprises": {
    "Amazon": "1018724"
  }
}
```

Dans `function/ingestion_json`, `main.py` orchestre le flux, `config.py` valide
la configuration, `utils.py` valide les entreprises et normalise les CIK,
`sec_client.py` interroge l'API SEC, et `storage.py` prépare la clé et écrit
le résultat dans S3.

`OrchestrationStack` définit un Step Functions Standard Workflow avec trois
modes :

- `full` : A (`ingestion_json`) → B (`ingestion_doc`) → C (synchronisation Bedrock).
- `documents_sync` : B → C. L'entrée contient des références aux objets de
  soumissions dans `excel_bucket`, sous la forme
  `{"submissions":[{"enterprise":"Amazon","bucket":"excel-bucket","key":"Amazon/CIK0001018724.json"}]}`.
- `sync_only` : C uniquement.

Le Scheduler lance `full` chaque 6 janvier à minuit dans le fuseau
`Europe/Paris`, actuellement avec Amazon comme entreprise configurée.
Step Functions transmet à B les références écrites par A ;
B lit les JSON directement dans `excel_bucket`. Il n'y a pas de notification
S3 qui déclenche B, afin d'éviter une exécution en double.

Pour lancer uniquement une synchronisation manuelle, l'entrée est
`{"mode":"sync_only"}`. Le résultat d'A fournit la liste `submissions`
nécessaire à un lancement `documents_sync`.

B valide et filtre les formulaires 10-K et DEF 14A, reconstruit les URLs SEC,
télécharge les documents avec `SEC_USER_AGENT` et les écrit dans
`RAW_BUCKET_NAME`, sous `{année}/{CIK sans zéros}/`. Les clés incluent
l'accession SEC pour distinguer les dépôts qui utilisent le même nom de
document. Chaque document a un fichier compagnon `{document}.metadata.json`
dans le même dossier. Il contient les attributs `enterprise`, `filingDate`,
`reportingDate` et `filingUrl` sous `metadataAttributes`; les dates sont au
format `JJ/MM/AAAA`. Si la SEC ne fournit pas de date de reporting, sa valeur
est une chaîne vide.

B est idempotente : si le document et son compagnon existent déjà et que le
`filingUrl` correspond, le dépôt est ignoré. Si l'un des deux fichiers manque
ou si l'URL ne correspond pas, B retélécharge le document puis écrit le
document et son JSON compagnon. Les requêtes SEC sont espacées d'au moins
0,11 seconde et la concurrence Lambda est limitée à une instance.

C démarre un job d'ingestion Bedrock ; le workflow vérifie son statut toutes
les 60 secondes et ne réussit qu'une fois le statut `COMPLETE` reçu.

Dans `function/ingestion_doc`, `main.py` orchestre le traitement, `filings.py`
valide et transforme les tableaux SEC en dépôts individuels, `sec_client.py`
gère les téléchargements, gzip et la limitation de débit, et `storage.py`
centralise la lecture/écriture S3.