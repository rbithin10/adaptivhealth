# Adaptiv Health Dashboard

Healthcare provider dashboard for monitoring patient cardiovascular health with AI-powered risk assessment.

## 🚀 Quick Start

### Prerequisites
- Node.js 16+ and npm
- Backend API reachable (default: AWS ALB endpoint, or local backend via environment override)

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm start
```

The dashboard will open at http://localhost:3000

### Demo Login
- Email: `test@example.com`
- Password: `Pass1234`

## 📁 Project Structure

```
public/                        # Static files served directly (HTML shell, manifest)
src/
├── components/                # Reusable UI building blocks
│   ├── cards/                 # Stat display cards (e.g. "Total Patients: 42")
│   ├── common/                # Shared components (top nav bar, status badges)
│   └── patient/               # Patient health panels (vitals, risk, alerts, ML)
├── pages/                     # Full-page views (Login, Dashboard, Admin, etc.)
├── services/                  # Backend communication (API client)
├── theme/                     # Visual styling (colours, fonts, MUI theme)
├── types/                     # Data shape definitions (TypeScript interfaces)
├── App.tsx                    # Main app — routing and role-based access control
├── index.tsx                  # Entry point — mounts the app in the browser
├── App.css                    # Global app container styles
├── index.css                  # Base page styles (fonts, buttons, scrollbars)
└── setupTests.ts              # Test configuration
```

## 🔧 Available Scripts

- `npm start` - Run development server
- `npm build` - Build for production
- `npm test` - Run tests

## 🎨 Features

✅ User authentication (JWT)
✅ Real-time dashboard with stats
✅ Patient monitoring
✅ Material-UI components
✅ TypeScript support
✅ Responsive design

## 🔗 Backend Integration

By default, the dashboard client targets the deployed AWS ALB backend.

To run against local backend instead, set:

```bash
REACT_APP_API_URL=http://localhost:8080
```

in your local environment file (for example `.env.development`), then restart the dashboard.

## 📚 Tech Stack

- React 18 + TypeScript
- Material-UI (MUI)
- React Router v6
- Axios for API calls
- Recharts for data visualization
