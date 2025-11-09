// --- 1. Konfigurace a Globální Stav ---
let allProducts = []; 
let currentFilters = { categories: [], sources: [] }; 

// !!! OPRAVA LOGA: Klíče musí odpovídat tomu, co je v DB (např. "dtrspider")
const logoMap = {
    // Tady musí být přesně to, co máš ve sloupci 'source_site' v DB
    'dtrspider': '/static/logos/datart.png', 
    'planeospider': '/static/logos/planeo.png',
    'mironetspider': '/static/logos/mironet.png',
    
    // Fallbacky, kdybys to měl čistě (pro jistotu)
    'datart': '/static/logos/datart.png', 
    'planeo': '/static/logos/planeo.png',
    'mironet': '/static/logos/mironet.png',
    'default': '/static/logos/default.png',
};

// --- 2. Tmavý Režim Logika (Funkční) ---
function toggleDarkMode() {
    const body = document.body;
    body.classList.toggle('dark-mode');
    
    const isDarkMode = body.classList.contains('dark-mode');
    localStorage.setItem('dark-mode', isDarkMode);

    const icon = document.querySelector('#dark-mode-toggle i');
    if (icon) {
        if (isDarkMode) {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
        } else {
            icon.classList.remove('fa-sun');
            icon.classList.add('fa-moon');
        }
    }
}

function loadDarkModeState() {
    const isDarkMode = localStorage.getItem('dark-mode') === 'true';
    const body = document.body;
    const icon = document.querySelector('#dark-mode-toggle i');

    if (isDarkMode) {
        body.classList.add('dark-mode');
        if (icon) {
            icon.classList.add('fa-sun');
            icon.classList.remove('fa-moon');
        }
    } else if (icon) {
        icon.classList.add('fa-moon');
        icon.classList.remove('fa-sun');
    }
}


// --- 3. Vykreslování Produktů a Filtrů (Hlavní stránka) ---

function createProductCard(product) {
    // Hledáme logo podle toho, co je v DB
    const sourceSiteKey = product.source_site ? product.source_site.toLowerCase() : 'default';
    const logoSrc = logoMap[sourceSiteKey] || logoMap.default;
    const ratingHtml = product.rating ? `<span class="product-rating">⭐ ${product.rating}</span>` : '';

    return `
        <div class="product-card" data-category="${product.category || 'Neznámá'}" data-source="${product.source_site || 'Neznámý'}">
            <div class="product-info">
                <div class="source-logo-container">
                    <img src="${logoSrc}" alt="${product.source_site} logo" class="source-logo">
                </div>
                <h3 class="product-title">${product.title}</h3>
                <p class="product-category">Kategorie: ${product.category || 'N/A'}</p>
                ${ratingHtml}
            </div>
            <div class="price-box">
                <span class="product-price">${(product.price || 0).toLocaleString('cs-CZ')} Kč</span>
                <a href="${product.link}" target="_blank" class="link-button">Koupit</a>
            </div>
        </div>
    `;
}

// Funkce pro filtry (zůstávají stejné)
function getUniqueOptions(data, key) {
    return [...new Set(data.map(item => item[key]).filter(Boolean))].sort(); 
}

function renderFilters() {
    const categories = getUniqueOptions(allProducts, 'category');
    const sources = getUniqueOptions(allProducts, 'source_site');
    
    const categoryContainer = document.getElementById('category-filters');
    const sourceContainer = document.getElementById('source-filters');

    const createFilterHtml = (options, type) => options.map(option => `
        <label>
            <input type="checkbox" data-filter-type="${type}" value="${option}">
            ${option}
        </label>
    `).join('');

    if (categoryContainer) categoryContainer.innerHTML = createFilterHtml(categories, 'category');
    if (sourceContainer) sourceContainer.innerHTML = createFilterHtml(sources, 'source');

    document.querySelectorAll('.filter-options input').forEach(checkbox => {
        checkbox.addEventListener('change', updateFilters);
    });
}

function updateFilters(event) {
    const checkbox = event.target;
    const type = checkbox.dataset.filterType;
    const value = checkbox.value;
    const filterArray = currentFilters[type === 'category' ? 'categories' : 'sources'];

    if (checkbox.checked) {
        filterArray.push(value);
    } else {
        const index = filterArray.indexOf(value);
        if (index > -1) {
            filterArray.splice(index, 1);
        }
    }
    filterAndRenderProducts(); 
}

