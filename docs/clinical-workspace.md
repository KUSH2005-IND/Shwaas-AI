# ShwaasAI clinical workspace

This branch adds a working doctor worklist, case review, investigation tracking, private report/OCR attachments, durable review sync and a focused Orthanc/OHIF PACS gateway. It shares the existing `Screening`, `User` and `Referral` database. Cough inference, preprocessing, weights and scoring thresholds are unchanged.

## Start here: run the dashboard before adding PACS

Requires Python 3.12 and Node 24. Use a separate virtual environment so the finalized ML environment stays intact. From the repository root:

```bash
python -m venv .venv-clinical
# Windows PowerShell:
.venv-clinical\Scripts\Activate.ps1
# macOS / Linux instead:
# source .venv-clinical/bin/activate
python -m pip install -r requirements-clinical.txt
npm --prefix clinical ci
npm --prefix clinical run build
```

Optional fictional demo records. This seed is additive; it never deletes existing records or resets passwords. Do not run the older `server.seed`, which deletes records.

```powershell
# PowerShell: choose a password with at least 12 characters.
$env:SHWAAS_DEMO_PASSWORD="replace-with-your-demo-password"
python -m server.clinical_seed
python -m uvicorn server.clinical:app --host 127.0.0.1 --port 8060
```

For Bash use `export SHWAAS_DEMO_PASSWORD='replace-with-your-demo-password'` instead. Open **http://127.0.0.1:8060/doctor/**. Sign in as `doctor_demo` with the password you chose. The worker login is `worker_demo` with the same initially chosen demo password. A second seed run keeps the original passwords.

The clinical app does not import Torch or load the cough model. Demo scores are clearly fictional seeded records, not new inference. Use only synthetic data for the hackathon.

For live UI development, activate the same Python environment and run `npm --prefix clinical run dev`. It starts the clinical API on 8060 and Vite on 5173, with a same-origin API proxy. Open http://localhost:5173/doctor/. Set `CLINICAL_START_API=0` and `CLINICAL_API_URL` when using an already-running backend instead. A checkout-local, ignored `clinical/.env.local` can hold those development settings. Do not include patient data or API keys in Vite environment variables.

## Connect the existing volunteer backend

The updated `server.main:app` installs the clinical routes and serves the built dashboard at `/doctor/`, so running your complete existing backend is the simplest integrated setup:

```bash
# In your existing backend environment, add clinical dependencies; retain its ML dependencies.
python -m pip install -r requirements-clinical.txt
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

Visit http://127.0.0.1:8000/doctor/. The Flutter app keeps its existing API base and multipart `/screenings` contract. It must sign in, include its bearer token, and explicitly send `consent_given=true`. The backend now requires these before saving a screening. Mobile, doctor UI, original documents and imaging metadata share one database; there is no second copy to reconcile. Do not run another backend against a different database and expect its records to appear.

Accounts need `role="doctor"` and the exact same nonempty `phc_center` as their volunteers. Doctors see that facility’s screenings; volunteers see their own submissions. Existing anonymous screenings with no submitting user remain unassigned and do not appear in a doctor worklist. Existing `admin` accounts are not automatically clinical accounts. Provision accounts intentionally using your admin process; the demo seed only provisions the two named demo accounts.

If you run the lightweight doctor service separately, use the same `SHWAAS_DATABASE_URL`, private-file directory and `SHWAAS_JWT_SECRET` as the volunteer service. SQLite is a single-host demonstration setup; do not place its database on a network share or run replicas. Before installing this branch, back up your database and original files. The clinical tables are additive; existing screening columns are retained.

### API compatibility changes

`GET /screenings`, detail, stats and referral updates now require authentication and enforce scope. Referral status changes require a doctor. `/ocr/scan` also requires authentication. The publicly known JWT key was replaced with `SHWAAS_JWT_SECRET` (at least 32 characters), or a generated local `data/.jwt-secret`. Existing tokens must sign in again. Share the configured secret between services, rather than copying secrets into source code. CORS defaults to no cross-origin web clients; native Flutter is unaffected. List specific web origins in `SHWAAS_CORS_ORIGINS` if needed; never combine wildcard origins with credentialed requests.

## Teammate handoff: persist OCR with its source

`/ocr/scan` extracts text but does not persist an attachment. After successfully saving a screening, upload the original to:

```text
POST /clinical/cases/{screening_id}/documents
Authorization: Bearer <worker token>
Content-Type: multipart/form-data

