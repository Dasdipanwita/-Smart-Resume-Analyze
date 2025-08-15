// Custom JavaScript for Resume Analyzer App

// Function to be called when the page loads
function initializeApp() {
    // Add event listeners and initialize components
    addUploadAreaEffects();
    enhanceUIComponents();
}

// Add visual effects to the upload area
function addUploadAreaEffects() {
    // This will be injected via Streamlit components
    const uploadAreaCode = `
        const uploadArea = document.querySelector('.upload-area');
        if (uploadArea) {
            uploadArea.addEventListener('dragover', function() {
                this.style.backgroundColor = '#e6f2ff'; // Slightly darker light blue
                this.style.borderColor = '#c0392b'; // Darker red
            });
            
            uploadArea.addEventListener('dragleave', function() {
                this.style.backgroundColor = '#f0f8ff'; // Very light blue
                this.style.borderColor = '#e74c3c'; // Red
            });
            
            uploadArea.addEventListener('drop', function() {
                this.style.backgroundColor = '#f0f8ff'; // Very light blue
                this.style.borderColor = '#e74c3c'; // Red
            });
        }
    `;
    
    // Return the code to be injected
    return uploadAreaCode;
}

// Enhance various UI components
function enhanceUIComponents() {
    // This will be injected via Streamlit components
    const enhanceUICode = `
        // Apply red text to file uploader elements
        const fileUploaderTexts = document.querySelectorAll('.stFileUploader p, .stFileUploader span, .stFileUploader label, .stFileUploader button');
        fileUploaderTexts.forEach(element => {
            element.style.color = '#e74c3c';
            element.style.fontWeight = 'bold';
        });
        
        // Style all buttons
        const buttons = document.querySelectorAll('button');
        buttons.forEach(button => {
            if (!button.classList.contains('custom-button')) {
                button.style.backgroundColor = '#e74c3c';
                button.style.color = 'white';
                button.style.fontWeight = 'bold';
                button.style.border = 'none';
                button.style.borderRadius = '5px';
                button.style.padding = '8px 16px';
                button.style.cursor = 'pointer';
                button.style.transition = 'all 0.3s ease';
            }
        });
        
        // Add animation to progress bars
        const progressBars = document.querySelectorAll('.stProgress > div > div');
        progressBars.forEach(bar => {
            bar.style.transition = 'width 1s ease-in-out';
            bar.style.backgroundColor = '#e74c3c';
        });
        
        // Enhance file uploader
        const fileUploaders = document.querySelectorAll('.stFileUploader');
        fileUploaders.forEach(uploader => {
            uploader.style.backgroundColor = '#f0f8ff';
            uploader.style.border = '1px dashed #e74c3c';
            uploader.style.borderRadius = '8px';
            uploader.style.padding = '10px';
        });
        
        // Target the drag and drop area specifically
        const dropZones = document.querySelectorAll('[data-testid="stFileDropzone"]');
        dropZones.forEach(zone => {
            zone.style.backgroundColor = '#f0f8ff';
            zone.style.border = '1px dashed #e74c3c';
            zone.style.borderRadius = '8px';
        });
    `;
    
    // Return the code to be injected
    return enhanceUICode;
}

// Animation for the resume score
function animateScore(score) {
    // This will be injected via Streamlit components
    const animateScoreCode = `
        const scoreElement = document.querySelector('.score-value');
        if (scoreElement) {
            let currentScore = 0;
            const targetScore = ${score};
            const duration = 1500; // 1.5 seconds
            const interval = 20; // Update every 20ms
            const steps = duration / interval;
            const increment = targetScore / steps;
            
            const timer = setInterval(() => {
                currentScore += increment;
                if (currentScore >= targetScore) {
                    clearInterval(timer);
                    currentScore = targetScore;
                }
                scoreElement.textContent = Math.round(currentScore);
            }, interval);
        }
    `;
    
    // Return the code to be injected
    return animateScoreCode;
}