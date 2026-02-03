# Business Management Dashboard

This repository provides a blueprint for a Business Management Dashboard built with:

- **Frontend**: React + TypeScript + Tailwind CSS
- **Backend**: Node.js + Express
- **Database**: MongoDB

The sections below include the requested folder structure, database schema, API routes, and setup instructions.

## Folder Structure

```
business-management-dashboard/
├── client/
│   ├── public/
│   └── src/
│       ├── assets/
│       ├── components/
│       │   ├── analytics/
│       │   ├── auth/
│       │   ├── employees/
│       │   ├── projects/
│       │   ├── salary/
│       │   └── worklogs/
│       ├── layouts/
│       ├── pages/
│       │   ├── AdminDashboard.tsx
│       │   ├── EmployeeDashboard.tsx
│       │   ├── Login.tsx
│       │   ├── Employees.tsx
│       │   ├── Projects.tsx
│       │   ├── Salary.tsx
│       │   └── WorkLogs.tsx
│       ├── routes/
│       ├── services/
│       │   ├── api.ts
│       │   └── auth.ts
│       ├── store/
│       ├── styles/
│       ├── types/
│       └── utils/
│   ├── index.html
│   ├── package.json
│   └── tailwind.config.ts
├── server/
│   ├── src/
│   │   ├── config/
│   │   │   ├── db.ts
│   │   │   └── env.ts
│   │   ├── controllers/
│   │   ├── middleware/
│   │   │   ├── auth.ts
│   │   │   └── errorHandler.ts
│   │   ├── models/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── utils/
│   │   └── app.ts
│   ├── package.json
│   └── tsconfig.json
├── docs/
│   └── api.md
├── .env.example
└── README.md
```

## Database Schema (MongoDB)

> The schema uses Mongoose-style definitions for clarity.

### User (Admin/Employee Authentication)

```ts
{
  _id: ObjectId,
  name: string,
  email: string,
  passwordHash: string,
  role: "admin" | "employee",
  employeeId?: ObjectId,
  createdAt: Date,
  updatedAt: Date
}
```

### Employee

```ts
{
  _id: ObjectId,
  name: string,
  email: string,
  roleTitle: string,
  salary: number,
  status: "active" | "inactive",
  createdAt: Date,
  updatedAt: Date
}
```

### WorkLog

```ts
{
  _id: ObjectId,
  employeeId: ObjectId,
  date: Date,
  projectId: ObjectId,
  task: string,
  hours: number,
  status: "pending" | "in-progress" | "completed",
  createdAt: Date,
  updatedAt: Date
}
```

### Project

```ts
{
  _id: ObjectId,
  name: string,
  description: string,
  status: "planned" | "active" | "on-hold" | "completed",
  deadline: Date,
  assignedEmployees: ObjectId[],
  createdAt: Date,
  updatedAt: Date
}
```

### SalaryPayment

```ts
{
  _id: ObjectId,
  employeeId: ObjectId,
  amount: number,
  month: string,
  paymentDate: Date,
  status: "paid" | "pending",
  createdAt: Date,
  updatedAt: Date
}
```

## API Routes

### Authentication

- `POST /api/auth/login` — Admin or employee login.
- `POST /api/auth/logout` — End session.
- `GET /api/auth/me` — Return authenticated user profile.

### Employees

- `GET /api/employees` — List employees.
- `POST /api/employees` — Add employee.
- `GET /api/employees/:id` — Get employee details.
- `PUT /api/employees/:id` — Edit employee.
- `PATCH /api/employees/:id/status` — Activate/deactivate.

### Work Logs

- `GET /api/work-logs` — Admin view of all logs.
- `GET /api/work-logs/me` — Employee view of own logs.
- `POST /api/work-logs` — Submit daily work.
- `PUT /api/work-logs/:id` — Update log (admin/owner).

### Projects

- `GET /api/projects` — List projects.
- `POST /api/projects` — Create project.
- `GET /api/projects/:id` — Project details.
- `PUT /api/projects/:id` — Update project.
- `PATCH /api/projects/:id/assignments` — Assign employees.
- `PATCH /api/projects/:id/status` — Update project status.

### Salary & Payments

- `GET /api/salary/payments` — Payment history.
- `POST /api/salary/payments` — Record salary payment.
- `GET /api/salary/pending` — Pending salary calculation.

### Dashboard Analytics

- `GET /api/analytics/overview` — Total employees, active projects, monthly payments.
- `GET /api/analytics/productivity` — Productivity chart data.

## Setup Instructions

### Prerequisites

- Node.js 18+
- MongoDB (local or Atlas)
- npm or pnpm

### Backend Setup (Express + MongoDB)

```bash
cd server
cp ../.env.example .env
npm install
npm run dev
```

### Frontend Setup (React + Tailwind)

```bash
cd client
npm install
npm run dev
```

### Environment Variables

```
PORT=5000
MONGO_URI=mongodb://localhost:27017/business-dashboard
JWT_SECRET=replace-with-strong-secret
CLIENT_URL=http://localhost:5173
```

## Notes

- The dashboard is designed to be responsive with Tailwind utility classes.
- Use role-based guards to restrict admin-only views and endpoints.
- Analytics endpoints should aggregate data using MongoDB pipelines for speed.
