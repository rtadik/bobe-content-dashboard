# GitHub Actions Setup

One-time configuration required to enable the GitHub Actions pipeline and admin panel.

---

## 1. GitHub Secrets

Go to: **https://github.com/rtadik/bobe-content-dashboard/settings/secrets/actions**

Click **New repository secret** and add each of the following (values from your `.env` file):

| Secret Name        | Value source          | Purpose                             |
|--------------------|-----------------------|-------------------------------------|
| `APIFY_API_TOKEN`  | `.env` → same name    | Twitter/Reddit scraping             |
| `GOOGLE_AI_API_KEY`| `.env` → same name    | Gemini content generation + RU translation |
| `WAVESPEED_API_KEY`| `.env` → same name    | EN images (GPT-Image-1.5) + RU images (Seedream 4.5) |
| `AIRTABLE_API_KEY` | `.env` → same name    | Airtable content delivery (optional) |

All four secrets must be present. The pipeline will fail with a clear error message if any are missing.

---

## 2. GitHub Pages Setup

The content dashboard deploys to the `gh-pages` branch of this repo.

1. Go to **https://github.com/rtadik/bobe-content-dashboard/settings/pages**
2. Under **Source**, select **Deploy from a branch**
3. Branch: `gh-pages` / folder: `/ (root)`
4. Click **Save**

Live URL: **https://rtadik.github.io/bobe-content-dashboard**
Admin panel: **https://rtadik.github.io/bobe-content-dashboard/admin/**

---

## 3. GitHub Actions Workflow Permissions

The `weekly-pipeline.yml` workflow pushes to the `gh-pages` branch using `GITHUB_TOKEN`.
This requires the repo's default workflow permission to be **Read and write**.

1. Go to **https://github.com/rtadik/bobe-content-dashboard/settings/actions**
2. Scroll to **Workflow permissions**
3. Select **Read and write permissions**
4. Click **Save**

---

## 4. Admin Panel Authentication

The admin panel uses your GitHub Personal Access Token (PAT) to trigger workflows.
The PAT is stored only in your browser tab's `sessionStorage` — it is never persisted
to `localStorage` or sent to any server other than `api.github.com`.

### Create a PAT

1. Go to **GitHub → Settings → Developer Settings → Personal access tokens → Fine-grained tokens**
2. Click **Generate new token**
3. Set expiration (90 days recommended)
4. Under **Repository access**, select **Only select repositories** and choose `bobe-content-dashboard`
5. Under **Permissions → Repository permissions**, set **Actions** to **Read and write**
6. Click **Generate token** and copy it

Store the PAT in your password manager. You will enter it in the admin panel UI each session.

---

## 5. Branch Note

Both workflow files (`weekly-pipeline.yml` and `onboard-client.yml`) reference `Fork-#1`
as the working branch (`ref: Fork-#1`). When `Fork-#1` is merged to `main`, update the
`ref:` field in both workflow files to `main`.

---

## 6. Trigger a Test Run

Once secrets are configured:

1. Go to **https://github.com/rtadik/bobe-content-dashboard/actions**
2. Select **Weekly Content Pipeline** from the left sidebar
3. Click **Run workflow** → set `mock: true` → click **Run workflow**
4. Watch the run logs to confirm all steps complete

Or use the admin panel at **https://rtadik.github.io/bobe-content-dashboard/admin/**:
1. Enter your PAT
2. Check **Mock run**
3. Click **Run Pipeline**

---

## 7. Artifact Download

After each pipeline run, the Excel workbook is uploaded as a GitHub Actions artifact
(downloadable for 30 days from the run page). To access it:

1. Go to **https://github.com/rtadik/bobe-content-dashboard/actions**
2. Click the completed pipeline run
3. Scroll to the bottom — **Artifacts** section
4. Download `weekly-content-{client_id}-{run_id}.xlsx`
