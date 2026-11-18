# Request AI-enabled access

The separate `/request-ai-access` page accepts a name, email, optional organization
and intended use. Applicants complete reCAPTCHA, receive an eight-digit email
code, then submit that code to record their request for operator review.
The code verifies control of that inbox. It is not an AI access token, and this
flow never enables inference, creates an account or grants workspace access.

Intake is OFF by default. Without provisioned settings the page explains that
requests are unavailable; it does not simulate verification or claim a submission.
Applicants' drafts and codes stay in page memory. Completed requests are held in
an external private queue, not in the Alloy corpus or vector database.

## Deployment configuration

Provision settings outside the installation, for example
`/var/lib/allow-intake-private/settings.json`, with mode `0600` under a service-owned
`0700` directory. All ancestors must be trusted and non-writable by other users;
symlinks are rejected. Create a separate service-owned `0700` directory for the
request queue, such as `/var/lib/allow-intake-private/requests`, under a private
`0700` parent. The settings file must not be inside the queue. Do not put either
directory in the repository or transfer package.

The settings file must contain exactly these keys:

- `smtpHost`, `smtpPort`, `smtpUsername`, `smtpPassword`: authenticated SMTP
  submission supporting mandatory STARTTLS, valid certificates and hostname checks.
- `sender`: a fixed sender address authorized by that mail service.
- `siteKey`, `captchaSecret`: reCAPTCHA v2 checkbox keys provisioned for the hostname.
- `hostname`: the exact public hostname, normally `allow.alloy4.fun`.
- `queueDirectory`: the absolute path of the private request queue.

Add only `"access_request_config": "/var/lib/allow-intake-private/settings.json"`
to the protected deployment `instance.json`. The service forwards the validated
path, disables core dumps and keeps secret values out of command-line arguments.
The setting is independent of `ai_mode`; anonymous AI remains disabled. Direct
local launches use `--allow.access-request.config=/absolute/protected/settings.json`.
Leave that option absent to keep intake OFF. Never use production credentials in
tests or commit settings, inbox addresses, request records or verification codes.

The page is proxied by the existing IIS rule. No extra public API to list requests
is exposed. Invalid explicit configuration stops startup rather than falling back
to a partially secured form.

## Verification and review

The server verifies reCAPTCHA through Google's fixed HTTPS endpoint, requiring
success, the configured hostname and a fresh timestamp. Tokens are single-use
and expire after two minutes according to
[Google's verification documentation](https://developers.google.com/recaptcha/docs/verify).
The complete submitted form is frozen into a ten-minute challenge. Only the
challenge identifier and email code are accepted during verification; changing
the email or purpose requires a new challenge and CAPTCHA.

There are at most five code attempts. Code hashes are held in memory; a restart
invalidates pending challenges. Provider failures, expiry and persistence errors
fail closed. The queue records only verified requests, with no automatic approval.
Operators must review the requested use and provision any eventual access through
a separately authorized process. The existing launch token must never be sent as
an applicant token.

Treat queue records as personal data: restrict access to the review operator,
review them promptly, and explicitly purge records after 30 days. This release
does not provide a review dashboard, an automatic retention job or token issuance.
Uncertain writes can leave a file needing operator inspection; all such files
count against the 1,000-record capacity. Never retry an ambiguous verification
write as a new approved request.

## Isolation and production acceptance

Only the CAPTCHA child frame loads Google code. Both the HTML iframe and the
child's HTTP Content Security Policy use `sandbox allow-scripts`, without
`allow-same-origin`. Direct child navigation stays sandboxed. The parent checks
the exact source window, opaque origin and rotating nonce for every message.
The child receives only a public site key and nonce, not applicant details or
workspace authority. Parent and workbench CSPs do not permit Google scripts.

Production activation requires a human browser test with the configured Google
keys in this opaque sandbox, and successful real email delivery. These are OPEN
until provisioning. If the provider does not support the sandbox, keep intake
disabled; do not add `allow-same-origin` or move its script into the parent. A
separate dedicated origin would require another reviewed design.

In-process limits cap challenge attempts at 10/hour globally and 3/hour per email
with a 60-second cooldown, verification at 60/minute, and concurrent external
work at two operations. Failures consume the attempt budget. Restarts reset these
budgets. A durable independent edge limiter is required before public enablement;
the conservative global cap also allows deliberate denial of intake availability.
SMTP spam controls, Google/mail service terms and costs, privacy handling,
retention operations and commercial readiness remain operator acceptance gates.

The [contract](../spec/ai-access-request.json),
[finite Lean proof](../formal/Allow/AiAccessRequest.lean) and
[six-reviewer decision](../gates/ai-access-request-v1/council-disposition.json)
preceded production implementation. They prove an abstract admission policy,
not the network, provider, filesystem, production implementation or deployment.
