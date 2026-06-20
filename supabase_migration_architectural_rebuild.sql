-- ============================================================
-- IndexField Architectural Rebuild Migration
-- Complete database restructure for facility-based multi-tenancy
-- Run this ENTIRE script in the Supabase SQL Editor
-- ============================================================

-- ============================================================
-- STEP 1: Create new tables for facility-based architecture
-- ============================================================

-- FACILITIES TABLE
CREATE TABLE IF NOT EXISTS public.facilities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  location TEXT,
  industry TEXT,
  technician_count INTEGER DEFAULT 1,
  critical_asset TEXT,
  modules_selected TEXT[] DEFAULT '{}',
  priorities TEXT[] DEFAULT '{}',
  primary_equipment TEXT,
  account_type TEXT DEFAULT 'sandbox',
  query_count INTEGER DEFAULT 0,
  session_expires_at TIMESTAMPTZ,
  converted BOOLEAN DEFAULT false,
  converted_at TIMESTAMPTZ,
  health_score INTEGER DEFAULT 0,
  owner_id UUID REFERENCES auth.users(id),
  waitlist_joined BOOLEAN DEFAULT false,
  emails_sent TEXT[] DEFAULT '{}',
  last_email_sent_at TIMESTAMPTZ,
  setup_complete BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- FACILITY_MEMBERS TABLE
CREATE TABLE IF NOT EXISTS public.facility_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id UUID REFERENCES facilities(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id),
  role TEXT NOT NULL DEFAULT 'technician',
  invited_by UUID REFERENCES auth.users(id),
  invite_email TEXT,
  invite_token TEXT UNIQUE,
  status TEXT DEFAULT 'active',
  expires_at TIMESTAMPTZ,
  joined_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- PROFILES TABLE (update if exists)
CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name TEXT,
  email TEXT,
  company_name TEXT,
  current_facility_id UUID REFERENCES facilities(id),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- INCIDENTS TABLE
CREATE TABLE IF NOT EXISTS public.incidents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id UUID REFERENCES facilities(id),
  user_id UUID REFERENCES auth.users(id),
  reported_by_name TEXT,
  asset_id UUID,
  asset_name TEXT,
  title TEXT NOT NULL,
  description TEXT,
  severity TEXT DEFAULT 'medium',
  status TEXT DEFAULT 'open',
  ai_response JSONB,
  ai_briefed BOOLEAN DEFAULT false,
  loto_initiated BOOLEAN DEFAULT false,
  work_order_id UUID,
  resolution_notes TEXT,
  compliance_report_generated BOOLEAN DEFAULT false,
  timeline JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT now(),
  resolved_at TIMESTAMPTZ
);

-- WAITLIST TABLE
CREATE TABLE IF NOT EXISTS public.waitlist (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  full_name TEXT,
  company_name TEXT,
  facility_name TEXT,
  industry TEXT,
  critical_asset TEXT,
  query_count_at_signup INTEGER DEFAULT 0,
  document_uploaded BOOLEAN DEFAULT false,
  source TEXT,
  joined_at TIMESTAMPTZ DEFAULT now(),
  contacted BOOLEAN DEFAULT false
);

-- IP_SESSIONS TABLE
CREATE TABLE IF NOT EXISTS public.ip_sessions (
  ip_address TEXT PRIMARY KEY,
  session_count INTEGER DEFAULT 0,
  last_session_at TIMESTAMPTZ DEFAULT now()
);

-- SHIFT_EVENTS TABLE
CREATE TABLE IF NOT EXISTS public.shift_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id UUID REFERENCES facilities(id),
  user_id UUID REFERENCES auth.users(id),
  event_type TEXT,
  description TEXT,
  asset_id UUID,
  severity TEXT,
  ai_analysis JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- SHIFT_HANDOVERS TABLE
