/**
 * Apollo.io Lead Scraper - Main JavaScript Application
 * Handles form interactions, progress monitoring, and UI updates
 */

// Global application state
const ApolloScraperApp = {
    currentJobId: null,
    progressInterval: null,
    config: {
        progressUpdateInterval: 2000, // 2 seconds
        alertAutoHideDelay: 5000 // 5 seconds
    }
};

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    setupEventListeners();
    initializeTooltips();
    updateDailyUsageDisplay();
    
    // Auto-refresh running jobs on dashboard
    if (window.location.pathname === '/dashboard') {
        startDashboardAutoRefresh();
    }
}

/**
 * Setup all event listeners
 */
function setupEventListeners() {
    // Main scraping form
    const scrapingForm = document.getElementById('scraping-form');
    if (scrapingForm) {
        scrapingForm.addEventListener('submit', handleScrapingFormSubmit);
        
        // Update estimated time when settings change
        const maxResultsInput = document.getElementById('max_results');
        const delayInput = document.getElementById('delay');
        
        if (maxResultsInput && delayInput) {
            maxResultsInput.addEventListener('input', updateEstimatedTime);
            delayInput.addEventListener('input', updateEstimatedTime);
            updateEstimatedTime(); // Initial calculation
        }
    }
    
    // Authentication test button
    const testAuthBtn = document.getElementById('test-auth-btn');
    if (testAuthBtn) {
        testAuthBtn.addEventListener('click', handleAuthenticationTest);
    }
    
    // Cancel job button
    const cancelJobBtn = document.getElementById('cancel-job-btn');
    if (cancelJobBtn) {
        cancelJobBtn.addEventListener('click', handleJobCancellation);
    }
    
    // Progress modal close event
    const progressModal = document.getElementById('progressModal');
    if (progressModal) {
        progressModal.addEventListener('hidden.bs.modal', function() {
            if (ApolloScraperApp.progressInterval) {
                clearInterval(ApolloScraperApp.progressInterval);
                ApolloScraperApp.progressInterval = null;
            }
        });
    }
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Handle scraping form submission
 */
function handleScrapingFormSubmit(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    const submitBtn = document.getElementById('start-scraping-btn');
    
    // Validate form
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    // Show loading state
    setButtonLoadingState(submitBtn, 'Starting...');
    
    // Submit form
    fetch('/start_scraping', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            ApolloScraperApp.currentJobId = data.job_id;
            showProgressModal(data);
            startProgressMonitoring(data.job_id);
            showAlert(`Scraping job started successfully! Estimated completion: ${data.estimated_time}`, 'success');
        } else {
            showAlert(`Error: ${data.error}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error starting scraping job:', error);
        showAlert(`Failed to start scraping: ${error.message}`, 'danger');
    })
    .finally(() => {
        resetButtonState(submitBtn, '<i class="bi bi-play-circle me-2"></i>Start Scraping');
    });
}

/**
 * Handle authentication test
 */
function handleAuthenticationTest(event) {
    const button = event.target;
    const cookiesTextarea = document.getElementById('cookies');
    const cookies = cookiesTextarea.value.trim();
    
    if (!cookies) {
        showAlert('Please enter cookies to test authentication', 'warning');
        cookiesTextarea.focus();
        return;
    }
    
    setButtonLoadingState(button, 'Testing...');
    
    fetch('/test_auth', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `cookies=${encodeURIComponent(cookies)}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('✓ Authentication successful! You can now start scraping.', 'success');
        } else {
            showAlert(`✗ Authentication failed: ${data.message}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Authentication test error:', error);
        showAlert(`Authentication test failed: ${error.message}`, 'danger');
    })
    .finally(() => {
        resetButtonState(button, '<i class="bi bi-check-circle me-1"></i>Test Authentication');
    });
}

/**
 * Handle job cancellation
 */
function handleJobCancellation() {
    if (!ApolloScraperApp.currentJobId) {
        showAlert('No active job to cancel', 'warning');
        return;
    }
    
    if (!confirm('Are you sure you want to cancel this job? This action cannot be undone.')) {
        return;
    }
    
    fetch(`/cancel_job/${ApolloScraperApp.currentJobId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Job cancelled successfully', 'info');
            if (ApolloScraperApp.progressInterval) {
                clearInterval(ApolloScraperApp.progressInterval);
                ApolloScraperApp.progressInterval = null;
            }
        } else {
            showAlert(`Error cancelling job: ${data.error}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error cancelling job:', error);
        showAlert(`Failed to cancel job: ${error.message}`, 'danger');
    });
}

/**
 * Show progress modal with initial data
 */
function showProgressModal(jobData) {
    const modal = document.getElementById('progressModal');
    if (!modal) return;
    
    // Update modal content
    document.getElementById('job-id').textContent = jobData.job_id;
    document.getElementById('job-status').textContent = 'Starting...';
    document.getElementById('progress-percentage').textContent = '0%';
    document.getElementById('progress-bar').style.width = '0%';
    document.getElementById('scraped-count').textContent = '0';
    document.getElementById('total-count').textContent = '0';
    
    // Remove any existing download button
    const existingDownloadBtn = document.getElementById('download-csv-btn');
    if (existingDownloadBtn) {
        existingDownloadBtn.remove();
    }
    
    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

/**
 * Start monitoring progress for a job
 */
function startProgressMonitoring(jobId) {
    if (ApolloScraperApp.progressInterval) {
        clearInterval(ApolloScraperApp.progressInterval);
    }
    
    ApolloScraperApp.progressInterval = setInterval(() => {
        updateJobProgress(jobId);
    }, ApolloScraperApp.config.progressUpdateInterval);
    
    // Initial update
    updateJobProgress(jobId);
}

/**
 * Update job progress display
 */
function updateJobProgress(jobId) {
    fetch(`/job_status/${jobId}`)
    .then(response => response.json())
    .then(data => {
        updateProgressDisplay(data);
        
        // Check if job is completed or failed
        if (data.status === 'completed') {
            handleJobCompletion(data);
        } else if (data.status === 'failed') {
            handleJobFailure(data);
        }
    })
    .catch(error => {
        console.error('Error updating job progress:', error);
    });
}

/**
 * Update the progress display elements
 */
function updateProgressDisplay(jobData) {
    const progress = jobData.progress || 0;
    const scrapedLeads = jobData.scraped_leads || 0;
    const totalLeads = jobData.total_leads || 0;
    const status = jobData.status || 'unknown';
    
    // Update progress elements
    const progressPercentage = document.getElementById('progress-percentage');
    const progressBar = document.getElementById('progress-bar');
    const scrapedCount = document.getElementById('scraped-count');
    const totalCount = document.getElementById('total-count');
    const jobStatus = document.getElementById('job-status');
    
    if (progressPercentage) progressPercentage.textContent = `${progress.toFixed(1)}%`;
    if (progressBar) progressBar.style.width = `${progress}%`;
    if (scrapedCount) scrapedCount.textContent = scrapedLeads.toLocaleString();
    if (totalCount) totalCount.textContent = totalLeads.toLocaleString();
    if (jobStatus) jobStatus.textContent = status.charAt(0).toUpperCase() + status.slice(1);
}

/**
 * Handle job completion
 */
function handleJobCompletion(jobData) {
    // Stop progress monitoring
    if (ApolloScraperApp.progressInterval) {
        clearInterval(ApolloScraperApp.progressInterval);
        ApolloScraperApp.progressInterval = null;
    }
    
    const scrapedLeads = jobData.scraped_leads || 0;
    showAlert(`🎉 Scraping completed successfully! ${scrapedLeads.toLocaleString()} leads extracted.`, 'success');
    
    // Add download button to progress modal
    addDownloadButtonToModal(jobData.id);
    
    // Update daily usage
    updateDailyUsageDisplay();
}

/**
 * Handle job failure
 */
function handleJobFailure(jobData) {
    // Stop progress monitoring
    if (ApolloScraperApp.progressInterval) {
        clearInterval(ApolloScraperApp.progressInterval);
        ApolloScraperApp.progressInterval = null;
    }
    
    const errorMessage = jobData.error_message || 'Unknown error occurred';
    showAlert(`❌ Scraping failed: ${errorMessage}`, 'danger');
}

/**
 * Add download button to progress modal
 */
function addDownloadButtonToModal(jobId) {
    const modalFooter = document.querySelector('#progressModal .modal-footer');
    if (!modalFooter || document.getElementById('download-csv-btn')) return;
    
    const downloadBtn = document.createElement('button');
    downloadBtn.id = 'download-csv-btn';
    downloadBtn.className = 'btn btn-success';
    downloadBtn.innerHTML = '<i class="bi bi-download me-2"></i>Download CSV';
    downloadBtn.onclick = () => downloadCSV(jobId);
    
    modalFooter.insertBefore(downloadBtn, modalFooter.firstChild);
}

/**
 * Download CSV file for a job
 */
function downloadCSV(jobId) {
    window.open(`/download_csv/${jobId}`, '_blank');
}

/**
 * Update estimated time based on current settings
 */
function updateEstimatedTime() {
    const maxResultsInput = document.getElementById('max_results');
    const delayInput = document.getElementById('delay');
    const estimatedTimeSpan = document.getElementById('estimated-time');
    
    if (!maxResultsInput || !delayInput || !estimatedTimeSpan) return;
    
    const maxResults = parseInt(maxResultsInput.value) || 1000;
    const delay = parseInt(delayInput.value) || 10;
    
    // Estimate: ~25 results per page, with delay between page requests
    const estimatedPages = Math.ceil(maxResults / 25);
    const totalSeconds = estimatedPages * delay;
    
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    
    let timeString = '';
    if (hours > 0) {
        timeString = `~${hours}h ${minutes}m`;
    } else {
        timeString = `~${minutes}m`;
    }
    
    estimatedTimeSpan.textContent = timeString;
}

/**
 * Update daily usage display
 */
function updateDailyUsageDisplay() {
    fetch('/daily_stats')
    .then(response => response.json())
    .then(data => {
        // Update navbar badge
        const dailyLeadsCount = document.getElementById('daily-leads-count');
        if (dailyLeadsCount) {
            dailyLeadsCount.textContent = data.leads_scraped.toLocaleString();
        }
        
        // Update any progress bars
        const progressBars = document.querySelectorAll('.daily-usage-progress');
        progressBars.forEach(bar => {
            const type = bar.dataset.type;
            if (type === 'leads') {
                const percentage = (data.leads_scraped / data.limits.max_daily_leads) * 100;
                bar.style.width = `${Math.min(percentage, 100)}%`;
            } else if (type === 'requests') {
                const percentage = (data.requests_made / data.limits.max_daily_requests) * 100;
                bar.style.width = `${Math.min(percentage, 100)}%`;
            }
        });
    })
    .catch(error => {
        console.error('Error updating daily usage:', error);
    });
}

/**
 * Start auto-refresh for dashboard
 */
function startDashboardAutoRefresh() {
    setInterval(() => {
        const runningJobs = document.querySelectorAll('.job-row[data-status="running"]');
        if (runningJobs.length > 0) {
            // Only refresh if there are running jobs
            location.reload();
        }
    }, 30000); // 30 seconds
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    const alertContainer = document.querySelector('main .container');
    if (!alertContainer) return;
    
    const alertId = `alert-${Date.now()}`;
    const alertDiv = document.createElement('div');
    alertDiv.id = alertId;
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <div class="d-flex align-items-center">
            <div class="me-2">
                ${getAlertIcon(type)}
            </div>
            <div class="flex-grow-1">${message}</div>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    // Insert at the top of the container
    alertContainer.insertBefore(alertDiv, alertContainer.firstChild);
    
    // Auto-hide after delay
    setTimeout(() => {
        const alert = document.getElementById(alertId);
        if (alert && alert.parentNode) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }
    }, ApolloScraperApp.config.alertAutoHideDelay);
}

/**
 * Get appropriate icon for alert type
 */
function getAlertIcon(type) {
    const icons = {
        'success': '<i class="bi bi-check-circle-fill"></i>',
        'danger': '<i class="bi bi-exclamation-triangle-fill"></i>',
        'warning': '<i class="bi bi-exclamation-circle-fill"></i>',
        'info': '<i class="bi bi-info-circle-fill"></i>'
    };
    return icons[type] || icons['info'];
}

/**
 * Set button to loading state
 */
function setButtonLoadingState(button, loadingText) {
    if (!button) return;
    
    button.dataset.originalText = button.innerHTML;
    button.innerHTML = `<i class="bi bi-arrow-clockwise spin me-2"></i>${loadingText}`;
    button.disabled = true;
}

/**
 * Reset button to normal state
 */
function resetButtonState(button, originalText = null) {
    if (!button) return;
    
    const textToUse = originalText || button.dataset.originalText || button.innerHTML;
    button.innerHTML = textToUse;
    button.disabled = false;
}

/**
 * Format number with commas
 */
function formatNumber(num) {
    return num.toLocaleString();
}

/**
 * Format date/time string
 */
function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleString();
    } catch (error) {
        console.error('Error formatting date:', error);
        return dateString;
    }
}

/**
 * Validate Apollo URL format
 */
function validateApolloUrl(url) {
    try {
        const urlObj = new URL(url);
        return urlObj.hostname.includes('apollo.io') && 
               (url.includes('#/people') || url.includes('/people'));
    } catch (error) {
        return false;
    }
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showAlert('Copied to clipboard', 'success');
        }).catch(error => {
            console.error('Error copying to clipboard:', error);
            showAlert('Failed to copy to clipboard', 'danger');
        });
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showAlert('Copied to clipboard', 'success');
    }
}

// Export for use in inline scripts
window.ApolloScraperApp = ApolloScraperApp;
window.showAlert = showAlert;
window.downloadCSV = downloadCSV;
window.copyToClipboard = copyToClipboard;
window.formatDateTime = formatDateTime;
window.formatNumber = formatNumber;
