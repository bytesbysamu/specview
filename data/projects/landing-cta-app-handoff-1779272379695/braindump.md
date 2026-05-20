Landing page CTA should redirect into the real app, not show results inline.

Current behavior: visitor pastes braindump on landing page, clicks Analyze, the analysis renders below the textarea on the landing page itself. The visitor stays on the static landing page the whole time.

Desired behavior: visitor pastes braindump on landing page, clicks the CTA button, the landing page fires the POST /api/public/analyze call immediately, then redirects the visitor into the real Angular app. The app picks up the in-flight job and shows the analysis polling/rendering in the real app UI with the real project view. The visitor sees the actual product, not a stripped-down landing page rendering.

The flow:
1. Visitor pastes braindump on landing page
2. Clicks CTA
3. Landing page POSTs to /api/public/analyze, gets back job_id
4. Landing page redirects to the app with the job_id (e.g. app.specview.dev/analyze?job=<job_id>)
5. App picks up the job_id from the URL, starts polling /api/public/analyze/<job_id>
6. Analysis renders progressively in the real app view — same UI as authenticated users see
7. A real project is created in the app so the visitor can see their analysis in context
8. For anything beyond viewing the analysis (full spec suite, editing, etc.), the visitor needs to sign up

Key change: the landing page does NOT render the result itself. It only fires the API call and hands off to the app. The app owns the rendering. This means the visitor experiences the real product UI from the first interaction.

The anonymous project should be visible in the app without auth. The job_id in the URL acts as a bearer token — if you have it, you can view the result. But to do anything else (generate more docs, save, edit), you need to sign up.

This replaces the current inline rendering on the landing page (landing/analyze.js showing results in a div). Instead, analyze.js just makes the POST call and redirects.

The backend must create a real project for the anonymous visitor. When POST /api/public/analyze fires, it saves the braindump into a new project on the filesystem (same as authenticated projects), then runs the analysis step against that project. The job_id maps to a real project_id. When the app loads with that job_id, it can show the project with the braindump already saved and the analysis generating into the same project. The visitor sees their braindump and analysis side by side in the real project view — just like an authenticated user would. The project belongs to an anonymous session until the visitor signs up and claims it.
