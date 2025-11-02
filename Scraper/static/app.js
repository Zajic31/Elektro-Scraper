document.getElementById('search-button').addEventListener('click', function() {
    const query = document.getElementById('search_item').value.trim();
    const modal = document.getElementById('resultsModal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');
    const statusMessage = document.getElementById('status-message');

    if (!query) {
        statusMessage.textContent = "Please enter a search term.";
        return;
    }

    // 1. Update status and clear old results
    statusMessage.textContent = "Searching database...";
    modalBody.innerHTML = ''; // Clear previous results
    
    // 2. Make an AJAX POST request to the /search endpoint
    fetch('/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: query })
    })
    .then(response => response.json())
    .then(data => {
        const results = data.results;
        
        // 3. Update Modal Title
        modalTitle.textContent = `Results for "${query}" (${results.length} found)`;
        
        // 4. Check for No Results
        if (results.length === 0) {
            modalBody.innerHTML = `<p style="text-align: center; color: #dc3545;">No products found matching "${query}".</p>`;
        } else {
            // 5. Build Result Cards and append to modal body
            results.forEach(item => {
                // Use Intl.NumberFormat for clean currency display (e.g., 53 990 Kč)
                const priceFormatted = new Intl.NumberFormat('cs-CZ', { 
                    style: 'currency', 
                    currency: 'CZK',
                    minimumFractionDigits: 0
                }).format(item.price);

                const card = document.createElement('div');
                card.className = 'result-card';
                
                card.innerHTML = `
                    <div class="details">
                        <div class="title-site">${item.title}</div>
                        <div class="site-info">From: ${item.source_site}</div>
                    </div>
                    <div class="price-rating">
                        <div class="price">${priceFormatted}</div>
                        <div class="rating">Rating: 
                            ${item.rating ? `${item.rating} / 5 ⭐` : 'N/A'}
                        </div>
                    </div>
                    <a href="${item.link}" target="_blank" class="view-link">View</a>
                `;
                modalBody.appendChild(card);
            });
        }
        
        // 6. Show the Pop-up
        modal.style.display = 'block';
        statusMessage.textContent = "Search complete.";

    })
    .catch(error => {
        console.error('Fetch error:', error);
        statusMessage.textContent = "An error occurred during search.";
    });
});

// --- Modal Display Logic ---

// Get the modal and the close button
const modal = document.getElementById('resultsModal');
const span = document.getElementsByClassName("close-btn")[0];

// Close the modal when the user clicks on (x)
span.onclick = function() {
  modal.style.display = "none";
}

// Close the modal when the user clicks anywhere outside of it
window.onclick = function(event) {
  if (event.target == modal) {
    modal.style.display = "none";
  }
}