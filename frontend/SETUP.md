# Frontend Setup Guide

## Project Structure

```
frontend/
├── public/
│   └── index.html              # HTML entry point
├── src/
│   ├── components/
│   │   ├── ChatInterface.tsx   # Main chat interface
│   │   ├── ChatInterface.css   # Chat styling
│   │   ├── FileUpload.tsx      # PDF upload component
│   │   ├── FileUpload.css      # Upload styling
│   │   ├── Sidebar.tsx         # Navigation sidebar
│   │   └── Sidebar.css         # Sidebar styling
│   ├── config/
│   │   └── api.ts              # API configuration
│   ├── types/
│   │   └── index.ts            # TypeScript type definitions
│   ├── App.tsx                 # Main application component
│   ├── App.css                 # App styling
│   ├── index.tsx               # React entry point
│   └── index.css               # Global styles
├── package.json
├── tsconfig.json
├── .env.example                # Environment variables template
└── .gitignore
```

## Installation

### Prerequisites
- Node.js 16+ and npm

### Steps

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env.local` file (copy from `.env.example`):
```bash
cp .env.example .env.local
```

4. Make sure your backend is running on `http://localhost:8000`

## Running the Application

### Development Mode
```bash
npm start
```

The app will open at `http://localhost:3000`

### Production Build
```bash
npm run build
```

## Features

### 📄 File Upload
- Drag and drop PDF files
- Click to browse and select files
- Visual upload progress indicator
- Real-time processing feedback

### 💬 Chat Interface
- Type and send questions
- Shift + Enter for multi-line input
- Auto-scrolling to latest messages
- Loading states with animations

### 📚 Source Display
- Expandable source cards
- Confidence scores for each result
- Original text preview
- Distance metrics from vector store

### 🎨 UI/UX
- Professional gradient design
- Responsive layout (desktop & mobile)
- Smooth animations and transitions
- Dark mode ready
- Accessibility features

## Environment Variables

Create `.env.local` file with:

```
REACT_APP_API_URL=http://localhost:8000
```

Change the URL if your backend runs on a different host/port.

## Build & Deploy

### Production Build
```bash
npm run build
```

This creates an optimized build in the `build/` folder.

### Deploy to Vercel (Recommended)
```bash
npm i -g vercel
vercel
```

### Deploy to Netlify
Connect your GitHub repo to Netlify for automatic deployments.

## Troubleshooting

### Backend Connection Issues
- Ensure FastAPI backend is running: `uvicorn app.main:app --reload`
- Check backend URL in `.env.local`
- Enable CORS in FastAPI if needed

### Styling Issues
- Clear browser cache (Ctrl+Shift+Delete)
- Try `npm install` again
- Check browser console for errors

### Performance
- The app uses React 18 for optimal performance
- Lazy loading of components
- Optimized re-renders

## Technologies Used

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Axios** - HTTP client (for future implementations)
- **Lucide React** - Icon library
- **CSS3** - Styling with modern features
