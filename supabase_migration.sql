-- ============================================================
-- IndexField Full Database Migration
-- Run this ENTIRE script in the Supabase SQL Editor
-- ============================================================

-- ============================================================
-- 1. PROFILES TABLE (create or update)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  full_name TEXT,
  job_title TEXT DEFAULT 'Technician',
  company TEXT DEFAULT '',
  role TEXT DEFAULT 'admin' CHECK (role IN ('admin', 'tech', 'viewer')),
  onboarded BOOLEAN DEFAULT FALSE,
  query_count INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add onboarded column if table already exists
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'profiles' AND column_name = 'onboarded') THEN
    ALTER TABLE public.profiles ADD COLUMN onboarded BOOLEAN DEFAULT FALSE;
  END IF;
END $$;

-- Add query_count column if table already exists
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'profiles' AND column_name = 'query_count') THEN
    ALTER TABLE public.profiles ADD COLUMN query_count INT DEFAULT 0;
  END IF;
END $$;

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'profiles' 
    AND policyname = 'Users can view own profile'
  ) THEN
    CREATE POLICY "Users can view own profile" ON profiles FOR SELECT USING (auth.uid() = id);
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'profiles' 
    AND policyname = 'Users can update own profile'
  ) THEN
    CREATE POLICY "Users can update own profile" ON profiles FOR UPDATE USING (auth.uid() = id);
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'profiles' 
    AND policyname = 'Users can insert own profile'
  ) THEN
    CREATE POLICY "Users can insert own profile" ON profiles FOR INSERT WITH CHECK (auth.uid() = id);
  END IF;
END $$;

-- ============================================================
-- 2. USER MANUALS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.user_manuals (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  backend_id TEXT,                    -- ID returned from backend processing
  filename TEXT NOT NULL,
  asset_type TEXT DEFAULT 'Industrial Equipment',
  status TEXT DEFAULT 'processing',
  page_count INT DEFAULT 0,
  section_count INT DEFAULT 0,
  chunk_count INT DEFAULT 0,
  file_size_bytes BIGINT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.user_manuals ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'user_manuals' 
    AND policyname = 'Users can view own manuals'
  ) THEN
    CREATE POLICY "Users can view own manuals" ON user_manuals FOR SELECT USING (auth.uid() = user_id);
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'user_manuals' 
    AND policyname = 'Users can insert own manuals'
  ) THEN
    CREATE POLICY "Users can insert own manuals" ON user_manuals FOR INSERT WITH CHECK (auth.uid() = user_id);
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'user_manuals' 
    AND policyname = 'Users can update own manuals'
  ) THEN
    CREATE POLICY "Users can update own manuals" ON user_manuals FOR UPDATE USING (auth.uid() = user_id);
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'user_manuals' 
    AND policyname = 'Users can delete own manuals'
  ) THEN
    CREATE POLICY "Users can delete own manuals" ON user_manuals FOR DELETE USING (auth.uid() = user_id);
  END IF;
END $$;

-- ============================================================
-- 3. USER ASSETS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.user_assets (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  asset_code TEXT NOT NULL,
  name TEXT NOT NULL,
  model TEXT DEFAULT '',
  location TEXT DEFAULT '',
  status TEXT DEFAULT 'online' CHECK (status IN ('online', 'offline', 'warning', 'maintenance')),
  serial_number TEXT DEFAULT '',
  last_maint TIMESTAMPTZ,
  next_maint TIMESTAMPTZ,
  qr_token TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.user_assets ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'user_assets' 
    AND policyname = 'Users can view own assets'
  ) THEN
    CREATE POLICY "Users can view own assets" ON user_assets FOR SELECT USING (auth.uid() = user_id);
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'user_assets' 
    AND policyname = 'Users can insert own assets'
  ) THEN
    CREATE POLICY "Users can insert own assets" ON user_assets FOR INSERT WITH CHECK (auth.uid() = user_id);
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'user_assets' 
    AND policyname = 'Users can update own assets'
  ) THEN
    CREATE POLICY "Users can update own assets" ON user_assets FOR UPDATE USING (auth.uid() = user_id);
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'user_assets' 
    AND policyname = 'Users can delete own assets'
  ) THEN
    CREATE POLICY "Users can delete own assets" ON user_assets FOR DELETE USING (auth.uid() = user_id);
  END IF;
END $$;

-- Add qr_token column if table already exists without it
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_assets' AND column_name = 'qr_token') THEN
    ALTER TABLE public.user_assets ADD COLUMN qr_token TEXT UNIQUE;
    -- Generate random tokens for existing assets
    UPDATE public.user_assets SET qr_token = encode(gen_random_bytes(16), 'hex') WHERE qr_token IS NULL;
    ALTER TABLE public.user_assets ALTER COLUMN qr_token SET NOT NULL;
  END IF;
END $$;

-- Create function to auto-generate qr_token for new assets
CREATE OR REPLACE FUNCTION public.generate_qr_token()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.qr_token IS NULL OR NEW.qr_token = '' THEN
    NEW.qr_token := encode(gen_random_bytes(16), 'hex');
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-generate qr_token on insert
DROP TRIGGER IF EXISTS on_user_asset_insert ON public.user_assets;
CREATE TRIGGER on_user_asset_insert
  BEFORE INSERT ON public.user_assets
  FOR EACH ROW
  EXECUTE FUNCTION public.generate_qr_token();

-- ============================================================
-- 4. KNOWLEDGE POSTS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.knowledge_posts (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  author_name TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  asset_code TEXT,
  likes INT DEFAULT 0,
  verified BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.knowledge_posts ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'knowledge_posts' 
    AND policyname = 'Users can view own posts'
  ) THEN
    CREATE POLICY "Users can view own posts" ON knowledge_posts FOR SELECT USING (auth.uid() = user_id);
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'knowledge_posts' 
    AND policyname = 'Users can insert own posts'
  ) THEN
    CREATE POLICY "Users can insert own posts" ON knowledge_posts FOR INSERT WITH CHECK (auth.uid() = user_id);
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'knowledge_posts' 
    AND policyname = 'Users can update own posts'
  ) THEN
    CREATE POLICY "Users can update own posts" ON knowledge_posts FOR UPDATE USING (auth.uid() = user_id);
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'knowledge_posts' 
    AND policyname = 'Users can delete own posts'
  ) THEN
    CREATE POLICY "Users can delete own posts" ON knowledge_posts FOR DELETE USING (auth.uid() = user_id);
  END IF;
END $$;

-- ============================================================
-- 5. QUERY HISTORY TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.query_history (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  query TEXT NOT NULL,
  answer TEXT,
  manual_id TEXT,
  sources JSONB DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.query_history ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'query_history' 
    AND policyname = 'Users can view own queries'
  ) THEN
    CREATE POLICY "Users can view own queries" ON query_history FOR SELECT USING (auth.uid() = user_id);
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'query_history' 
    AND policyname = 'Users can insert own queries'
  ) THEN
    CREATE POLICY "Users can insert own queries" ON query_history FOR INSERT WITH CHECK (auth.uid() = user_id);
  END IF;
END $$;

-- ============================================================
-- 6. AUTO-CREATE PROFILE ON SIGNUP (Trigger)
-- ============================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, onboarded)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email),
    FALSE
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop existing trigger if it exists, then recreate
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================
-- DONE! Your database is ready.
-- ============================================================
