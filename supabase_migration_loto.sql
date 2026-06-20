-- ============================================================
-- IndexField Lockout / Tagout Database Migration
-- Run this in Supabase SQL Editor to set up LOTO permitting
-- ============================================================

CREATE TABLE IF NOT EXISTS public.loto_permits (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  facility_id UUID NOT NULL,
  asset_id UUID NOT NULL,
  asset_name TEXT NOT NULL,
  initiated_by TEXT NOT NULL,
  initiated_at TIMESTAMPTZ DEFAULT NOW(),
  procedure_source TEXT NOT NULL,
  procedure_content JSONB DEFAULT '{}'::jsonb,
  additional_technicians TEXT[] DEFAULT '{}'::text[],
  work_description TEXT NOT NULL,
  estimated_duration TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'RELEASED', 'INCOMPLETE')),
  steps_completed JSONB DEFAULT '{}'::jsonb,
  energy_verifications JSONB DEFAULT '{}'::jsonb,
  safe_entry_authorized_by TEXT,
  safe_entry_authorized_at TIMESTAMPTZ,
  released_by TEXT,
  released_at TIMESTAMPTZ,
  release_checklist JSONB DEFAULT '{}'::jsonb,
  release_notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.loto_permits ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view permits for their facility" ON public.loto_permits
  FOR SELECT USING (true);

CREATE POLICY "Users can insert permits for their facility" ON public.loto_permits
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Users can update permits for their facility" ON public.loto_permits
  FOR UPDATE USING (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_loto_permits_facility_id ON public.loto_permits(facility_id);
CREATE INDEX IF NOT EXISTS idx_loto_permits_asset_id ON public.loto_permits(asset_id);
CREATE INDEX IF NOT EXISTS idx_loto_permits_status ON public.loto_permits(status);
