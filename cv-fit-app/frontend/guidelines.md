# 🟢 Project Guidelines: ĐẬU (AI CV Tailoring App)

## 1. Role & Expectations
You are a Senior Frontend Engineer and UI/UX Expert. Your code must be highly modular, scalable, DRY (Don't Repeat Yourself), and perfectly typed. NEVER dump all code into a single `page.tsx` file. Always break down complex views into smaller, manageable components.

## 2. Tech Stack
- **Framework:** Next.js (App Router)
- **Language:** TypeScript (Strict typing required)
- **Styling:** Tailwind CSS + Shadcn UI
- **Icons:** Lucide React

## 3. Brand Identity & Design System
STRICTLY adhere to these design rules. Do not hallucinate colors or styles.
- **Background:** Soft Cream (`bg-[#F9F9F2]`)
- **Primary Color:** Mung Bean Green (`bg-[#98C18E]`, hover: `bg-[#85AE7B]`)
- **Text Color:** Deep Forest (`text-[#2F4F4F]`)
- **Alert/Accent:** Red Bean (`text-[#B22222]`)
- **Vibe:** Minimalist, approachable, tech-startup. 
- **Borders/Corners:** Use `rounded-2xl` or `rounded-3xl` for cards and large buttons. No sharp edges.
- **Shadows:** Use soft, floating shadows (`shadow-sm`, `shadow-md`, `shadow-green-900/5`).

## 4. Architecture & Folder Structure
Follow this standard Next.js App Router structure. If a file is getting longer than 150-200 lines, extract its sections into sub-components.

```text
src/
├── app/
│   ├── page.tsx                 // ONLY the Landing Page wrapper
│   ├── app/                     // The Application Route (Workspace)
│   │   └── page.tsx             // Workspace wrapper (manages state between Step 1 & 2)
│   └── layout.tsx               // Global layout & fonts
├── components/
│   ├── landing/                 // Components specific to Landing Page (Hero, Features, etc.)
│   ├── workspace/               // App components
│   │   ├── InputSection.tsx     // Step 1: CV & JD Textareas
│   │   ├── MatchDashboard.tsx   // Step 2: Top 4 metric cards
│   │   └── DiffViewer.tsx       // Step 2: Side-by-side original vs upgraded CV
│   ├── shared/                  // Reusable UI (Logo, TopNavbar, Footer)
│   └── ui/                      // Shadcn standard components (Button, Card, etc.)
├── lib/
│   └── utils.ts                 // Tailwind merge and shared functions
└── types/
    └── index.ts                 // TypeScript interfaces (e.g., CVData, MatchResult)
```

## 5. Coding Standards
TypeScript: Define clear interface or type for all component props and state objects in types/index.ts.
Modularity: Extract reusable UI elements (like the Logo with the leaf 🌱) into components/shared/Logo.tsx.
State Management: Keep state as close to where it's used as possible. For the workspace flow, manage the step state in app/app/page.tsx and pass data down via props.
Client Components: Use "use client" only at the top of components that require hooks (useState, useEffect, event listeners). Keep layouts and static sections as Server Components.
code
Code
---

### Step 2: Prompt the Agent to Refactor

Once you have saved the `guidelines.md` file, give your AI agent this exact prompt to clean up the mess it made in `page.tsx`:

***

**Prompt for the AI Agent:**

> "I have created a new file called `guidelines.md` in the root of the project. Please read it completely. 
> 
> Right now, the code is messy because everything is dumped into a single `page.tsx` file. Acting as a Senior Next.js Engineer, I want you to **refactor the entire codebase** following the rules and folder structure defined in `guidelines.md`.
> 
> **Specific Tasks:**
> 1. Separate the Landing Page into modular components inside `components/landing/` and leave only the composition in `app/page.tsx`.
> 2. Create the `app/app/page.tsx` route to act as the main Workspace page.
> 3. Extract the Workspace UI into `components/workspace/InputSection.tsx`, `MatchDashboard.tsx`, and `DiffViewer.tsx`.
> 4. Extract shared components like the "Đậu" logo into `components/shared/Logo.tsx`.
> 5. Make sure the state management (switching from step 1 to step 2) works perfectly in the new separated structure.
> 6. Ensure the design system (colors, rounded corners, soft shadows) remains exactly as it is right now.
> 
> Do this step-by-step. Start by creating the folder structure and extracting the shared components, then the landing page, and finally the workspace components."