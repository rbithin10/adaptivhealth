# src/ — Source Code

All the application source code lives here. This is where the React app is built from.

## Folder Structure

| Folder | Purpose |
|--------|---------|
| `components/` | Reusable UI building blocks (cards, panels, badges, navigation bar) |
| `pages/` | Full-page views — one file per screen the user sees (Login, Dashboard, Patient Detail, etc.) |
| `services/` | Code that talks to the backend server (API calls for data, login, messaging, etc.) |
| `theme/` | Visual styling — colours, font sizes, and Material-UI theme configuration |
| `types/` | Data shape definitions — describes what the server sends back so the app knows what to expect |

## Key Root Files

| File | Purpose |
|------|---------|
| `App.tsx` | The main app — sets up page routing and role-based access control |
| `index.tsx` | The entry point — mounts the React app into the browser |
| `App.css` | Global CSS styles for the app container |
| `index.css` | Base page styles — fonts, buttons, scrollbars, form inputs |
| `setupTests.ts` | Test configuration — loaded before every test run |
