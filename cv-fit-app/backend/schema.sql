-- SQL schema for CVFit Monetization & Credit Wallet System
-- Execute this script in your Supabase SQL Editor.

-- Drop tables if they exist (for cleanup if needed, run carefully)
-- DROP TABLE IF EXISTS public.credit_transactions;
-- DROP TABLE IF EXISTS public.users;

-- Create users table to store profiles and credit balances
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    image TEXT, -- Avatar URL from Google
    credits INTEGER NOT NULL DEFAULT 5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index on email for fast user lookup
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);

-- Create credit transactions ledger for auditing credit additions/subtractions
CREATE TABLE IF NOT EXISTS public.credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL, -- e.g., +10 (purchase), -1 (use)
    type TEXT NOT NULL,      -- 'signup_bonus', 'purchase', 'cv_analysis', 'mock_interview'
    description TEXT,        -- detail, e.g., "CV Analysis for resume.pdf" or "Bought Starter Pack"
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index on user_id for faster transaction history lookups
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON public.credit_transactions(user_id);

-- Create user_cvs table to store historical resume plain text uploads
CREATE TABLE IF NOT EXISTS public.user_cvs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    cv_text TEXT NOT NULL,
    cv_filename VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index on user_id and is_active for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_cvs_user_id ON public.user_cvs(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_cvs_active_unique ON public.user_cvs(user_id) WHERE is_active = TRUE;
