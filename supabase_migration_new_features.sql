-- ============================================================
-- IndexField New Features Database Migration
-- Run this in Supabase SQL Editor after the initial migration
-- ============================================================

-- ============================================================
-- FEATURE 2: SHIFT HANDOVER INTELLIGENCE
-- ============================================================

-- Shift Handovers Table
CREATE TABLE IF NOT EXISTS public.shift_handovers (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT NOT NULL,
  facility_name TEXT NOT NULL,
  shift_type TEXT NOT NULL CHECK (shift_type IN ('DAY', 'NIGHT', 'CUSTOM')),
  shift_start TIMESTAMPTZ NOT NULL,
  shift_end TIMESTAMPTZ NOT NULL,
  generated_at TIMESTAMPTZ DEFAULT NOW(),
  generated_by_name TEXT,
  overall_status TEXT CHECK (overall_status IN ('GREEN', 'AMBER', 'RED')),
  summary TEXT,
  critical_items JSONB DEFAULT '[]'::jsonb,
  work_orders_summary JSONB DEFAULT '[]'::jsonb,
  assets_accessed JSONB DEFAULT '[]'::jsonb,
  maintenance_status JSONB DEFAULT '{}'::jsonb,
  queries_summary JSONB DEFAULT '[]'::jsonb,
  incidents_summary JSONB DEFAULT '[]'::jsonb,
  ai_recommendations JSONB DEFAULT '[]'::jsonb,
  acknowledged_by TEXT,
  acknowledged_at TIMESTAMPTZ,
  share_token TEXT UNIQUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alter table queries to add columns if they don't exist in existing DB
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'shift_handovers' AND column_name = 'generated_by_name') THEN
    ALTER TABLE public.shift_handovers ADD COLUMN generated_by_name TEXT;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'shift_handovers' AND column_name = 'overall_status') THEN
    ALTER TABLE public.shift_handovers ADD COLUMN overall_status TEXT;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'shift_handovers' AND column_name = 'summary') THEN
    ALTER TABLE public.shift_handovers ADD COLUMN summary TEXT;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'shift_handovers' AND column_name = 'critical_items') THEN
    ALTER TABLE public.shift_handovers ADD COLUMN critical_items JSONB DEFAULT '[]'::jsonb;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'shift_handovers' AND column_name = 'work_orders_summary') THEN
    ALTER TABLE public.shift_handovers ADD COLUMN work_orders_summary JSONB DEFAULT '[]'::jsonb;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'shift_handovers' AND column_name = 'assets_accessed') THEN
    ALTER TABLE public.shift_handovers ADD COLUMN assets_accessed JSONB DEFAULT '[]'::jsonb;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'shift_handovers' AND column_name = 'maintenance_status') THEN
    ALTER TABLE public.shift_handovers ADD COLUMN maintenance_status JSONB DEFAULT '{}'::jsonb;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'shift_handovers' AND column_name = 'queries_summary') THEN
    ALTER TABLE public.shift_handovers ADD COLUMN queries_summary JSONB DEFAULT '[]'::jsonb;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'shift_handovers' AND column_name = 'incidents_summary') THEN
    ALTER TABLE public.shift_handovers ADD COLUMN incidents_summary JSONB DEFAULT '[]'::jsonb;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'shift_handovers' AND column_name = 'ai_recommendations') THEN
    ALTER TABLE public.shift_handovers ADD COLUMN ai_recommendations JSONB DEFAULT '[]'::jsonb;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'shift_handovers' AND column_name = 'share_token') THEN
    ALTER TABLE public.shift_handovers ADD COLUMN share_token TEXT UNIQUE;
  END IF;
  
  -- Change acknowledged_by column to TEXT type if it exists as UUID
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'shift_handovers' AND column_name = 'acknowledged_by' AND data_type = 'uuid') THEN
    ALTER TABLE public.shift_handovers DROP COLUMN acknowledged_by;
    ALTER TABLE public.shift_handovers ADD COLUMN acknowledged_by TEXT;
  END IF;
END $$;


ALTER TABLE public.shift_handovers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own facility handovers" ON shift_handovers FOR SELECT USING (
  auth.uid()::text = user_id OR 
  acknowledged_by = auth.uid()::text
);

CREATE POLICY "Users can insert own handovers" ON shift_handovers FOR INSERT WITH CHECK (auth.uid()::text = user_id);

CREATE POLICY "Users can update own handovers" ON shift_handovers FOR UPDATE USING (auth.uid()::text = user_id);