CREATE TABLE IF NOT EXISTS public.shift_handovers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id UUID REFERENCES facilities(id),
  shift_type TEXT,
  generated_by UUID REFERENCES auth.users(id),
  report_content JSONB,
  acknowledged BOOLEAN DEFAULT false,
  acknowledged_by UUID REFERENCES auth.users(id),
  acknowledged_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- WORK_ORDERS TABLE (update if exists)
CREATE TABLE IF NOT EXISTS public.work_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id UUID REFERENCES facilities(id),
  user_id UUID REFERENCES auth.users(id),
  asset_id UUID,
  title TEXT NOT NULL,
  description TEXT,
  priority TEXT DEFAULT 'medium',
  status TEXT DEFAULT 'open',
  assigned_to UUID REFERENCES auth.users(id),
  due_date TIMESTAMPTZ,
  ai_briefing JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- DOCUMENTS TABLE (rename from user_manuals)
CREATE TABLE IF NOT EXISTS public.documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id UUID REFERENCES facilities(id),
  user_id UUID REFERENCES auth.users(id),
  filename TEXT NOT NULL,
  file_hash TEXT,
  backend_id TEXT,
  asset_type TEXT DEFAULT 'Industrial Equipment',
  status TEXT DEFAULT 'processing',
  page_count INTEGER DEFAULT 0,
  section_count INTEGER DEFAULT 0,
  chunk_count INTEGER DEFAULT 0,
  file_size_bytes BIGINT DEFAULT 0,
  maintenance_intervals JSONB DEFAULT '[]',
  compliance_refs JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- USER_ASSETS TABLE (update with facility_id)
CREATE TABLE IF NOT EXISTS public.user_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id UUID REFERENCES facilities(id),
  user_id UUID REFERENCES auth.users(id),
  asset_code TEXT NOT NULL,
  name TEXT NOT NULL,
  model TEXT DEFAULT '',
  location TEXT DEFAULT '',
  status TEXT DEFAULT 'online' CHECK (status IN ('online', 'offline', 'warning', 'maintenance')),
  serial_number TEXT DEFAULT '',
  last_maint TIMESTAMPTZ,
  next_maint TIMESTAMPTZ,
  assigned_technician UUID REFERENCES auth.users(id),
  qr_token TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- QUERY_HISTORY TABLE
CREATE TABLE IF NOT EXISTS public.query_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id UUID REFERENCES facilities(id),
  user_id UUID REFERENCES auth.users(id),
  query TEXT NOT NULL,
  response TEXT,
  sources JSONB,
  document_ids TEXT[],
  created_at TIMESTAMPTZ DEFAULT now()
);

-- TRIBAL_KNOWLEDGE TABLE (rename from knowledge_posts)
CREATE TABLE IF NOT EXISTS public.tribal_knowledge (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id UUID REFERENCES facilities(id),
  user_id UUID REFERENCES auth.users(id),
  author_name TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  asset_code TEXT,
  likes INTEGER DEFAULT 0,
  verified BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- MAINTENANCE_ITEMS TABLE
CREATE TABLE IF NOT EXISTS public.maintenance_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id UUID REFERENCES facilities(id),
  asset_id UUID,
  task_name TEXT NOT NULL,
  interval TEXT,
  due_date TIMESTAMPTZ,
  last_completed TIMESTAMPTZ,
  source_document_id UUID,
  source_page INTEGER,
  assigned_technician UUID REFERENCES auth.users(id),
  status TEXT DEFAULT 'pending',
  compliance_standard TEXT,
  compliance_consequence TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- STEP 2: Add facility_id to existing tables that need it
-- ============================================================

-- Add facility_id to user_assets if not exists
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_assets' AND column_name = 'facility_id') THEN
    ALTER TABLE public.user_assets ADD COLUMN facility_id UUID REFERENCES facilities(id);
  END IF;
END $$;

-- Add facility_id to documents if not exists (using user_manuals as base)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_manuals') THEN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_manuals' AND column_name = 'facility_id') THEN
      ALTER TABLE public.user_manuals ADD COLUMN facility_id UUID REFERENCES facilities(id);
    END IF;
  END IF;
END $$;

