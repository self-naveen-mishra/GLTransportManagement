// Initialize tooltips
var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
});

// Form validation
(function () {
    'use strict';
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
})();


document.getElementById('tableSearch').addEventListener('input', function (e) {
    const searchText = e.target.value.toLowerCase();
    const table = document.getElementById('dataTable');
    const rows = table.getElementsByTagName('tr');
    let noMatchesFound = true;

    // Skip header row (index 0)
    for (let i = 1; i < rows.length; i++) {
        const row = rows[i];
        const cells = row.getElementsByTagName('td');
        let rowText = '';
        let found = false;

        // Combine all cell text in the row
        for (let cell of cells) {
            rowText += cell.textContent.toLowerCase() + ' ';
        }

        // Check if search text exists in row text
        if (rowText.includes(searchText)) {
            row.style.display = '';
            found = true;
            noMatchesFound = false;

            // Highlight matching text if search box is not empty
            if (searchText.length > 0) {
                for (let cell of cells) {
                    const cellText = cell.textContent;
                    if (cellText.toLowerCase().includes(searchText)) {
                        cell.classList.add('highlight');
                    } else {
                        cell.classList.remove('highlight');
                    }
                }
            } else {
                // Remove highlights if search box is empty
                for (let cell of cells) {
                    cell.classList.remove('highlight');
                }
            }
        } else {
            row.style.display = 'none';
        }
    }

    // Show no results message if no matches found
    const existingMessage = document.getElementById('noResultsMessage');
    if (noMatchesFound && searchText.length > 0) {
        if (!existingMessage) {
            const message = document.createElement('div');
            message.id = 'noResultsMessage';
            message.className = 'alert alert-info mt-3';
            message.innerHTML = '<i class="bi bi-info-circle me-2"></i>No matching records found';
            table.parentNode.appendChild(message);
        }
    } else if (existingMessage) {
        existingMessage.remove();
    }
});

// Debounce function to improve search performance
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Apply debouncing to search
const searchInput = document.getElementById('tableSearch');
const debouncedSearch = debounce((e) => {
    const event = new Event('input');
    searchInput.dispatchEvent(event);
}, 300);

searchInput.addEventListener('input', debouncedSearch);
