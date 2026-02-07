# MIT Hostel Solutions

A comprehensive digital platform for modern hostel management. Streamline operations, enhance communication, and create a better living experience for students and administrators.

**Tagline**: Smart Living, Simplified

## 🎯 Overview

MIT Hostel Solutions is a full-stack web application designed to manage all aspects of hostel operations. It provides separate portals for students and wardens, enabling efficient management of room allocations, leave requests, complaints, fees, notices, and more.

## ✨ Features

### Student Portal
- **Dashboard**: Overview of room allocation, fee status, active complaints, and recent leave applications
- **Profile Management**: View and update personal information, contact details, and academic information
- **Room Information**: View allocated room and bed number, see roommates
- **Leave Management**: Apply for leave, track approval status, view leave history
- **Complaints/Issues**: Report maintenance issues and track their resolution status
- **Notices**: View hostel announcements and important notices
- **Fee Management**: Check fee payment status and view payment history

### Warden Portal
- **Dashboard**: Comprehensive overview with statistics on students, rooms, complaints, leaves, and fees
- **Student Management**: Add, view, search, and manage student records
- **Room Management**: Manage rooms, track occupancy, view room details and members
- **Room Allocation**: Manual and automatic room allocation system
- **Leave Management**: Approve or reject student leave requests
- **Complaints Management**: Track and resolve student complaints
- **Notices Management**: Create and publish hostel notices
- **Fee Management**: Track fee collection, view payment status, generate reports
- **Reports & Analytics**: Generate comprehensive reports and analytics

## 🛠️ Technology Stack

### Frontend
- **React 18.3** - UI library
- **TypeScript** - Type-safe JavaScript
- **Vite 7.2** - Build tool and dev server
- **React Router DOM 6.30** - Client-side routing
- **TanStack Query 5.83** - Data fetching and caching
- **shadcn/ui** - UI component library (Radix UI primitives)
- **Tailwind CSS 3.4** - Utility-first CSS framework
- **Lucide React** - Icon library
- **React Hook Form** - Form management
- **Zod** - Schema validation
- **Recharts** - Chart library for analytics

### Backend
- REST API running on `http://127.0.0.1:8000`
- JSON-based communication
- Session-based authentication

## 📋 Prerequisites

Before you begin, ensure you have the following installed:
- **Node.js** (v18 or higher) - [Download](https://nodejs.org/)
- **npm** or **yarn** - Package manager
- **Git** - Version control

## 🚀 Getting Started

### Installation

1. **Clone the repository**
   ```bash
   git clone <YOUR_GIT_URL>
   cd Hostel_managment-main
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start the development server**
   ```bash
   npm run dev
   ```

4. **Open your browser**
   - The application will be available at `http://localhost:8080`
   - Make sure your backend API is running on `http://127.0.0.1:8000`

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run build:dev` - Build in development mode
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## 📁 Project Structure

```
src/
├── components/
│   ├── StudentLayout.tsx      # Student portal sidebar layout
│   ├── WardenLayout.tsx        # Warden portal sidebar layout
│   └── ui/                     # shadcn/ui components
├── pages/
│   ├── Index.tsx              # Landing page
│   ├── Login.tsx               # Login page (Student & Warden)
│   ├── SignupStudent.tsx        # Student registration
│   ├── SignupWarden.tsx        # Warden registration
│   ├── ForgotPassword.tsx       # Password recovery
│   ├── NotFound.tsx            # 404 page
│   ├── student/                # Student pages
│   │   ├── StudentDashboard.tsx
│   │   ├── Profile.tsx
│   │   ├── Room.tsx
│   │   ├── Leave.tsx
│   │   ├── Complaints.tsx
│   │   ├── Notices.tsx
│   │   └── Fees.tsx
│   └── warden/                 # Warden pages
│       ├── WardenDashboard.tsx
│       ├── Students.tsx
│       ├── Rooms.tsx
│       ├── Allocation.tsx
│       ├── Leaves.tsx
│       ├── Complaints.tsx
│       ├── Notices.tsx
│       ├── Fees.tsx
│       └── Reports.tsx
├── hooks/                      # Custom React hooks
├── lib/                        # Utility functions
├── App.tsx                     # Main application component
├── main.tsx                    # Application entry point
└── index.css                   # Global styles
```

## 🔌 API Integration

The application connects to a backend API running on `http://127.0.0.1:8000`. Key endpoints include:

### Authentication
- `POST /warden-login` - Warden login
- `POST /student-login` - Student login

### Student Endpoints
- `GET /student/{usn}` - Get student details
- `GET /student-leaves/{usn}` - Get student leave history
- `POST /student/recent-leaves` - Get recent leaves
- `POST /complaint/active-count` - Get active complaints count
- `POST /fees/student` - Get student fee details

### Warden Endpoints
- `GET /students` - Get all students
- `POST /add-student` - Add new student
- `GET /rooms` - Get all rooms
- `GET /available-rooms` - Get available rooms
- `GET /pending-students` - Get pending allocations
- `GET /dashboard/summary` - Get dashboard summary
- `GET /fees/summary` - Get fee collection summary

**Note**: Ensure your backend API is running and accessible before using the application.

## 🎨 Design System

The application uses a custom design system with:

- **Color Palette**: Primary (Blue), Secondary (Teal), Success (Green), Warning (Orange), Accent (Orange)
- **Typography**: Modern, clean font system
- **Components**: 40+ reusable UI components from shadcn/ui
- **Responsive Design**: Mobile-first approach
- **Animations**: Smooth transitions and fade-in effects

## 🔐 Authentication

- **Students**: Session stored in localStorage after login
- **Wardens**: Session-based authentication
- **Protected Routes**: Automatic redirect to login if not authenticated

## 🚢 Deployment

### Build for Production

```bash
npm run build
```

This creates an optimized production build in the `dist/` directory.

### Deploy Options

1. **Static Hosting** (Vercel, Netlify, GitHub Pages)
   ```bash
   npm run build
   # Deploy the dist/ folder
   ```

2. **Traditional Web Server**
   - Build the project
   - Serve the `dist/` folder using a web server (Nginx, Apache, etc.)
   - Configure API proxy if needed

3. **Docker** (if containerized)
   ```bash
   docker build -t hostel-management .
   docker run -p 8080:80 hostel-management
   ```

### Environment Variables

Create a `.env` file for environment-specific configurations:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Update API URLs in the codebase if your backend is hosted elsewhere.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is proprietary software for MIT Hostel Solutions.

## 👥 Support

For support, please contact the development team or open an issue in the repository.

## 🔄 Version

Current version: 0.0.0

---

**Built with ❤️ for MIT Hostel Management**