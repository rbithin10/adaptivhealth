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
src/
├── components/        # Reusable UI components
├── pages/            # Page components (Login, Dashboard, etc.)
├── services/         # API service layer
└── App.tsx           # Main application component
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
