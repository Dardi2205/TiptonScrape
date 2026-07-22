document.addEventListener('DOMContentLoaded', function() {
    // View toggle
    const viewBtns = document.querySelectorAll('.view-btn');
    const viewInput = document.getElementById('viewInput');

    viewBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            viewBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            if (viewInput) viewInput.value = this.dataset.view;
            this.closest('form').submit();
        });
    });

    // Load stats
    fetch('/api/stats/')
        .then(r => r.json())
        .then(data => {
            document.getElementById('totalProducts').textContent = data.total_products || 0;
            document.getElementById('totalStores').textContent = data.total_stores || 0;
            document.getElementById('totalDiscounts').textContent = data.products_on_discount || 0;
            document.getElementById('avgPrice').textContent = data.avg_price
                ? Math.round(data.avg_price).toLocaleString() + ' L'
                : '-';
        })
        .catch(() => {});
});
