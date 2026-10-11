# Tests Report — annual_report_rag

## Summary

12 new files were created (11 test files + 1 `__init__.py`).  
The test suite grew from **27** tests to **90** tests, all passing in ~1.3 s with no real AWS calls.  
No tests were skipped.

---

## Test Files Created

### 1. `tests/unit/ingestion_doc/test_config.py`

**Module covered:** `function/ingestion_doc/config.py` — `Settings.from_env()`

| Test | Type |
|---|---|
| `test_from_env_returns_settings_with_all_env_vars` | Nominal |
| `test_from_env_uses_default_user_agent` | Nominal (default) |
| `test_from_env_raises_when_excel_bucket_missing` | Error — missing env var |
| `test_from_env_raises_when_excel_bucket_empty` | Error — empty string |
| `test_from_env_raises_when_raw_bucket_missing` | Error — missing env var |
| `test_from_env_raises_when_raw_bucket_empty` | Error — empty string |
| `test_from_env_raises_when_user_agent_missing_email` | Error — no `@` in value |

---

### 2. `tests/unit/ingestion_doc/test_storage.py`

**Module covered:** `function/ingestion_doc/storage.py` — `load_submissions`, `upload_filing`, `filing_is_current`

| Test | Type |
|---|---|
| `test_load_submissions_returns_parsed_dict` | Nominal |
| `test_load_submissions_raises_if_body_is_json_array` | Error — array body |
| `test_load_submissions_raises_if_body_is_invalid_json` | Error — invalid JSON |
| `test_upload_filing_puts_document_and_metadata` | Nominal — two `put_object` calls verified |
| `test_upload_filing_metadata_empty_reporting_date` | Edge — `None` reporting date → `""` |
| `test_filing_is_current_returns_false_when_document_missing` | Error — 404 on document key |
| `test_filing_is_current_returns_false_when_metadata_missing` | Error — 404 on metadata key |
| `test_filing_is_current_returns_false_when_metadata_url_differs` | Error — URL mismatch |
| `test_filing_is_current_returns_true_when_url_matches` | Nominal |
| `test_filing_is_current_returns_false_when_metadata_is_invalid_json` | Error — corrupt metadata |
| `test_filing_is_current_reraises_unexpected_client_error` | Error — non-404 ClientError re-raised |

---

### 3. `tests/unit/ingestion_doc/test_storage_client_error.py`

**Module covered:** `function/ingestion_doc/storage.py` — ClientError re-raise paths

| Test | Type |
|---|---|
| `test_filing_is_current_reraises_non_404_head_object_error` | Error — `AccessDenied` on `head_object` |
| `test_filing_is_current_reraises_non_404_get_object_error` | Error — `AccessDenied` on `get_object` |

---

### 4. `tests/unit/ingestion_doc/test_filings_extended.py`

**Module covered:** `function/ingestion_doc/filings.py` — `extract_filings`, `Filing.s3_key`

| Test | Type |
|---|---|
| `test_extract_filings_rejects_non_dict_payload` | Error — non-dict input |
| `test_extract_filings_rejects_invalid_cik_zero` | Error — all-zero CIK |
| `test_extract_filings_rejects_non_digit_cik` | Error — non-digit CIK |
| `test_extract_filings_rejects_missing_filings_recent` | Error — missing `filings` key |
| `test_extract_filings_rejects_missing_form_list` | Error — missing `form` key |
| `test_extract_filings_rejects_invalid_filing_date_format` | Error — bad date string |
| `test_extract_filings_rejects_invalid_report_date_format` | Error — bad report date string |
| `test_extract_filings_rejects_non_string_report_date` | Error — integer report date |
| `test_extract_filings_rejects_invalid_primary_document_with_slash` | Error — slash in filename |
| `test_extract_filings_accepts_empty_report_date` | Edge — `""` → `None` |
| `test_extract_filings_mismatched_report_date_array_length` | Error — array length mismatch |
| `test_filing_s3_key_raises_on_empty_primary_document_after_sanitise` | Error — document sanitises to `""` |

---

### 5. `tests/unit/ingestion_doc/test_handler_extended.py`

**Module covered:** `function/ingestion_doc/main.py` — `lambda_handler`, `_submission_location`

