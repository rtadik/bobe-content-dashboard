# Admin Panel & Dashboard Infrastructure Summary

**Date**: 2026-03-17  
**Purpose**: Comprehensive reference for admin panel architecture, authentication, styling, and integration with static build process

---

## Overview

The RT Content Generator workspace includes a password-protected admin panel (`/admin/`) that enables workflow triggering, status monitoring, and client onboarding. The admin panel is optional in deployment (requires `--include-admin` flag in `build_static.py`) and includes:

- GitHub Personal Access Token (PAT) authentication
- Workflow triggering for weekly pipeline, announcements, and client onboarding
- Real-time workflow status monitoring with auto-polling
- Multi-client capability via per-client config isolation

---

## File Structure

```
admin/
├── index.html       # Password-protected admin panel UI (305 lines)
├── admin.css        # Dark theme styles (547 lines)
└── admin.js         # GitHub API client & workflow automation (593 lines)
```

---

## Authentication Mechanism

### Session Storage (admin.js: lines 1-20)
- **PAT Storage**: Stored exclusively in browser `sessionStorage` under key `github_pat`
- **Lifecycle**: Persists only for the session tab; cleared when tab is closed
- **Never Persisted**: No API calls store the PAT; it's generated fresh each session
- **Security Note**: The PAT is sent directly to `api.github.com` and nowhere else

Helper functions:
```javascript
savePat(pat)          // Stores PAT in sessionStorage
loadPat()             // Retrieves PAT from sessionStorage
clearPat()            // Removes PAT from sessionStorage
```

