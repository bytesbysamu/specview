/**
 * demo-content.js — Four rotating demo braindumps for the landing page.
 *
 * Each entry has:
 *   slug  — matches a key in DEMO_SLUGS from redirect.js (and app demo fixtures)
 *   text  — the full braindump text that gets typed into the textarea
 *
 * The four categories deliberately represent the messiest, most honest way
 * developers actually think — not polished prose, just real starting points.
 */

window.DEMO_CONTENT = [
  {
    slug: 'mobile-app',
    text: `want to build a habit tracker app but not another checklist thing. the problem with every habit app i've tried is they guilt-trip you when you miss a day. want something more forgiving.

core idea: you set a "rhythm" not a daily streak. so if you want to exercise 4x a week, missing tuesday doesn't break anything. the app just looks at your rolling 7-day window.

UI should be super minimal. one screen. circles for each habit, fill as you log. no charts, no streaks, no gamification nonsense. just a calm visual of how you're doing.

notifications: smart ones based on your actual behavior patterns. if i always exercise in the morning, remind me at 7am. if i skip a week, don't spam me.

monetization: free with 3 habits, paid ($3/mo) for unlimited. no ads ever.

build it native iOS first, android later. need offline-first, sync when back online. maybe share habits with an accountability partner.

timeline: want something shippable in 2 months. solo project.`,
  },
  {
    slug: 'saas-feature',
    text: `we need bulk operations in the dashboard. right now users can only act on one item at a time and we're getting hammered in support tickets about it.

the ask: checkboxes on table rows, a floating action bar that appears when any row is checked, actions are: assign to team member, change status, add tag, archive, delete. delete should require confirmation with count ("delete 12 items?").

tricky part: we have pagination and users want to select ALL matching their current filter, not just the visible page. need a "select all 2,847 matching results" option. this is the hard part — backend has to handle a filter-based bulk operation, not just an ID list.

current stack: react frontend, django rest framework backend, postgres. the table is already using react-table so row selection should be somewhat straightforward.

also: undo. bulk delete is scary. 30-second undo window before the records are actually deleted. soft delete + background job to hard delete after the window.

need to make sure this works with our permission system — users can only bulk-act on items they own or their team owns.

estimate: 2 sprints. biggest risk is the "select all" with filter-based backend operations.`,
  },
  {
    slug: 'side-project',
    text: `i keep losing track of interesting papers i want to read. not arxiv specifically — more like blog posts, substack posts, HN links, the occasional pdf. bookmarks don't work, read-later apps have too much friction.

idea: a dead-simple read-later tool that emails you one thing per day from your backlog. that's it. one item, every morning, based on some rotation logic (mix of oldest unread + stuff you keep ignoring + new additions).

save stuff via: browser extension (one click), email forward (send to save@mything.com), or api. read-later apps always have too many ways to save — i just want these three.

the email should just be the content. if it's a blog post, fetch the article and email the full text. if it's a PDF, send the PDF as attachment. if it's a video, just send the link.

no app UI needed beyond a simple list page to see your backlog and remove stuff. mobile web is fine.

monetization: $3/month or $25/year. free tier: 50 items max. paid: unlimited.

tech: probably just flask + postgres + sendgrid + a browser extension. nothing fancy. want to build this in a weekend and actually use it myself.

biggest unknown: the article fetching/rendering pipeline. need something that handles paywalls gracefully (just send the link if can't fetch).`,
  },
  {
    slug: 'refactoring-task',
    text: `our authentication code is a mess. it grew organically over 3 years and now it's spread across 6 files with duplicated logic everywhere.

current state: auth logic in middleware.py, utils/auth.py, api/helpers.py, and bizarrely some in the user model itself. token validation happens in 3 different places with slightly different behavior. the password reset flow has a bug we've never fixed because nobody wants to touch it.

what i want: a single auth module. one place for token validation, one place for password logic, one place for session management. everything else imports from there.

constraints: can't break existing API contracts. we have mobile clients on old versions that we can't force-update. so the external behavior has to stay identical while we clean up the internals.

approach i'm thinking: create new auth/ module, move things incrementally with a deprecation shim layer so old imports still work, write tests for the current (broken) behavior first so we know what to preserve vs fix.

the password reset bug: tokens don't expire properly when the user changes their email before using the reset link. need to fix this as part of the refactor but make sure the fix is in one place.

estimate: 1 sprint for the refactor, another half sprint for testing. risk: the shim layer becoming permanent and making things worse.`,
  },
];