-- Add facility_id to work_orders if not exists
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'work_orders' AND column_name = 'facility_id') THEN
    ALTER TABLE public.work_orders ADD COLUMN facility_id UUID REFERENCES facilities(id);
  END IF;
END $$;

-- Add facility_id to tribal_knowledge if not exists (using knowledge_posts as base)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'knowledge_posts') THEN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'knowledge_posts' AND column_name = 'facility_id') THEN
      ALTER TABLE public.knowledge_posts ADD COLUMN facility_id UUID REFERENCES facilities(id);
    END IF;
  END IF;
END $$;

-- Add facility_id to shift_handovers if not exists
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'shift_handovers' AND column_name = 'facility_id') THEN
    ALTER TABLE public.shift_handovers ADD COLUMN facility_id UUID REFERENCES facilities(id);
  END IF;
END $$;

-- Add facility_id to incidents if not exists
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'incidents' AND column_name = 'facility_id') THEN
    ALTER TABLE public.incidents ADD COLUMN facility_id UUID REFERENCES facilities(id);
  END IF;
END $$;

-- Add facility_id to query_history if not exists
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'query_history' AND column_name = 'facility_id') THEN
    ALTER TABLE public.query_history ADD COLUMN facility_id UUID REFERENCES facilities(id);
  END IF;
END $$;

-- Add facility_id to maintenance_items if not exists
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'maintenance_items' AND column_name = 'facility_id') THEN
    ALTER TABLE public.maintenance_items ADD COLUMN facility_id UUID REFERENCES facilities(id);
  END IF;
END $$;

-- ============================================================
-- STEP 3: Enable RLS on all tables
-- ============================================================

ALTER TABLE public.facilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.facility_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.waitlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ip_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shift_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shift_handovers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.work_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.query_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tribal_knowledge ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.maintenance_items ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- STEP 4: Create RLS Policies
-- ============================================================

-- FACILITIES POLICIES
DO $$
BEGIN
  -- Users can SELECT their own facility if they are in facility_members
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'facilities' AND policyname = 'Users can view their facility') THEN
    CREATE POLICY "Users can view their facility" ON facilities 
    FOR SELECT USING (
      id IN (SELECT facility_id FROM facility_members WHERE user_id = auth.uid() AND status = 'active')
    );
  END IF;
  
  -- Users can UPDATE their facility if their role is owner
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'facilities' AND policyname = 'Owners can update facility') THEN
    CREATE POLICY "Owners can update facility" ON facilities 
    FOR UPDATE USING (
      id IN (SELECT facility_id FROM facility_members WHERE user_id = auth.uid() AND role = 'owner' AND status = 'active')
    );
  END IF;
  
  -- Service role bypasses all RLS
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'facilities' AND policyname = 'Service role can manage facilities') THEN
    CREATE POLICY "Service role can manage facilities" ON facilities 
    FOR ALL USING (auth.role() = 'service_role');
  END IF;
END $$;

-- FACILITY_MEMBERS POLICIES
DO $$
BEGIN
  -- Users can SELECT members of facilities they belong to
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'facility_members' AND policyname = 'Users can view facility members') THEN
    CREATE POLICY "Users can view facility members" ON facility_members 
    FOR SELECT USING (
      facility_id IN (SELECT facility_id FROM facility_members WHERE user_id = auth.uid() AND status = 'active')
    );
  END IF;
  
  -- Only owners can INSERT members
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'facility_members' AND policyname = 'Owners can insert members') THEN
    CREATE POLICY "Owners can insert members" ON facility_members 
    FOR INSERT WITH CHECK (
      facility_id IN (SELECT facility_id FROM facility_members WHERE user_id = auth.uid() AND role = 'owner' AND status = 'active')
    );
  END IF;
  
  -- Only owners can DELETE members
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'facility_members' AND policyname = 'Owners can delete members') THEN
    CREATE POLICY "Owners can delete members" ON facility_members 
    FOR DELETE USING (
      facility_id IN (SELECT facility_id FROM facility_members WHERE user_id = auth.uid() AND role = 'owner' AND status = 'active')
    );
  END IF;
  
  -- Service role bypasses all RLS
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'facility_members' AND policyname = 'Service role can manage members') THEN
    CREATE POLICY "Service role can manage members" ON facility_members 
    FOR ALL USING (auth.role() = 'service_role');
  END IF;
