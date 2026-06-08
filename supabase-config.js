// =============================================
// IndexField — Supabase Configuration
// =============================================
// INSTRUCTIONS:
// 1. Go to https://supabase.com and create a project
// 2. Go to Settings > API in your Supabase dashboard
// 3. Replace the values below with your actual keys
// =============================================

const SUPABASE_URL = 'https://bosexeozaaejrfljwcqt.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJvc2V4ZW96YWFlanJmbGp3Y3F0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2MTc3NzUsImV4cCI6MjA5NDE5Mzc3NX0.Crpns4oPIe5uKqPmgYsFRTQ1fJgRfON3JcRhfA3qZZU';

// Initialize the Supabase client (shared across all pages)
window.supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
