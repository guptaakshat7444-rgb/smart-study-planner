SMART STUDY PLANNER: SHARED SIDEBAR TEMPLATE UPDATE

WHAT THIS PACKAGE DOES
- Converts the existing pages to extend templates/base.html so they share the sidebar and top bar.
- Preserves base.html, index.html, and subjects.html from your uploaded archive.
- Retains existing form field names, methods, Jinja variables, and URL calls.

HOW TO APPLY
1. Stop Flask with Ctrl+C.
2. Make a backup copy of your current templates folder.
3. Extract this ZIP and copy the included templates folder into your project, allowing matching files to be replaced.
4. Open template_page_styles.css from this ZIP and append its contents to the END of your existing static/css/style.css. Do not replace your whole stylesheet with this patch.
5. Start Flask again and test Dashboard, Subjects, Topics, Exams, Preferences, Availability, Progress, Sessions, and Study Plan.

LIMITATION
The archive did not include app.py or style.css, so this update was checked for Jinja template syntax, but not run against your local Flask app. Existing route calls were retained; if Flask reports a BuildError, compare that endpoint with app.py.