function filterAndRenderProducts() {
    const listContainer = document.getElementById('product-list');
    if (!listContainer) return;
    
    const activeCategories = currentFilters.categories.length > 0;
    const activeSources = currentFilters.sources.length > 0;

    const filteredData = allProducts.filter(product => {
        const matchesCategory = !activeCategories || currentFilters.categories.includes(product.category);
        const matchesSource = !activeSources || currentFilters.sources.includes(product.source_site);
        return matchesCategory && matchesSource;
    });

    listContainer.innerHTML = filteredData.map(createProductCard).join('');
    
    const resultsHeader = document.querySelector('.results-area h2');
    if (resultsHeader) {
        resultsHeader.textContent = `Nalezené produkty (${filteredData.length})`;
    }
}


// --- 4. Načítání Dat z Backendu (DB) ---

async function loadDataFromDB() {
    try {
        const response = await fetch('/api/products'); 
        if (!response.ok) throw new Error('Chyba při načítání API');
        
        const products = await response.json();
        allProducts = products;
        
        renderFilters();
        filterAndRenderProducts(); 
        
    } catch (error) {
        console.error("Chyba při inicializaci dat:", error);
    }
}


// --- 5. Logika Vyhledávání (Opraveno vkládání do modálu) ---

function executeSearch() {
    const queryInput = document.getElementById('search-input'); 
    if (!queryInput) return;
    
    const query = queryInput.value.trim(); 
    
    const modal = document.getElementById('resultsModal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');

    if (!query) {
        alert("Zadej hledaný výraz.");
        return;
    }
    if (!modal || !modalBody || !modalTitle) {
        console.error("Chyba: Chybí elementy modálního okna v HTML.");
        return;
    }

    modalBody.innerHTML = '<p>Hledám v databázi...</p>'; 
    modalTitle.textContent = `Hledání pro "${query}"...`;
    
    fetch('/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query })
    })
    .then(response => response.json())
    .then(data => {
        const results = data.results;
        
        modalTitle.textContent = `Výsledky pro "${query}" (${results.length} nalezeno)`;
        
        if (results.length === 0) {
            modalBody.innerHTML = `<p style="text-align: center; color: var(--text-color);">Nebyly nalezeny žádné produkty.</p>`;
        } else {
            modalBody.innerHTML = ''; // Vyčistit "Hledám..."
            
            // !!! OPRAVA ZDE: Používáme insertAdjacentHTML
            results.forEach(item => {
                const cardHtml = createProductCard(item); 
                // Tato metoda je spolehlivější než appendChild s wrapperem
                modalBody.insertAdjacentHTML('beforeend', cardHtml);
            });
        }
        
        modal.style.display = 'block';

    })
    .catch(error => {
        console.error('Fetch error:', error);
        modalBody.innerHTML = `<p style="color: red;">Při vyhledávání došlo k chybě. Zkontroluj konzoli a Flask server.</p>`;
    });
}

// Logika zavírání modálního okna
function setupModalLogic() {
    const modal = document.getElementById('resultsModal');
    if (!modal) return; 

    const span = document.getElementsByClassName("close-btn")[0];

    if (span) {
         span.onclick = function() {
            modal.style.display = "none";
        }
    }
    window.onclick = function(event) {
        if (event.target === modal) {
            modal.style.display = "none";
        }
    }
}


// --- 6. Inicializace (Spuštění všeho) ---

document.addEventListener('DOMContentLoaded', () => {
    // 1. Tmavý režim
    loadDarkModeState();
    
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', toggleDarkMode);
    } else {
        console.error("Chyba: Tlačítko tmavého režimu (ID: dark-mode-toggle) nebylo nalezeno.");
    }

    // 2. Načtení dat z DB (pro filtry a hlavní seznam)
    loadDataFromDB(); 

    // 3. PŘIPOJENÍ VYHLEDÁVÁNÍ (Enter v poli)
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('keydown', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault(); 
                executeSearch();
            }
        });
    }
    
    // 4. PŘIPOJENÍ VYHLEDÁVÁNÍ (Klik na tlačítko)
    const searchButton = document.getElementById('search-button');
    if (searchButton) {
        searchButton.addEventListener('click', executeSearch);
    }
    
    // 5. Logika modálního okna
    setupModalLogic();
});