PLACE YOUR BIGQUERY CREDENTIALS HERE
====================================

1. Place your 'bigquery_service_account.json' file in this directory.

2. Alternatively, set the GOOGLE_APPLICATION_CREDENTIALS environment variable
   to point to your credentials file location.

3. The service account must have the following BigQuery permissions:
   - BigQuery Data Viewer
   - BigQuery Job User

4. To obtain credentials:
   a. Go to Google Cloud Console
   b. Navigate to IAM & Admin > Service Accounts
   c. Create or select a service account
   d. Create a JSON key and download it
   e. Place the JSON file here as 'bigquery_service_account.json'
