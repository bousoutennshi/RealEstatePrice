document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const listingsGrid = document.getElementById('listings-grid');
    const totalListingsEl = document.getElementById('total-listings');
    const minPriceEl = document.getElementById('min-price');
    const lastUpdatedEl = document.getElementById('last-updated');
    const sortSelect = document.getElementById('sort-select');
    const searchInput = document.getElementById('search-input');
    const refreshBtn = document.getElementById('refresh-btn');

    // State
    let listings = [];

    // Initial Load
    fetchListings();

    // Event Listeners
    sortSelect.addEventListener('change', renderListings);
    searchInput.addEventListener('input', renderListings);
    refreshBtn.addEventListener('click', () => {
        listingsGrid.innerHTML = '<div class="loading-spinner"><i class="fas fa-circle-notch fa-spin"></i> Loading...</div>';
        fetchListings();
    });

    async function fetchListings() {
        try {
            const response = await fetch('/api/listings');
            const data = await response.json();

            if (data.error) {
                console.error(data.error);
                listingsGrid.innerHTML = `<div style="text-align:center; grid-column:1/-1;">Error loading data: ${data.error}</div>`;
                return;
            }

            // 重複排除ロジック
            // キー: price-area-floor-direction
            const uniqueMap = new Map();
            data.listings.forEach(item => {
                // ソースごとの重複排除に変更（異なるサイトなら同じ物件でも表示）
                const key = `${item.source}-${item.price || 0}-${item.area || 0}-${item.floor || 0}-${item.direction || ''}`;
                if (!uniqueMap.has(key)) {
                    uniqueMap.set(key, item);
                }
            });

            listings = Array.from(uniqueMap.values());
            console.log(`Loaded ${data.listings.length} listings, ${listings.length} unique.`);

            updateStats(data, listings.length);
            renderListings();

        } catch (error) {
            console.error('Error fetching listings:', error);
            listingsGrid.innerHTML = '<div style="text-align:center; grid-column:1/-1;">Failed to connect to server.</div>';
        }
    }

    function updateStats(data, uniqueCount) {
        // 表示名を変更
        const statLabel = document.querySelector('.stat-label');
        if (statLabel) statLabel.textContent = 'Unique Listings';

        totalListingsEl.textContent = uniqueCount;

        // Find min price
        const prices = listings.map(l => l.price).filter(p => p > 0);
        if (prices.length > 0) {
            const minPrice = Math.min(...prices);
            minPriceEl.innerHTML = formatPrice(minPrice);
        }

        // Format date
        if (data.last_updated) {
            const date = new Date(data.last_updated);
            lastUpdatedEl.textContent = date.toLocaleString('ja-JP');
        }
    }

    function renderListings() {
        // Filter
        const searchTerm = searchInput.value.toLowerCase();
        let filtered = listings.filter(l => {
            return (l.title && l.title.toLowerCase().includes(searchTerm)) ||
                (l.source && l.source.toLowerCase().includes(searchTerm));
        });

        // Sort
        const sortValue = sortSelect.value;
        filtered.sort((a, b) => {
            if (sortValue === 'price-asc') return (a.price || 999999999) - (b.price || 999999999);
            if (sortValue === 'price-desc') return (b.price || 0) - (a.price || 0);
            if (sortValue === 'floor-desc') return (b.floor || 0) - (a.floor || 0);
            if (sortValue === 'floor-asc') return (a.floor || 999) - (b.floor || 999);
            if (sortValue === 'area-desc') return (b.area || 0) - (a.area || 0);
            if (sortValue === 'posted-desc') return (b.posted_date || '').localeCompare(a.posted_date || '');
            return 0;
        });

        // Render
        listingsGrid.innerHTML = '';

        if (filtered.length === 0) {
            listingsGrid.innerHTML = '<div style="text-align:center; grid-column:1/-1; padding: 50px;">No listings found matching your criteria.</div>';
            return;
        }

        filtered.forEach((listing, index) => {
            const card = createListingCard(listing, index);
            listingsGrid.appendChild(card);
        });
    }

    function createListingCard(listing, index) {
        const div = document.createElement('div');
        div.className = 'listing-card';
        div.style.animationDelay = `${index * 0.05}s`;

        const priceFormatted = formatPrice(listing.price);
        const areaFormatted = listing.area ? `${listing.area}m²` : '-';
        const floorFormatted = listing.floor ? `${listing.floor}F` : '-';
        const directionFormatted = listing.direction || '-';
        const maintenance = listing.management_fee ? `¥${listing.management_fee.toLocaleString()}` : '-';
        const repair = listing.repair_reserve ? `¥${listing.repair_reserve.toLocaleString()}` : '-';

        div.innerHTML = `
            <div class="card-header">
                <div class="price-tag">${priceFormatted}</div>
                <div class="card-title" title="${listing.title}">${listing.title}</div>
            </div>
            <div class="card-body">
                <div class="info-grid">
                    <div class="info-item">
                        <span class="info-label"><i class="fas fa-vector-square info-icon"></i> Area</span>
                        <span class="info-value">${areaFormatted}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label"><i class="fas fa-building info-icon"></i> Floor</span>
                        <span class="info-value">${floorFormatted}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label"><i class="fas fa-compass info-icon"></i> Direction</span>
                        <span class="info-value">${directionFormatted}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label"><i class="fas fa-tools info-icon"></i> Repair Fee</span>
                        <span class="info-value">${repair}</span>
                    </div>
                </div>
                
                <div class="tags-section">
                    <span class="tag source-${listing.source.toLowerCase()}">${listing.source}</span>
                    ${listing.age_years ? `<span class="tag">Age: ${listing.age_years}yr</span>` : ''}
                </div>
            </div>
            <div class="card-footer">
                <span class="posted-date"><i class="far fa-clock"></i> ${listing.posted_date || 'Unknown'}</span>
                <a href="${listing.url}" target="_blank" class="view-btn">
                    View <i class="fas fa-external-link-alt"></i>
                </a>
            </div>
        `;

        return div;
    }

    function formatPrice(price) {
        if (!price) return '-';

        if (price >= 100000000) {
            const oku = Math.floor(price / 100000000);
            const man = Math.floor((price % 100000000) / 10000);
            return `<span style="font-size:1.4em">${oku}</span>億${man > 0 ? `<span style="font-size:1.1em">${man}</span>万` : ''}円`;
        } else {
            const man = Math.floor(price / 10000);
            return `<span style="font-size:1.4em">${man}</span>万円`;
        }
    }
});