| Test | Type |
|---|---|
| `test_handler_rejects_empty_submissions_list` | Error — empty list |
| `test_handler_rejects_non_list_submissions` | Error — non-list value |
| `test_submission_location_rejects_non_dict` | Error — non-dict submission |
| `test_submission_location_rejects_missing_enterprise` | Error — missing key |
| `test_submission_location_rejects_empty_enterprise` | Error — empty string |
| `test_submission_location_rejects_missing_bucket` | Error — missing key |
| `test_submission_location_rejects_missing_key` | Error — missing key |
| `test_handler_raises_when_bucket_does_not_match_config` | Error — bucket mismatch |

---

### 6. `tests/unit/ingestion_doc/test_sec_client_extended.py`

**Module covered:** `function/ingestion_doc/sec_client.py` — redirect check, plain body, URL validation

| Test | Type |
|---|---|
| `test_download_filing_raises_on_redirect_to_non_sec_url` | Error — redirect to non-SEC URL |
| `test_download_filing_returns_plain_body_when_no_gzip` | Nominal — no gzip |
| `test_download_filing_rejects_url_not_starting_with_https_sec_gov` | Error — HTTP URL rejected before call |

---

### 7. `tests/unit/ingestion_json/test_config.py`

**Module covered:** `function/ingestion_json/config.py` — `Settings.from_env()`

| Test | Type |
|---|---|
| `test_from_env_returns_settings_with_all_env_vars` | Nominal |
| `test_from_env_uses_default_user_agent` | Nominal (default) |
| `test_from_env_raises_when_bucket_missing` | Error — absent env var |
| `test_from_env_raises_when_bucket_empty` | Error — empty string |
| `test_from_env_raises_when_user_agent_has_no_email` | Error — no `@` |

---

### 8. `tests/unit/ingestion_json/test_storage.py`

**Module covered:** `function/ingestion_json/storage.py` — `submissions_s3_key`, `upload_submissions`

| Test | Type |
|---|---|
| `test_submissions_s3_key_builds_correct_path` | Nominal |
| `test_submissions_s3_key_builds_path_for_arbitrary_enterprise` | Nominal |
| `test_upload_submissions_calls_put_object_with_correct_args` | Nominal — args & ContentType verified |

---

### 9. `tests/unit/ingestion_json/test_sec_client_extended.py`

**Module covered:** `function/ingestion_json/sec_client.py` — gzip branch

| Test | Type |
|---|---|
| `test_fetch_submissions_decompresses_gzip_response` | Nominal — gzip decompression |
| `test_fetch_submissions_rejects_invalid_cik` | Error — bad CIK, no HTTP call made |

---

### 10. `tests/unit/ingestion_json/test_utils_extended.py`

**Module covered:** `function/ingestion_json/utils.py` — empty-name guard, integer CIK, s3 key stripping

| Test | Type |
|---|---|
| `test_get_enterprises_rejects_empty_enterprise_name` | Error — empty name key |
| `test_normalise_cik_accepts_integer_input` | Nominal — integer → padded string |
| `test_normalise_cik_rejects_non_digit_string` | Error — non-digit string |
| `test_enterprise_s3_key_strips_leading_and_trailing_symbols` | Edge — leading/trailing `._-` removed |

---

### 11. `tests/unit/knowledge_base_sync/test_handler_extended.py`

**Module covered:** `function/knowledge_base_sync/main.py` — missing branches

| Test | Type |
|---|---|
| `test_handler_start_without_execution_id_omits_client_token` | Nominal — no `executionId` |
| `test_handler_start_raises_on_empty_execution_id` | Error — `""` executionId |
| `test_handler_start_raises_when_bedrock_returns_no_job_id` | Error — empty Bedrock response |
| `test_handler_status_raises_when_job_id_missing` | Error — no `jobId` key |
| `test_handler_status_raises_when_bedrock_returns_no_status` | Error — empty Bedrock response |
| `test_handler_client_token_is_sha256_of_execution_id` | Nominal — token derivation verified |

---

### 12. `tests/unit/knowledge_base_sync/__init__.py`

Empty package marker (was missing).

---

## Mocking strategy used

All external dependencies are replaced with plain fake classes (no `MagicMock`, no `moto`),
matching the existing codebase style:

| Dependency | Approach |
|---|---|
| `boto3` S3 client | Inline fake class injected via `monkeypatch.setattr(main, "s3_client", ...)` |
| `boto3` Bedrock client | Inline fake class injected via `monkeypatch.setattr(main, "bedrock_client", ...)` |
| `urllib.request.urlopen` | `monkeypatch.setattr(sec_client, "urlopen", ...)` with `FakeResponse` context manager |
| Environment variables | `monkeypatch.setenv` / `monkeypatch.delenv` exclusively |
| `get_settings()` | `monkeypatch.setattr(main, "get_settings", lambda: Settings(...))` |

