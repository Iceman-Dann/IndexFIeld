// =============================================
// SETUP WIZARD CHECK
// =============================================
async function checkSetupWizard() {
    try {
        const { data: { session } } = await supabaseClient.auth.getSession();
        if (!session) return;

        // Check if user has a facility
        const { data: profile } = await supabaseClient
            .from('profiles')
            .select('current_facility_id')
            .eq('id', session.user.id)
            .single();

        if (!profile || !profile.current_facility_id) {
            // No facility - redirect to wizard
            window.location.href = 'setup-wizard.html';
            return;
        }

        // Check if facility setup is complete
        const { data: facility } = await supabaseClient
            .from('facilities')
            .select('setup_complete')
            .eq('id', profile.current_facility_id)
            .single();

        if (!facility || !facility.setup_complete) {
            // Setup not complete - redirect to wizard
            window.location.href = 'setup-wizard.html';
        }
    } catch (e) {
        console.warn('Setup wizard check failed:', e);
        // Don't block the dashboard if check fails
    }
}