END $$;

-- PROFILES POLICIES
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'profiles' AND policyname = 'Users can view own profile') THEN
    CREATE POLICY "Users can view own profile" ON profiles FOR SELECT USING (auth.uid() = id);
  END IF;
  
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'profiles' AND policyname = 'Users can update own profile') THEN
    CREATE POLICY "Users can update own profile" ON profiles FOR UPDATE USING (auth.uid() = id);
  END IF;
  
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'profiles' AND policyname = 'Users can insert own profile') THEN
    CREATE POLICY "Users can insert own profile" ON profiles FOR INSERT WITH CHECK (auth.uid() = id);
  END IF;
  
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'profiles' AND policyname = 'Service role can manage profiles') THEN
    CREATE POLICY "Service role can manage profiles" ON profiles 
    FOR ALL USING (auth.role() = 'service_role');
  END IF;
END $$;

-- GENERIC FACILITY-BASED POLICIES (for all data tables)
-- These policies apply to: incidents, shift_events, shift_handovers, work_orders, documents, user_assets, query_history, tribal_knowledge, maintenance_items

DO $$
DECLARE
  table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY['incidents', 'shift_events', 'shift_handovers', 'work_orders', 'documents', 'user_assets', 'query_history', 'tribal_knowledge', 'maintenance_items']
  LOOP
    -- Users can SELECT records from their facility
    EXECUTE format('
      CREATE POLICY "Users can view %s" ON %I
      FOR SELECT USING (
        facility_id IN (SELECT current_facility_id FROM profiles WHERE id = auth.uid())
      )
    ', table_name, table_name);
    
    -- Users can INSERT records for their facility
    EXECUTE format('
      CREATE POLICY "Users can insert %s" ON %I
      FOR INSERT WITH CHECK (
        facility_id IN (SELECT current_facility_id FROM profiles WHERE id = auth.uid())
      )
    ', table_name, table_name);
    
    -- Users can UPDATE records in their facility
    EXECUTE format('
      CREATE POLICY "Users can update %s" ON %I
      FOR UPDATE USING (
        facility_id IN (SELECT current_facility_id FROM profiles WHERE id = auth.uid())
      )
    ', table_name, table_name);
    
    -- Only owners and supervisors can DELETE
    EXECUTE format('
      CREATE POLICY "Owners and supervisors can delete %s" ON %I
      FOR DELETE USING (
        facility_id IN (
          SELECT fm.facility_id FROM facility_members fm
          WHERE fm.user_id = auth.uid() 
          AND fm.facility_id = %I.facility_id
          AND fm.status = ''active''
          AND fm.role IN (''owner'', ''supervisor'')
        )
      )
    ', table_name, table_name, table_name);
    
    -- Service role bypasses all RLS
    EXECUTE format('
      CREATE POLICY "Service role can manage %s" ON %I
      FOR ALL USING (auth.role() = ''service_role'')
    ', table_name, table_name);
  END LOOP;
END $$;

-- WAITLIST POLICIES (public insert, service role all)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'waitlist' AND policyname = 'Public can insert waitlist') THEN
    CREATE POLICY "Public can insert waitlist" ON waitlist FOR INSERT WITH CHECK (true);
  END IF;
  
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'waitlist' AND policyname = 'Service role can manage waitlist') THEN
    CREATE POLICY "Service role can manage waitlist" ON waitlist FOR ALL USING (auth.role() = 'service_role');
  END IF;
END $$;

-- IP_SESSIONS POLICIES (public insert/update, service role all)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'ip_sessions' AND policyname = 'Public can insert ip_sessions') THEN
    CREATE POLICY "Public can insert ip_sessions" ON ip_sessions FOR INSERT WITH CHECK (true);
  END IF;
  
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'ip_sessions' AND policyname = 'Public can update ip_sessions') THEN
    CREATE POLICY "Public can update ip_sessions" ON ip_sessions FOR UPDATE WITH CHECK (true);
  END IF;
  
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'ip_sessions' AND policyname = 'Service role can manage ip_sessions') THEN
    CREATE POLICY "Service role can manage ip_sessions" ON ip_sessions FOR ALL USING (auth.role() = 'service_role');
  END IF;
