# lib/ — App Source Code

All the Dart source code for the AdaptivHealth mobile app lives here.

## Subfolders

| Folder | Purpose |
|--------|---------|
| `config/` | Platform detection and app-wide configuration helpers |
| `dev_utils/` | Reserved for future developer/debugging tools |
| `models/` | Data classes that represent things like health predictions |
| `providers/` | State managers that keep track of login status, theme choice, vitals, and chat messages — screens listen to these to stay up to date |
| `screens/` | Full-page views the user navigates between (login, home dashboard, health details, etc.) |
| `services/` | Backend communication, Bluetooth device handling, health platform integrations, and on-device AI |
| `theme/` | Colors, fonts, and visual styling shared across all screens |
| `widgets/` | Reusable UI building blocks used by multiple screens (cards, badges, buttons, charts) |

## Entry Point

`main.dart` — Starts the app, loads saved login tokens, initializes background services, and decides which screen to show first.
