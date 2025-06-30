document.addEventListener('DOMContentLoaded', function() {
    // Confirm password match on registration form
    const registrationForm = document.getElementById('registration-form');
    if (registrationForm) {
        registrationForm.addEventListener('submit', function(e) {
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirm_password').value;
            
            if (password !== confirmPassword) {
                e.preventDefault();
                alert('Passwords do not match!');
            }
        });
    }
    
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Toggle availability status
    const availabilityToggle = document.getElementById('availability-toggle');
    if (availabilityToggle) {
        availabilityToggle.addEventListener('change', function() {
            const statusText = document.getElementById('availability-status');
            if (this.checked) {
                statusText.textContent = 'Available';
                statusText.className = 'badge bg-success';
            } else {
                statusText.textContent = 'Not Available';
                statusText.className = 'badge bg-secondary';
            }
            
            // Here you would typically make an AJAX call to update the status on the server
            fetch('/update-availability', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ is_available: this.checked }),
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    // Revert if update failed
                    this.checked = !this.checked;
                    if (this.checked) {
                        statusText.textContent = 'Available';
                        statusText.className = 'badge bg-success';
                    } else {
                        statusText.textContent = 'Not Available';
                        statusText.className = 'badge bg-secondary';
                    }
                    alert('Failed to update availability status.');
                }
            });
        });
    }
    
    // Image preview for profile photo upload
    const photoInput = document.getElementById('photo');
    if (photoInput) {
        photoInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    const preview = document.getElementById('photo-preview');
                    preview.src = event.target.result;
                    preview.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
    }
});