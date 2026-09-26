// ── DARK MODE ──
const darkToggle = document.getElementById('darkToggle');
const html = document.documentElement;

function setTheme(dark) {
    html.setAttribute('data-theme', dark ? 'dark' : 'light');
    localStorage.setItem('theme', dark ? 'dark' : 'light');
    if (darkToggle) darkToggle.textContent = dark ? '☀️' : '🌙';
}

// Load saved theme
const savedTheme = localStorage.getItem('theme') || 'light';
setTheme(savedTheme === 'dark');

if (darkToggle) {
    darkToggle.addEventListener('click', (e) => {
        e.preventDefault();
        const isDark = html.getAttribute('data-theme') === 'dark';
        setTheme(!isDark);
    });
}

// ── NAVBAR SCROLL ──
const navbar = document.querySelector('.navbar');
window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
        navbar?.classList.add('scrolled');
    } else {
        navbar?.classList.remove('scrolled');
    }
});

// ── ACTIVE NAV LINK ──
const navLinks = document.querySelectorAll('.nav-link');
const currentPath = window.location.pathname;
navLinks.forEach(link => {
    if (link.getAttribute('href') === currentPath) {
        link.classList.add('active');
    }
});

// ── TABS ──
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            const tabGroup = btn.closest('.tab-group') || document;

            // Remove active from all buttons in this group
            tabGroup.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            // Remove active from ALL tab-content in document (handles content outside tab-group)
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            // Search entire document for tab content
            const content = document.getElementById(targetTab);
            if (content) content.classList.add('active');
        });
    });
}
initTabs();

// ── LOADING ──
function showLoading() {
    const el = document.getElementById('loading');
    if (el) el.classList.add('show');
}
function hideLoading() {
    const el = document.getElementById('loading');
    if (el) el.classList.remove('show');
}

// ── ALERTS ──
function showAlert(message, type = 'info', containerId = 'alertContainer') {
    const container = document.getElementById(containerId);
    if (!container) return;
    const div = document.createElement('div');
    div.className = `alert alert-${type} fade-in`;
    div.textContent = message;
    container.innerHTML = '';
    container.appendChild(div);
    setTimeout(() => div.remove(), 4000);
}

// ── CHEAT CODE ──
let cheatBuffer = '';
document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    cheatBuffer += e.key.toLowerCase();
    if (cheatBuffer.length > 20) cheatBuffer = cheatBuffer.slice(-20);
    if (cheatBuffer.includes('ncsc2026')) {
        cheatBuffer = '';
        window.location.href = '/admin';
    }
});

// ── FADE IN ON SCROLL ──
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('fade-in');
        }
    });
}, { threshold: 0.1 });

document.querySelectorAll('.module-card, .card, .senior-card').forEach(el => {
    observer.observe(el);
});

// ── CONFIRM DELETE ──
function confirmDelete(message = 'Are you sure?') {
    return confirm(message);
}

// ── COUNTER ANIMATION ──
function animateCounter(el, target, duration = 1500) {
    let start = 0;
    const step = target / (duration / 16);
    const timer = setInterval(() => {
        start += step;
        if (start >= target) {
            el.textContent = target;
            clearInterval(timer);
        } else {
            el.textContent = Math.floor(start);
        }
    }, 16);
}

// Animate stats on page load
document.querySelectorAll('.stat-number[data-count]').forEach(el => {
    const target = parseInt(el.getAttribute('data-count'));
    animateCounter(el, target);
});