---

## Final pytest run output (verbatim)

```
====================================================== test session starts ======================================================
platform win32 -- Python 3.13.9, pytest-9.0.2, pluggy-1.6.0 -- C:\Python313\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\tanto\work\annual_report_rag
configfile: pyproject.toml
plugins: anyio-4.9.0, langsmith-0.4.9, cov-7.1.0
collecting ... collecting 26 items                                                                                                              collected 90 items

tests/unit/ingestion_doc/test_config.py::test_from_env_returns_settings_with_all_env_vars PASSED                           [  1%]
tests/unit/ingestion_doc/test_config.py::test_from_env_uses_default_user_agent PASSED                                      [  2%]
tests/unit/ingestion_doc/test_config.py::test_from_env_raises_when_excel_bucket_missing PASSED                             [  3%]
tests/unit/ingestion_doc/test_config.py::test_from_env_raises_when_excel_bucket_empty PASSED                               [  4%]
tests/unit/ingestion_doc/test_config.py::test_from_env_raises_when_raw_bucket_missing PASSED                               [  5%]
tests/unit/ingestion_doc/test_config.py::test_from_env_raises_when_raw_bucket_empty PASSED                                 [  6%]
tests/unit/ingestion_doc/test_config.py::test_from_env_raises_when_user_agent_missing_email PASSED                         [  7%]
tests/unit/ingestion_doc/test_filings.py::test_extract_filings_filters_forms_and_reconstructs_archive_urls PASSED          [  8%]
tests/unit/ingestion_doc/test_filings.py::test_extract_filings_rejects_mismatched_arrays PASSED                            [ 10%]
tests/unit/ingestion_doc/test_filings.py::test_extract_filings_rejects_invalid_selected_filing PASSED                      [ 11%]
tests/unit/ingestion_doc/test_filings.py::test_extract_filings_rejects_missing_root_cik PASSED                             [ 12%]
tests/unit/ingestion_doc/test_filings_extended.py::test_extract_filings_rejects_non_dict_payload PASSED                    [ 13%]
tests/unit/ingestion_doc/test_filings_extended.py::test_extract_filings_rejects_invalid_cik_zero PASSED                    [ 14%]
tests/unit/ingestion_doc/test_filings_extended.py::test_extract_filings_rejects_non_digit_cik PASSED                       [ 15%]
tests/unit/ingestion_doc/test_filings_extended.py::test_extract_filings_rejects_missing_filings_recent PASSED              [ 16%]
tests/unit/ingestion_doc/test_filings_extended.py::test_extract_filings_rejects_missing_form_list PASSED                   [ 17%]
tests/unit/ingestion_doc/test_filings_extended.py::test_extract_filings_rejects_invalid_filing_date_format PASSED          [ 18%]
tests/unit/ingestion_doc/test_filings_extended.py::test_extract_filings_rejects_invalid_report_date_format PASSED          [ 20%]
tests/unit/ingestion_doc/test_filings_extended.py::test_extract_filings_rejects_non_string_report_date PASSED              [ 21%]
tests/unit/ingestion_doc/test_filings_extended.py::test_extract_filings_rejects_invalid_primary_document_with_slash PASSED [ 22%]
tests/unit/ingestion_doc/test_filings_extended.py::test_extract_filings_accepts_empty_report_date PASSED                   [ 23%]
tests/unit/ingestion_doc/test_filings_extended.py::test_extract_filings_mismatched_report_date_array_length PASSED         [ 24%]
tests/unit/ingestion_doc/test_filings_extended.py::test_filing_s3_key_raises_on_empty_primary_document_after_sanitise PASSED [ 25%]
tests/unit/ingestion_doc/test_handler.py::test_handler_downloads_only_supported_filings_and_uploads_metadata_files PASSED  [ 26%]
tests/unit/ingestion_doc/test_handler.py::test_handler_rejects_missing_submission_references PASSED                        [ 27%]
tests/unit/ingestion_doc/test_handler.py::test_handler_skips_filings_with_matching_metadata PASSED                         [ 28%]
tests/unit/ingestion_doc/test_handler_extended.py::test_handler_rejects_empty_submissions_list PASSED                      [ 30%]
tests/unit/ingestion_doc/test_handler_extended.py::test_handler_rejects_non_list_submissions PASSED                        [ 31%]
tests/unit/ingestion_doc/test_handler_extended.py::test_submission_location_rejects_non_dict PASSED                        [ 32%]
tests/unit/ingestion_doc/test_handler_extended.py::test_submission_location_rejects_missing_enterprise PASSED              [ 33%]
tests/unit/ingestion_doc/test_handler_extended.py::test_submission_location_rejects_empty_enterprise PASSED                [ 34%]
tests/unit/ingestion_doc/test_handler_extended.py::test_submission_location_rejects_missing_bucket PASSED                  [ 35%]
tests/unit/ingestion_doc/test_handler_extended.py::test_submission_location_rejects_missing_key PASSED                     [ 36%]
tests/unit/ingestion_doc/test_handler_extended.py::test_handler_raises_when_bucket_does_not_match_config PASSED            [ 37%]
tests/unit/ingestion_doc/test_sec_client.py::test_download_filing_sets_user_agent_and_decompresses_gzip PASSED             [ 38%]
tests/unit/ingestion_doc/test_sec_client.py::test_download_filing_rejects_non_archive_url PASSED                           [ 40%]
tests/unit/ingestion_doc/test_sec_client.py::test_rate_limiter_keeps_requests_at_or_below_ten_per_second PASSED            [ 41%]
tests/unit/ingestion_doc/test_sec_client_extended.py::test_download_filing_raises_on_redirect_to_non_sec_url PASSED        [ 42%]
tests/unit/ingestion_doc/test_sec_client_extended.py::test_download_filing_returns_plain_body_when_no_gzip PASSED          [ 43%]
tests/unit/ingestion_doc/test_sec_client_extended.py::test_download_filing_rejects_url_not_starting_with_https_sec_gov PASSED [ 44%]
tests/unit/ingestion_doc/test_storage.py::test_load_submissions_returns_parsed_dict PASSED                                 [ 45%]
tests/unit/ingestion_doc/test_storage.py::test_load_submissions_raises_if_body_is_json_array PASSED                        [ 46%]
tests/unit/ingestion_doc/test_storage.py::test_load_submissions_raises_if_body_is_invalid_json PASSED                      [ 47%]
tests/unit/ingestion_doc/test_storage.py::test_upload_filing_puts_document_and_metadata PASSED                             [ 48%]
tests/unit/ingestion_doc/test_storage.py::test_upload_filing_metadata_empty_reporting_date PASSED                          [ 50%]
tests/unit/ingestion_doc/test_storage.py::test_filing_is_current_returns_false_when_document_missing PASSED                [ 51%]
tests/unit/ingestion_doc/test_storage.py::test_filing_is_current_returns_false_when_metadata_missing PASSED                [ 52%]
tests/unit/ingestion_doc/test_storage.py::test_filing_is_current_returns_false_when_metadata_url_differs PASSED            [ 53%]
tests/unit/ingestion_doc/test_storage.py::test_filing_is_current_returns_true_when_url_matches PASSED                      [ 54%]
tests/unit/ingestion_doc/test_storage.py::test_filing_is_current_returns_false_when_metadata_is_invalid_json PASSED        [ 55%]
tests/unit/ingestion_doc/test_storage.py::test_filing_is_current_reraises_unexpected_client_error PASSED                   [ 56%]
tests/unit/ingestion_doc/test_storage_client_error.py::test_filing_is_current_reraises_non_404_head_object_error PASSED    [ 57%]
tests/unit/ingestion_doc/test_storage_client_error.py::test_filing_is_current_reraises_non_404_get_object_error PASSED     [ 58%]
tests/unit/ingestion_json/test_config.py::test_from_env_returns_settings_with_all_env_vars PASSED                          [ 60%]
tests/unit/ingestion_json/test_config.py::test_from_env_uses_default_user_agent PASSED                                     [ 61%]
tests/unit/ingestion_json/test_config.py::test_from_env_raises_when_bucket_missing PASSED                                  [ 62%]
tests/unit/ingestion_json/test_config.py::test_from_env_raises_when_bucket_empty PASSED                                    [ 63%]
tests/unit/ingestion_json/test_config.py::test_from_env_raises_when_user_agent_has_no_email PASSED                         [ 64%]
tests/unit/ingestion_json/test_handler.py::test_handler_fetches_and_uploads_each_enterprise_submissions_document PASSED    [ 65%]
tests/unit/ingestion_json/test_handler.py::test_handler_requires_bucket_configuration PASSED                               [ 66%]
tests/unit/ingestion_json/test_handler.py::test_handler_rejects_invalid_event_before_fetch PASSED                          [ 67%]
tests/unit/ingestion_json/test_sec_client.py::test_fetch_submissions_uses_padded_cik_and_contact_user_agent PASSED         [ 68%]
tests/unit/ingestion_json/test_sec_client.py::test_fetch_submissions_rejects_invalid_json_payload[not-json] PASSED         [ 70%]
tests/unit/ingestion_json/test_sec_client.py::test_fetch_submissions_rejects_invalid_json_payload[[]] PASSED               [ 71%]
tests/unit/ingestion_json/test_sec_client_extended.py::test_fetch_submissions_decompresses_gzip_response PASSED            [ 72%]
tests/unit/ingestion_json/test_sec_client_extended.py::test_fetch_submissions_rejects_invalid_cik PASSED                   [ 73%]
tests/unit/ingestion_json/test_storage.py::test_submissions_s3_key_builds_correct_path PASSED                              [ 74%]
tests/unit/ingestion_json/test_storage.py::test_submissions_s3_key_builds_path_for_arbitrary_enterprise PASSED             [ 75%]
tests/unit/ingestion_json/test_storage.py::test_upload_submissions_calls_put_object_with_correct_args PASSED               [ 76%]
tests/unit/ingestion_json/test_utils.py::test_get_enterprises_normalises_ciks[event0] PASSED                               [ 77%]
tests/unit/ingestion_json/test_utils.py::test_get_enterprises_normalises_ciks[event1] PASSED                               [ 78%]
tests/unit/ingestion_json/test_utils.py::test_get_enterprises_rejects_invalid_cik PASSED                                   [ 79%]
tests/unit/ingestion_json/test_utils.py::test_get_enterprises_rejects_non_object_event PASSED                              [ 80%]
tests/unit/ingestion_json/test_utils.py::test_normalise_cik_rejects_zero_and_overlong_values[0] PASSED                     [ 81%]
tests/unit/ingestion_json/test_utils.py::test_normalise_cik_rejects_zero_and_overlong_values[12345678901] PASSED           [ 82%]
tests/unit/ingestion_json/test_utils.py::test_enterprise_s3_key_normalises_name PASSED                                     [ 83%]
tests/unit/ingestion_json/test_utils.py::test_enterprise_s3_key_rejects_name_without_usable_characters PASSED              [ 84%]
tests/unit/ingestion_json/test_utils_extended.py::test_get_enterprises_rejects_empty_enterprise_name PASSED                [ 86%]
tests/unit/ingestion_json/test_utils_extended.py::test_normalise_cik_accepts_integer_input PASSED                          [ 87%]
tests/unit/ingestion_json/test_utils_extended.py::test_normalise_cik_rejects_non_digit_string PASSED                       [ 88%]
tests/unit/ingestion_json/test_utils_extended.py::test_enterprise_s3_key_strips_leading_and_trailing_symbols PASSED        [ 90%]
tests/unit/knowledge_base_sync/test_handler.py::test_handler_starts_ingestion_job_with_execution_token PASSED              [ 91%]
tests/unit/knowledge_base_sync/test_handler.py::test_handler_returns_ingestion_job_status PASSED                           [ 92%]
tests/unit/knowledge_base_sync/test_handler.py::test_handler_rejects_unknown_operation PASSED                              [ 93%]
tests/unit/knowledge_base_sync/test_handler_extended.py::test_handler_start_without_execution_id_omits_client_token PASSED [ 94%]
tests/unit/knowledge_base_sync/test_handler_extended.py::test_handler_start_raises_on_empty_execution_id PASSED            [ 95%]
tests/unit/knowledge_base_sync/test_handler_extended.py::test_handler_start_raises_when_bedrock_returns_no_job_id PASSED   [ 96%]
tests/unit/knowledge_base_sync/test_handler_extended.py::test_handler_status_raises_when_job_id_missing PASSED             [ 97%]
tests/unit/knowledge_base_sync/test_handler_extended.py::test_handler_status_raises_when_bedrock_returns_no_status PASSED  [ 98%]
tests/unit/knowledge_base_sync/test_handler_extended.py::test_handler_client_token_is_sha256_of_execution_id PASSED        [100%]
====================================================== 90 passed in 1.26s =======================================================
```

---

## Skipped tests

None. All 90 tests pass without real AWS credentials or internet access.