-- Shift Events Table (logs all activity during shifts)
CREATE TABLE IF NOT EXISTS public.shift_events (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('QUERY', 'ASSET_ACCESS', 'WORK_ORDER', 'MAINTENANCE', 'INCIDENT', 'DOCUMENT_ADDED')),
  asset_id UUID REFERENCES public.user_assets(id) ON DELETE SET NULL,
  asset_name TEXT,
  description TEXT,
  severity TEXT DEFAULT 'INFO' CHECK (severity IN ('INFO', 'WARNING', 'CRITICAL')),
  shift_id UUID REFERENCES public.shift_handovers(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.shift_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own shift events" ON shift_events FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Users can insert own shift events" ON shift_events FOR INSERT WITH CHECK (auth.uid()::text = user_id);

-- ============================================================
-- FEATURE 4: TRIBAL KNOWLEDGE CAPTURE
-- ============================================================

-- Tribal Knowledge Table
CREATE TABLE IF NOT EXISTS public.tribal_knowledge (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT NOT NULL,
  facility_id TEXT,
  asset_id UUID REFERENCES public.user_assets(id) ON DELETE SET NULL,
  manual_id UUID REFERENCES public.user_manuals(id) ON DELETE SET NULL,
  page_reference INT,
  section TEXT,
  original_query TEXT,
  ai_answer_summary TEXT,
  technician_note TEXT NOT NULL,
  added_by_name TEXT NOT NULL,
  verified BOOLEAN DEFAULT FALSE,
  verified_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  verified_at TIMESTAMPTZ,
  helpful_count INT DEFAULT 0,
  voice_query BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.tribal_knowledge ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view tribal knowledge" ON tribal_knowledge FOR SELECT USING (true);

CREATE POLICY "Users can insert own tribal knowledge" ON tribal_knowledge FOR INSERT WITH CHECK (auth.uid()::text = user_id);

CREATE POLICY "Users can update own tribal knowledge" ON tribal_knowledge FOR UPDATE USING (auth.uid()::text = user_id);

CREATE POLICY "Supervisors can verify tribal knowledge" ON tribal_knowledge FOR UPDATE USING (
  EXISTS (
    SELECT 1 FROM public.profiles 
    WHERE id = auth.uid() AND role = 'admin'
  )
);

-- ============================================================
-- FEATURE 5: WORK ORDER GENERATION
-- ============================================================

-- Work Orders Table
CREATE TABLE IF NOT EXISTS public.work_orders (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT NOT NULL,
  facility_name TEXT NOT NULL,
  asset_id UUID REFERENCES public.user_assets(id) ON DELETE SET NULL,
  asset_name TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  priority TEXT DEFAULT 'MEDIUM' CHECK (priority IN ('HIGH', 'MEDIUM', 'LOW', 'CRITICAL')),
  status TEXT DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'IN_PROGRESS', 'COMPLETE', 'CANCELLED')),
  assigned_to TEXT,
  estimated_hours DECIMAL(5,2),
  linked_manual_id UUID REFERENCES public.user_manuals(id) ON DELETE SET NULL,
  linked_page INT,
  linked_tribal_knowledge_id UUID REFERENCES public.tribal_knowledge(id) ON DELETE SET NULL,
  created_from TEXT DEFAULT 'MANUAL' CHECK (created_from IN ('MANUAL', 'AI_SUGGESTION', 'MAINTENANCE_SCHEDULE', 'INCIDENT', 'QUERY')),
  due_date TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.work_orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own facility work orders" ON work_orders FOR SELECT USING (true);

CREATE POLICY "Users can insert own work orders" ON work_orders FOR INSERT WITH CHECK (auth.uid()::text = user_id);

CREATE POLICY "Users can update own work orders" ON work_orders FOR UPDATE USING (auth.uid()::text = user_id);

-- Add account_type to profiles for paywall checks
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'profiles' AND column_name = 'account_type') THEN
    ALTER TABLE public.profiles ADD COLUMN account_type TEXT DEFAULT 'sandbox' CHECK (account_type IN ('sandbox', 'enterprise'));
  END IF;
END $$;

-- Add facility_name to profiles
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'profiles' AND column_name = 'facility_name') THEN
    ALTER TABLE public.profiles ADD COLUMN facility_name TEXT DEFAULT 'Default Facility';
  END IF;
END $$;

-- ============================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_shift_handovers_user_id ON public.shift_handovers(user_id);
CREATE INDEX IF NOT EXISTS idx_shift_handovers_facility ON public.shift_handovers(facility_name);
CREATE INDEX IF NOT EXISTS idx_shift_handovers_created_at ON public.shift_handovers(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_shift_events_user_id ON public.shift_events(user_id);
CREATE INDEX IF NOT EXISTS idx_shift_events_asset_id ON public.shift_events(asset_id);
CREATE INDEX IF NOT EXISTS idx_shift_events_shift_id ON public.shift_events(shift_id);
CREATE INDEX IF NOT EXISTS idx_shift_events_created_at ON public.shift_events(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tribal_knowledge_asset_id ON public.tribal_knowledge(asset_id);
CREATE INDEX IF NOT EXISTS idx_tribal_knowledge_manual_id ON public.tribal_knowledge(manual_id);
CREATE INDEX IF NOT EXISTS idx_tribal_knowledge_verified ON public.tribal_knowledge(verified);
CREATE INDEX IF NOT EXISTS idx_tribal_knowledge_helpful_count ON public.tribal_knowledge(helpful_count DESC);

CREATE INDEX IF NOT EXISTS idx_work_orders_user_id ON public.work_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_work_orders_asset_id ON public.work_orders(asset_id);
CREATE INDEX IF NOT EXISTS idx_work_orders_status ON public.work_orders(status);
CREATE INDEX IF NOT EXISTS idx_work_orders_priority ON public.work_orders(priority);
CREATE INDEX IF NOT EXISTS idx_work_orders_created_at ON public.work_orders(created_at DESC);

-- ============================================================
-- DONE! New features database schema is ready.
-- ============================================================
