-- Add missing fields to work_orders table
ALTER TABLE work_orders 
ADD COLUMN IF NOT EXISTS procedure_steps JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS ai_briefing JSONB,
ADD COLUMN IF NOT EXISTS ai_briefed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

-- Add ai_suggestion_count to profiles table for paywall tracking
ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS ai_suggestion_count INTEGER DEFAULT 0;

-- Create index on work_orders for faster queries
CREATE INDEX IF NOT EXISTS idx_work_orders_user_id ON work_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_work_orders_status ON work_orders(status);
CREATE INDEX IF NOT EXISTS idx_work_orders_priority ON work_orders(priority);
CREATE INDEX IF NOT EXISTS idx_work_orders_due_date ON work_orders(due_date);