file: original PDF / PNG / JPEG
expected_sha256: optional SHA-256 of the original bytes
fields_json: [{"name":"OCR text","value":"extracted text","page":1}]
```

Prefer separate fields (test name, specimen date, result) with the actual source page. Limits: 20 MB, 20 PDF pages, 100 fields, 2,000 characters per field. Split a long OCR transcription into page/block fields within these limits. PDFs must be unencrypted. No image-to-diagnosis inference is performed here. New fields always start `needs_verification`; corrected transcription is confirmed separately. The doctor can inspect the original, edit extracted fields, and confirm transcription. The report snapshot includes the fields, source hash and verification status.

The receipt contains `document.id`, `document.sha256` and `receipt=received|already_received`. Retrying the same bytes for the same case returns the same document. On a timeout, retry the original bytes until a receipt is received; retain the local original until then. Files are uploaded online; the doctor browser does not queue large attachments.

## Review sync and conflicts

- Browser review edits, investigation requests and investigation status updates enter an IndexedDB outbox before transmission. AES-GCM encrypts the payload with an account-specific nonextractable browser key. This protects persisted plaintext; it is not protection from XSS, an unlocked browser profile, device compromise or clearing browser storage.
- Every event has a UUID `event_id`. The server commits its change and receipt together. Exact replay returns the original receipt. Reusing a key with different content is rejected.
- Review edits and order updates include `expected_version`. A stale version returns 409. The queue keeps the draft; the UI shows server and draft values before an explicit resubmission against a new version. Orders with invalid transitions require the doctor to resolve the underlying state rather than blindly retry.
- Worklist polling runs every eight seconds while signed in. It includes newly received mobile screenings even when those predate clinical audit events. A scoped `/clinical/changes?after=` feed is also available for a future incremental client.
- The UI acknowledges only server receipts. A pending review does not become a completed server review while offline. An expired session can be signed into again without deleting queued work. Signing out is blocked while changes remain unresolved.
- This is **pending-edit resilience**, not full offline access to all records. The worklist is fetched online. The present mobile client's simulated offline screening fallback and missing replay worker are not fixed by this branch. Replace that fallback with an explicit unsynced draft before claiming end-to-end offline screening sync.

## Start the PACS services

Requires Docker Desktop / Docker Engine with Compose and a recent BuildKit. First build downloads and builds OHIF; allow more time than a normal dashboard build.

```bash
python -m server.clinical_setup
docker compose --env-file .env.clinical -f compose.clinical.yml up --build -d
docker compose --env-file .env.clinical -f compose.clinical.yml run --rm clinical python -m server.clinical_seed
```

Open http://127.0.0.1:8060/doctor/. Your generated demo password is `SHWAAS_DEMO_PASSWORD` in `.env.clinical`. Never commit that file. The setup script does not overwrite it. Do not start this container on port 8060 while another API already uses that port.

The Compose file binds the existing repository `data/` directory, so it can use the same local database. On Linux, its configured UID/GID must own that directory and have access to existing files; the setup script records your nonroot UID/GID. If you run setup as root, assign a suitable nonroot owner and UID/GID before starting. Avoid simultaneous SQLite writes from host/container processes on Docker Desktop shared filesystems. Prefer one integrated backend for the demo. If using a host backend with Docker PACS, configure private networking deliberately; the archive is intentionally not published on a host port.

The services are:

| Service | Role | Exposure |
| --- | --- | --- |
| Clinical API | Auth, case scope, files, image gateway and UI | localhost:8060 |
| Orthanc 26.9.1 | Persistent DICOM archive + DICOMweb | Private Docker network only |
| OHIF v3.13.13 | DICOM viewer | Private Docker network, proxied after clinician login |

OHIF is built with `PUBLIC_URL=/clinical/pacs/viewer/`; its asset paths are baked into its build. Configuring `routerBasename` alone is insufficient to relocate a root-path image. Its config is mounted at that same prefix. The API rewrites archive `BulkDataURI` references and restricts each DICOMweb read to an explicitly linked, facility-authorized study. Global QIDO browsing, archive writes, arbitrary upstream URLs and DICOM C-STORE ports are not exposed through the gateway.

### PACS acceptance walkthrough

1. Open a demo case and request a Chest X-ray investigation.
2. On Imaging, verify that the archive reports `connected`.
3. Upload a genuine, deidentified single-frame CR/DX chest X-ray DICOM file. Its PatientID should match the displayed patient code. If different, verify the association manually before using the explicit confirmation checkbox. Do not associate someone else’s scan merely to bypass the check. PDFs, CT, multiframe images and structured reports are outside this focused imaging ingest; use Documents for PDF/image reports.
4. Retry the same file: the instance ID should stay the same. Conflicting bytes for one SOP UID are rejected. A study cannot be assigned to two cases.
5. Open the archive preview, then Open OHIF. Confirm pixels load, window/level works and the correct study is displayed. A PNG preview is not a diagnostic workstation. This branch does not validate display calibration or diagnostic suitability.
6. Mark investigation receipt separately from clinical review. Receipt does not establish study completeness. Review the findings and enter the clinical assessment explicitly.
7. Sign in with another facility’s test account. Both preview and DICOMweb requests for the study must return 404. An unauthenticated request must return 401.

Docker is unavailable in the implementation environment: the container build, actual archive storage and OHIF pixel display still need this live acceptance walkthrough. Gateway tests use an archive stub and valid synthetic DICOM headers; they do not validate pixel decoding. Multi-file ingest retains already acknowledged instances if a later file fails; retrying the batch deduplicates those instances. No DICOM deletion/reconciliation UI or completeness certification is included.

## Reports and clinical responsibility

A `reviewed` status requires nonempty assessment notes and a next action. Each completion creates an immutable snapshot. Later edits create new review versions without rewriting older snapshots. Print/save PDF includes symptom answers, acoustic provenance, OCR fields and verification status, investigations and imaging identifiers. It is a clinician record, not an automated TB diagnosis or signed government notification. The record brief is compiled deterministically from the case, not an LLM agent. Ni-kshay submission is not connected.

## Validation

```bash
python -m pytest tests/test_clinical.py -q
npm --prefix clinical test
npm --prefix clinical run build
```

The clinical test suite covers role/facility restrictions, cookie CSRF checks, exact event replay, changed-content replay rejection, optimistic version conflicts, immutable snapshots, investigation transitions, original-file checksums and validation, OCR verification, scoped change cursors, DICOM identity checks, instance retry deduplication and private preview/DICOMweb access. It also checks that legacy record endpoints cannot bypass the new restrictions. No model retraining or live model performance evaluation is involved.

Implementation checks: 18 clinical API tests plus six legacy auth/read/referral tests passed, four browser-outbox tests passed, and the TypeScript/production build passed. The outbox tests cover encryption, account separation, module reload, simultaneous key creation across tabs and tamper rejection. Six legacy tests that need the full model/audio fixtures or Tesseract were excluded from this lightweight verification; their inference logic was not changed. Legacy integration tests now use an isolated database and explicit worker/doctor authentication and consent.

The sign-in layout was inspected in the browser. An authenticated browser walkthrough of the review and attachment screens remains an acceptance check; automated credential entry was not used. The API tests and browser-storage tests do not replace that walkthrough.

For a patient-facing deployment, complete TLS with secure cookies (`SHWAAS_COOKIE_SECURE=true`), identity and access provisioning, consent/retention procedures, encrypted storage/backup with restoration testing, login throttling, an audited deployment configuration and a clinical review of the workflow. Browser drafts require HTTPS or localhost for WebCrypto. The current schema scopes by an account’s mutable `phc_center`; introduce durable facility memberships and record assignments before staff transfers or multiple-facility deployment. The audit log is append-only through the app, not tamper-proof against database administrators. Worklist statistics cover at most the displayed 500 records; add server pagination/aggregate metrics for larger deployments.