END $$;

-- ============================================================
-- STEP 5: Create indexes for performance
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_facilities_owner_id ON public.facilities(owner_id);
CREATE INDEX IF NOT EXISTS idx_facilities_account_type ON public.facilities(account_type);
CREATE INDEX IF NOT EXISTS idx_facility_members_facility_id ON public.facility_members(facility_id);
CREATE INDEX IF NOT EXISTS idx_facility_members_user_id ON public.facility_members(user_id);
CREATE INDEX IF NOT EXISTS idx_facility_members_invite_token ON public.facility_members(invite_token);
CREATE INDEX IF NOT EXISTS idx_profiles_current_facility_id ON public.profiles(current_facility_id);
CREATE INDEX IF NOT EXISTS idx_incidents_facility_id ON public.incidents(facility_id);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON public.incidents(status);
CREATE INDEX IF NOT EXISTS idx_shift_events_facility_id ON public.shift_events(facility_id);
CREATE INDEX IF NOT EXISTS idx_shift_handovers_facility_id ON public.shift_handovers(facility_id);
CREATE INDEX IF NOT EXISTS idx_work_orders_facility_id ON public.work_orders(facility_id);
CREATE INDEX IF NOT EXISTS idx_work_orders_assigned_to ON public.work_orders(assigned_to);
CREATE INDEX IF NOT EXISTS idx_documents_facility_id ON public.documents(facility_id);
CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON public.documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_user_assets_facility_id ON public.user_assets(facility_id);
CREATE INDEX IF NOT EXISTS idx_user_assets_qr_token ON public.user_assets(qr_token);
CREATE INDEX IF NOT EXISTS idx_query_history_facility_id ON public.query_history(facility_id);
CREATE INDEX IF NOT EXISTS idx_tribal_knowledge_facility_id ON public.tribal_knowledge(facility_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_items_facility_id ON public.maintenance_items(facility_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_items_due_date ON public.maintenance_items(due_date);

-- ============================================================
-- STEP 6: Create functions and triggers
-- ============================================================

-- Function to auto-generate qr_token for assets
CREATE OR REPLACE FUNCTION public.generate_qr_token()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.qr_token IS NULL OR NEW.qr_token = '' THEN
    NEW.qr_token := encode(gen_random_bytes(16), 'hex');
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-generate qr_token on insert
DROP TRIGGER IF EXISTS on_user_asset_insert ON public.user_assets;
CREATE TRIGGER on_user_asset_insert
  BEFORE INSERT ON public.user_assets
  FOR EACH ROW
  EXECUTE FUNCTION public.generate_qr_token();

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add updated_at triggers to relevant tables
DROP TRIGGER IF EXISTS update_profiles_updated_at ON public.profiles;
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON public.profiles
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_work_orders_updated_at ON public.work_orders;
CREATE TRIGGER update_work_orders_updated_at BEFORE UPDATE ON public.work_orders
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- ============================================================
-- STEP 7: Grant necessary permissions
-- ============================================================

-- Grant usage on uuid generation
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON SCHEMA public TO service_role;

-- Grant select on all tables for authenticated users
GRANT SELECT ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT INSERT ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT UPDATE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT DELETE ON ALL TABLES IN SCHEMA public TO authenticated;

-- Grant all permissions to service role
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO service_role;

-- ============================================================
-- MIGRATION COMPLETE
-- ============================================================