### PAT Validation Flow
1. User enters GitHub PAT in the "Connect GitHub" section
2. `connect(pat)` function calls `ghFetch('/user')` to validate PAT with GitHub API
3. On success:
   - PAT saved to sessionStorage
   - Auth status badge changes to "Connected" (green, #1589DC)
   - All workflow sections become enabled
   - Disconnect button appears
4. On failure:
   - Error message displayed: "Invalid PAT or network error"
   - Auth status remains "Not connected"

### GitHub API Integration (admin.js: lines 40-80)
```javascript
ghFetch(endpoint, options)
  ├─ Adds Authorization header: "Bearer {pat}"
  ├─ Handles 401/403 responses (suggests PAT regeneration)
  └─ Returns JSON response or throws error

triggerWorkflow(workflow_file, client_payload)
  ├─ Constructs endpoint: `/repos/{repo}/actions/workflows/{workflow}/dispatches`
  └─ Sends POST with client_payload containing workflow inputs
```

**Workflow Files Triggered**:
- `weekly-pipeline.yml` (Weekly Content Pipeline)
- `generate-announcement.yml` (Announcement Test)
- `onboard-client.yml` (Onboard New Client)

---

## UI Sections & Forms

### 1. Connect GitHub (lines 28-64 in index.html)
**Purpose**: Authenticate with GitHub PAT  
**Form Elements**:
- Password input for PAT (placeholder: `ghp_xxxxxxxxxxxxxxxxxxxx`)
- "Connect" button
- Error message display area
- Collapsible help section with 6-step PAT creation instructions

**Help Details**:
- Navigate to GitHub Settings → Developer Settings → Personal access tokens → Fine-grained tokens
- Select repository access: `bobe-content-dashboard` only
- Repository permissions: Actions → "Read and write"
- Recommended expiration: 90 days

### 2. Client Intake Form Link (lines 67-81)
**Purpose**: Share intake form link with new clients  
**Content**:
- Displays URL: `https://content.rejiglabs.com/intake/`
- Copy button for easy sharing
- Explanation: 9-section intake form, email + JSON download for onboarding

### 3. Weekly Content Pipeline (lines 84-129)
**Purpose**: Trigger full pipeline run for weekly content generation  
**Visible Only When**: Connected to GitHub (display: none by default)

**Form Fields**:
- Client ID (default: "bobe")
- Week Of (optional, format: YYYY-MM-DD, defaults to current Monday)

**Checkboxes**:
- Skip image generation (faster run, content only)
- Skip Airtable sync
- Mock run (no API calls, testing only)

**Execution Flow**:
1. User fills form and clicks "Run Pipeline"
2. `runPipeline()` collects form data
3. Triggers `weekly-pipeline.yml` via GitHub Actions API
4. Success message displays: "Pipeline triggered. Check Run Status below."
5. Run Status section auto-polls for completion

**Behind the Scenes**:
- Workflow dispatches to `pipeline_runner.py` with parameters:
  - `client`: Client ID
  - `week_of`: Week date (or current Monday)
  - `skip_images`: Boolean flag
  - `skip_airtable`: Boolean flag
  - `mode`: 'full'
  - `export_excel`: True (for compatibility)

### 4. Announcement Test (lines 132-195)
**Purpose**: Test announcement generation in isolation  
**Visible Only When**: Connected to GitHub

**Form Fields**:
- Client ID (default: "bobe")
- Week Of (optional, format: YYYY-MM-DD)
- Announcement Text (required textarea, 4 rows, placeholder guides user)

**Checkbox**:
- Mock run (no API calls, testing only)

**Tabbed Interface** (3 phases):

#### Tab: Content
- Generates 1 topic angle + EN content (Twitter thread + Telegram post) + image prompts + RU translation
- Should be run **first**
- Button: "Test Content"

#### Tab: Images
- Generates EN + RU images for existing topic
- Requires content phase to have run first
- Button: "Test Images" (with image icon)

#### Tab: Translation
- Re-generates only Russian translation for existing EN content
- Requires content phase first
- Button: "Test Translation" (with globe icon)

**Execution Flow**:
1. User enters client ID, week, and announcement text
2. Selects tab and clicks test button
3. `runAnnouncementTest(phase)` attempts hybrid execution:
   - **Local First**: Tries Flask `/api/generate-announcement` endpoint (localhost:5001)
   - **Fallback**: If local fails, triggers GitHub Actions `generate-announcement.yml`
4. For local execution: `pollJobStatus()` polls Flask API every 3 seconds
5. Success/error message displayed in `.ann-msg` or `.ann-error` elements

**Mode Hint Display**:
- Element `#ann-mode-hint` shows execution context (green text, 0.75rem)
- Displays: "Running locally..." or "Triggered GitHub Actions workflow"

### 5. Onboard New Client (lines 198-253)
**Purpose**: Create new client directory and commit to repo  
**Visible Only When**: Connected to GitHub

**Required Fields** (6 total):
1. Client ID (lowercase, no spaces, e.g., "acmecorp")
2. Display Name (e.g., "Acme Corp")
3. Tagline (one-line brand tagline)
4. Website (e.g., "acmecorp.com")
5. Industry (e.g., "DeFi, SaaS, ecommerce...")
6. Airtable Base ID (optional, format: `appXXXXXXXXXX`)

**Hidden Fields** (defaults):
- Platforms: "twitter,telegram"
- Primary Color: "#1a1a2e"
- Accent Color: "#00aaff"

**Execution Flow**:
1. User fills all required fields, optionally adds Airtable Base ID
2. Clicks "Create Client"
3. `runOnboard()` validates client ID (alphanumeric, lowercase) and website format
4. Triggers `onboard-client.yml` workflow
5. Workflow creates `clients/{client_id}/` directory from `_template/`
6. Next steps message displays: "Client created. Next step: run `/onboard-client {id}` in Claude Code..."

**Workflow Execution**:
- Creates directory structure with template files
- **Important Note**: Static files (config.json, content-guidelines.md, etc.) are created by the workflow
- User must then run `/onboard-client {id}` command in Claude Code to AI-draft content guidelines

### 6. Run Status (lines 256-291)
**Purpose**: Monitor workflow execution across three categories  
**Visible Only When**: Connected to GitHub

**Layout**: 3-column grid
- Column 1: Weekly Pipeline Runs
- Column 2: Announcement Runs
- Column 3: Onboard Runs

**Features**:
- Auto-refresh indicator: Shows "Auto-refreshing" badge with pulse animation when active
- Manual refresh button: "↻ Refresh" (top right)
- Auto-polling: Starts only when active runs exist, 30-second interval

**Run Display Format**:
```
[Status Badge] {Workflow Name}
{Client} / {Week}
{Relative Time} ago  [Status Details]
```

**Status Colors**:
- Yellow (#E0C145): Queued
- Blue (#1589DC): In Progress
- Green (#5BD69F): Completed
- Red (#FF5A5A): Failed

**Relative Time Display** (lines 470-480 in admin.js):
- Generates strings like "2 minutes ago", "1 hour ago", "3 days ago"
- Updated by `refreshStatus()` function

---

## CSS Architecture

### Color Palette (admin.css: lines 4-21)
```css
--bg: #0D1526                /* Background (dark navy) */
--bg-secondary: #1a2d4d      /* Secondary bg (slightly lighter) */
--primary: #1589DC           /* Primary accent (bright blue) */
--accent: #00aaff            /* Alt accent (cyan) */
--success: #5BD69F           /* Success state (green) */
--warning: #E0C145           /* Warning state (yellow) */
--error: #FF5A5A             /* Error state (red) */
--text-primary: #f0f0f0      /* Primary text (light gray) */
--text-secondary: #b0b0b0    /* Secondary text (darker gray) */
--border: #2a4a6a            /* Border color */
```

### Typography
**Font Stack**: `-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif`  
**Monospace Stack**: `'SF Mono', 'Fira Code', monospace`

**Font Sizes**:
- Body: 14px / 1.6 line-height
- Card titles: 18px / 1.3
- Labels: 13px
- Hints/secondary: 0.85em (11.9px)

### Layout & Spacing
- **Border Radius**: 10px (standard), 6px (small)
- **Container**: max-width 1200px, margin: 0 auto
- **Padding Standard**: 16px (cards), 24px (sections)
- **Gap**: 12px (form groups), 8px (buttons)

### Responsive Design
**Breakpoint**: 600px

```css
@media (max-width: 600px) {
  .form-grid {
    grid-template-columns: 1fr;  /* Single column on mobile */
  }
  .runs-grid {
    grid-template-columns: 1fr;  /* Single column on mobile */
  }
}
```

### Key Component Styles

#### Buttons
```css
.btn {
  padding: 10px 16px;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary {
  background: var(--primary);
  color: white;
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border);
}
```

#### Input Elements
```css
.input {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  color: var(--text-primary);
  padding: 10px 12px;
  border-radius: 6px;
}

.input:focus {
  border-color: var(--primary);
  outline: none;
  box-shadow: 0 0 0 3px rgba(21, 137, 220, 0.2);
}
```

#### Message States
```css
.success-msg {
  color: var(--success);
  background: rgba(91, 214, 159, 0.15);
  padding: 12px;
  border-radius: 6px;
  border-left: 3px solid var(--success);
}

.error-msg {
  color: var(--error);
  background: rgba(255, 90, 90, 0.15);
  padding: 12px;
  border-radius: 6px;
  border-left: 3px solid var(--error);
}
```

#### Auth Badge
```css
.auth-badge {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.85em;
  font-weight: 600;
}

.auth-badge.disconnected {
  background: rgba(255, 90, 90, 0.2);
  color: var(--error);
}

.auth-badge.connected {
  background: rgba(91, 214, 159, 0.2);
  color: var(--success);
}
```

#### Pulse Animation
```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
```

### Sticky Header
```css
.site-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: linear-gradient(to bottom, var(--bg) 80%, transparent);
  backdrop-filter: blur(10px);
}
```

---

## JavaScript Implementation

### Session Management
```javascript
// PAT storage helpers
function savePat(pat) {
  sessionStorage.setItem('github_pat', pat);
}

function loadPat() {
  return sessionStorage.getItem('github_pat');
}

function clearPat() {
  sessionStorage.removeItem('github_pat');
}
```

### GitHub API Client
```javascript
async function ghFetch(endpoint, options = {}) {
  const pat = loadPat();
  if (!pat) throw new Error('PAT not loaded');
  
  const url = `https://api.github.com${endpoint}`;
  const headers = {
    'Authorization': `Bearer ${pat}`,
    'Accept': 'application/vnd.github.v3+json',
    ...options.headers
  };
  
  const response = await fetch(url, { ...options, headers });
  
  if (response.status === 401 || response.status === 403) {
    clearPat();
    throw new Error('Unauthorized. PAT may be expired. Please regenerate.');
  }
  
  return response.json();
}
```

### Workflow Triggering
```javascript
async function triggerWorkflow(workflow_file, client_payload) {
  const endpoint = `/repos/rtadik/bobe-content-dashboard/actions/workflows/${workflow_file}/dispatches`;
  const body = {
    ref: 'main',
    inputs: client_payload
  };
  
  await ghFetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
}
```

### Status Polling
```javascript
async function refreshStatus() {
  try {
    // Fetch runs from all three workflows in parallel
    const [pipeline, announcement, onboard] = await Promise.all([
      getWorkflowRuns('weekly-pipeline.yml'),
      getWorkflowRuns('generate-announcement.yml'),
      getWorkflowRuns('onboard-client.yml')
    ]);
    
    renderRuns('pipeline-runs', pipeline);
    renderRuns('announcement-runs', announcement);
    renderRuns('onboard-runs', onboard);
    
    // Auto-refresh only if active runs exist
    const hasActive = pipeline.concat(announcement, onboard)
      .some(r => ['queued', 'in_progress'].includes(r.status));
    
    if (hasActive && !autoRefreshTimer) {
      autoRefreshTimer = setInterval(refreshStatus, 30000); // 30 seconds
    } else if (!hasActive && autoRefreshTimer) {
      clearInterval(autoRefreshTimer);
      autoRefreshTimer = null;
    }
  } catch (error) {
    console.error('Status refresh failed:', error);
  }
}
```

### Hybrid Announcement Execution
```javascript
async function runAnnouncementTest(phase) {
  const text = document.getElementById('ann-text').value;
  const clientId = document.getElementById('ann-client').value;
  const week = document.getElementById('ann-week').value;
  const mock = document.getElementById('ann-mock').checked;
  
  // Try local Flask first
  try {
    const response = await fetch('http://localhost:5001/api/generate-announcement', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_id: clientId,
        week_of: week,
        announcement_text: text,
        phase: phase,
        mock: mock
      })
    });
    
    if (response.ok) {
      const job = await response.json();
      document.getElementById('ann-mode-hint').textContent = 'Running locally...';
      // Poll for completion
      pollJobStatus(job.job_id);
      return;
    }
  } catch (e) {
    // Fall through to GitHub Actions
  }
  
  // Fallback to GitHub Actions
  document.getElementById('ann-mode-hint').textContent = 'Triggered GitHub Actions workflow';
  await triggerWorkflow('generate-announcement.yml', {
    client_id: clientId,
    week_of: week,
    announcement_text: text,
    phase: phase,
    mock: mock.toString()
  });
}
```

### XSS Prevention
```javascript
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Usage in rendering
function renderRuns(containerId, runs) {
  const html = runs.map(run => 
    `<div class="run-item">
      <span class="status-badge ${run.status}"></span>
      ${escapeHtml(run.name)}
      <span class="run-time">${getRelativeTime(run.created_at)}</span>
    </div>`
  ).join('');
  
  document.getElementById(containerId).innerHTML = html;
}
```

---

## Integration with Static Build

### build_static.py Integration

#### Admin Panel Inclusion (Optional)
The admin panel is **NOT** included in deployment by default. Inclusion requires explicit flag:

```bash
python scripts/build_static.py --output dist --include-admin
```

**Flag Location**: Lines 3820-3821 in build_static.py  
**Condition**: `if args.include_admin:`

#### Copy Logic (Lines 3851-3858)
```python
if args.include_admin:
    admin_src = Path(__file__).parent.parent / "admin"
    admin_dst = Path(args.output) / "admin"
    if admin_src.exists():
        shutil.copytree(str(admin_src), str(admin_dst), 
                        dirs_exist_ok=True)
        print(f"  Admin panel copied to {admin_dst}")
    else:
        print("  Warning: admin/ directory not found, 
               skipping --include-admin")
```

**Operation**:
1. Locates `admin/` directory in project root
2. Copies entire directory to `{output}/admin/`
3. `dirs_exist_ok=True` allows idempotent re-runs (no errors if directory exists)
4. Prints confirmation or warning message

#### Login Page Routing
**File**: `templates/login.html` (generated from Jinja2)  
**Role Detection** (Lines 2599-2600 in build_static.py):

```python
if user_role == 'admin':
    # Redirect to /admin/ page
    window.location.href = '/admin/';
```

#### Credential Generation (Lines 64-98 in build_static.py)
```python
def generate_credentials():
    """Generate auto-credentials for all onboarded clients."""
    clients = []
    for client_dir in Path('clients').iterdir():
        if client_dir.name in ('_template',) or client_dir.name.startswith('_'):
            continue
        
        client_id = client_dir.name
        password = f"{client_id}123"
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        clients.append({
            'username': 'admin',
            'password_hash': password_hash,
            'client_id': client_id,
            'role': 'admin',
            'display_name': client_id.title()
        })
    
    return clients
```

**Auto-Generated Credentials**:
- **Username**: "admin" (consistent for all clients)
- **Password Format**: "{client_id}123" (e.g., "bobe123", "acmecorp123")
- **Hash Algorithm**: SHA-256
- **Discovery**: Reads all directories in `clients/` directory
- **Exclusions**: Skips `_template` and any directory starting with underscore

---

## Deployment & Access

### Local Development
**Admin Panel URL**: http://localhost:5000/admin/  
**Note**: Only accessible after authentication on login page

### Production (Cloudflare Pages)
**Admin Panel URL**: https://content.rejiglabs.com/admin/  
**Alternative URL**: https://bobe-content-dashboard.pages.dev/admin/

### Availability
- Admin panel is optional in deployment
- When included (`--include-admin` flag), accessible to all authenticated users with admin role
- Login credentials auto-generated per client

---

## GitHub Actions Integration

### Workflows Triggered from Admin Panel

| Workflow | Input Parameters | Purpose |
|----------|-----------------|---------|
| `weekly-pipeline.yml` | client_id, week_of, skip_images, skip_airtable, mode, export_excel | Full weekly content pipeline |
| `generate-announcement.yml` | client_id, week_of, announcement_text, phase, mock | Single announcement test |
| `onboard-client.yml` | client_id, display_name, tagline, website, industry, platforms, airtable_base_id, primary_color, accent_color | New client onboarding |

### Execution Model
1. User fills form in admin panel
2. JavaScript collects form data
3. `triggerWorkflow()` POSTs to GitHub Actions API
4. Workflow executes on GitHub's runners
5. Status updates fetched every 30 seconds by `refreshStatus()`
6. Results displayed in Run Status section

### Fallback for Announcements
- Announcement test attempts local Flask first (faster feedback)
- Falls back to GitHub Actions if local unavailable
- Mode hint displays which path was used

---

## Security Considerations

### PAT Security
- ✓ Stored only in `sessionStorage` (cleared on tab close)
- ✓ Never transmitted to third-party servers
- ✓ Never persisted to disk or cookie
- ✓ Sent only to `api.github.com` via HTTPS
- ✓ Validation via GitHub API before use

### XSS Prevention
- ✓ All user-generated content escaped via `escapeHtml()`
- ✓ Uses `textContent` manipulation to prevent script injection
- ✓ Applied to workflow names, client IDs, and timestamps

### CSRF Protection
- ✓ GitHub API uses Bearer token (not cookie-based)
- ✓ Tokens are session-local, not shared cross-site
- ✓ Form submissions via API, not form posts

### Input Validation
- ✓ Client ID validated: alphanumeric, lowercase, no spaces
- ✓ Website URL format validated
- ✓ Week date format: YYYY-MM-DD
- ✓ Announcement text required (non-empty)

---

## Visual Design Language

### Dark Theme Rationale
- Reduces eye strain for extended admin panel use
- Aligns with modern SaaS admin UI conventions
- High contrast for accessibility (WCAG AA compliance)
- Professional appearance for B2B use

### Color System
- **Primary (#1589DC)**: Interactive elements, focus states, primary actions
- **Accent (#00aaff)**: Alternative highlight, secondary actions
- **Success (#5BD69F)**: Positive states, completed workflows
- **Warning (#E0C145)**: Cautionary states, queued workflows
- **Error (#FF5A5A)**: Negative states, failed workflows
- **Background (#0D1526)**: Primary canvas, maximum contrast
- **Text Primary (#f0f0f0)**: Main text, high readability
- **Text Secondary (#b0b0b0)**: Labels, hints, secondary info

### Layout Principles
- **Vertical Rhythm**: Consistent spacing (8px, 12px, 16px, 24px)
- **Grid System**: 2-column form layout, 3-column status grid
- **Card-Based**: Sectioned functionality in distinct cards
- **Responsive**: Single column on mobile (600px breakpoint)
- **Sticky Header**: Navigation always visible, z-index: 100

### Typography Hierarchy
- **H1/Page Title**: 24px, primary color
- **H2/Section Title**: 18px, primary text
- **Body**: 14px / 1.6 line-height, secondary text
- **Labels**: 13px, semi-bold
- **Hints/Help Text**: 11-12px, secondary color

---

## Future Enhancements

Potential improvements to consider:
1. Multi-workspace support (multiple GitHub org/repo pairs)
2. Webhook integration for automatic status updates (replace polling)
3. Workflow log viewer integrated into status panel
4. Client activity audit trail
5. Scheduled pipeline runs (cron-based)
6. Batch workflow triggering for multiple clients
7. API rate limit monitoring and warnings
8. Dark/light theme toggle

---

## References

- **GitHub API Docs**: https://docs.github.com/en/rest
- **GitHub Actions Workflow Dispatch**: https://docs.github.com/en/rest/actions/workflows?apiVersion=2022-11-28#create-a-workflow-dispatch-event
- **RFC 3394 (Session Storage)**: Web Storage specification
- **OWASP XSS Prevention**: https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html
